"""Parse the tagged master manuscript (.docx) into a list of book blocks.

Layout tags ([...]) and Notes are dropped; the "How to read this document"
preamble and the "Production notes" tail are excluded. Output is a list of
sections, each a list of blocks, ready for pagination and IDML generation.
"""
import html
import re
import sys
import zipfile

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def curly(text):
    """Straight quotes -> curly (spec: curly throughout)."""
    out = []
    for i, ch in enumerate(text):
        prev = text[i - 1] if i else ' '
        if ch == '"':
            out.append('“' if prev in ' \t(—[\u2028' else '”')
        elif ch == "'":
            out.append('‘' if prev in ' \t(—[\u2028"“' else '’')
        else:
            out.append(ch)
    return ''.join(out)


def runs_of(pxml):
    runs = []
    for r in re.findall(r'<w:r[ >].*?</w:r>', pxml, re.S):
        t = ''.join(re.findall(r'<w:t(?: [^>]*)?>([^<]*)</w:t>', r))
        t = html.unescape(t)
        if '<w:tab/>' in r:
            t += '\t'
        if '<w:br/>' in r or '<w:br ' in r:
            t += '\u2028'
        if not t:
            continue
        b = bool(re.search(r'<w:b/>|<w:b w:val="(1|true)"', r))
        i = bool(re.search(r'<w:i/>|<w:i w:val="(1|true)"', r))
        runs.append([t, b, i])
    joined = curly(''.join(r[0] for r in runs))
    pos = 0
    for r in runs:
        r[0] = joined[pos:pos + len(r[0])]
        pos += len(r[0])
    # merge adjacent runs with equal formatting
    merged = []
    for r in runs:
        if merged and merged[-1][1:] == r[1:]:
            merged[-1][0] += r[0]
        else:
            merged.append(r)
    return merged


def para_style(pxml):
    m = re.search(r'<w:pStyle w:val="([^"]+)"', pxml)
    return m.group(1) if m else 'BodyText'


def parse(path):
    with zipfile.ZipFile(path) as z:
        doc = z.read('word/document.xml').decode('utf8')
    body = doc[doc.find('<w:body>'):]
    items = re.findall(r'<w:tbl>.*?</w:tbl>|<w:p[ >].*?</w:p>', body, re.S)
    blocks = []
    for it in items:
        if it.startswith('<w:tbl>'):
            cols = [int(x) for x in re.findall(r'<w:gridCol w:w="(\d+)"', it)]
            rows = []
            for r in re.findall(r'<w:tr[ >].*?</w:tr>', it, re.S):
                cells = []
                for c in re.findall(r'<w:tc>.*?</w:tc>', r, re.S):
                    paras = [runs_of(p) for p in re.findall(r'<w:p[ >].*?</w:p>', c, re.S)]
                    cells.append(paras)
                rows.append({'header': 'tblHeader' in r,
                             'bold': bool(re.search(r'<w:b/>', r)),
                             'cells': cells})
            blocks.append({'kind': 'table', 'cols': cols, 'rows': rows})
        else:
            st = para_style(it)
            runs = runs_of(it)
            text = ''.join(r[0] for r in runs)
            blocks.append({'kind': 'para', 'style': st, 'runs': runs, 'text': text,
                           'num': '<w:numPr>' in it})
    return blocks


def book_blocks(blocks):
    """Trim to manuscript text, drop tags/notes, attach the preceding layout tag."""
    start = next(i for i, b in enumerate(blocks)
                 if b['kind'] == 'para' and b['style'] == 'Tag' and b['text'].startswith('[TITLE PAGE'))
    end = next(i for i, b in enumerate(blocks)
               if b['kind'] == 'para' and b['style'] == 'Tag' and b['text'].startswith('[END OF MANUSCRIPT'))
    out = []
    last_tag = ''
    for b in blocks[start:end]:
        if b['kind'] == 'para' and b['style'] == 'Tag':
            last_tag = b['text']
            continue
        if b['kind'] == 'para' and b['style'] == 'Note':
            continue
        b['tag'] = last_tag
        out.append(b)
    return out


if __name__ == '__main__':
    bl = book_blocks(parse(sys.argv[1]))
    for b in bl:
        print(b['kind'], b.get('style'), (b.get('text') or '')[:60])
