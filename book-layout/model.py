"""Turn parsed manuscript blocks into a book model: sections of styled items.

Item kinds:
  {'t': 'p', 'style': <paragraph style>, 'runs': [(text, charstyle|None)]}
  {'t': 'table', 'kind': 'worksheet'|'grid'|'appendix', 'widths': [pt],
   'rows': [{'type': 'header'|'body'|'result', 'cells': [[runs, ...], ...]}]}
  {'t': 'band', 'pairs': [(label, line_text)]}
  {'t': 'rules', 'count': n}          # blank write-in lines
"""
import re

from parse_docx import parse, book_blocks

# 6x9 KDP geometry (points)
PW, PH = 432.0, 648.0
M_TOP, M_BOT, M_IN, M_OUT = 54.0, 61.2, 54.0, 39.6
TW = PW - M_IN - M_OUT          # 338.4 text width
TH = PH - M_TOP - M_BOT         # 532.8 text height
SINK = 77.5                      # chapter-opener drop = 5 body lines

NBSP = ' '
LSEP = ' '

# Defaults for Allen's open decisions (confirmed by the user: "use the defaults")
CH8_SECOND_LINE = 'If it doubled tomorrow, would your revenue change?'


def close_dashes(text):
    """TSA assembly rule: em dashes closed up in running text."""
    return text.replace(' \u2014 ', '\u2014')


def fill_runs(text, style=None, cell_chars=None):
    """Split text on underscore runs; each run becomes a 'Fill-in Rule' segment
    of non-breaking spaces (underlined by the character style)."""
    out = []
    text = close_dashes(text)
    parts = re.split(r'(_{3,})', text)
    for i, part in enumerate(parts):
        if not part:
            continue
        if i % 2:
            n = len(part)
            if cell_chars is not None and text.strip('_ $%×') == '':
                n = cell_chars           # answer-only cell: run to cell width
            else:
                n = max(4, round(n * 0.9))
            out.append((NBSP * n, 'Fill-in Rule'))
        else:
            out.append((part, style))
    return out


def body_runs(runs, para_start_runin=True):
    """Map docx runs (text, bold, italic) to character styles."""
    out = []
    for k, (text, b, i) in enumerate(runs):
        if b and k == 0 and para_start_runin and text.rstrip().endswith('.'):
            cs = 'Run-in'
        elif b:
            cs = 'Semibold'
        elif i:
            cs = 'Italic'
        else:
            cs = None
        out.extend(fill_runs(text, cs))
    return out


def plain(text, cs=None):
    return [(text, cs)]


def table_item(block):
    ncols = len(block['cols'])
    total = sum(block['cols'])
    rows = block['rows']
    if ncols == 5:
        kind = 'appendix'
        widths = [16, 64, 126, 84, 48.4]
    else:
        kind = 'worksheet' if ncols == 2 else 'grid'
        widths = [round(TW * c / total, 2) for c in block['cols']]
    out_rows = []
    for r in rows:
        cells = r['cells']
        # source fix: Worksheet 1 / Step 1 has the "L" of "Last" stranded in col 1
        if ncols == 2:
            a = ''.join(t for p in cells[0] for t, _, _ in p)
            if a.endswith(' L'):
                cells[0] = [[[a[:-2], False, False]]]
                b = ''.join(t for p in cells[1] for t, _, _ in p)
                cells[1] = [[['L' + b, False, False]]]
        if r['header']:
            rtype = 'header'
        elif r['bold'] and kind != 'appendix':
            rtype = 'result'
        else:
            rtype = 'body'
        new_cells = []
        for ci, cell in enumerate(cells):
            w = widths[ci]
            paras = []
            for p in cell:
                text = ''.join(t for t, _, _ in p)
                # answer-only cells: rule length that fits the cell
                chars = max(6, int((w - 14) / 3.2))
                if text.startswith('$ ') and set(text[2:]) <= {'_'}:
                    paras.append([('$ ', None), (NBSP * (chars - 3), 'Fill-in Rule')])
                elif re.fullmatch(r'_+( [%×])?', text):
                    tail = text.split(' ')[1] if ' ' in text else ''
                    rr = [(NBSP * (chars - (3 if tail else 0)), 'Fill-in Rule')]
                    if tail:
                        rr.append((' ' + tail, None))
                    paras.append(rr)
                else:
                    paras.append(fill_runs(text))
            new_cells.append(paras)
        out_rows.append({'type': rtype, 'cells': new_cells})
    return {'t': 'table', 'kind': kind, 'widths': widths, 'rows': out_rows}


def build_sections(docx_path):
    blocks = book_blocks(parse(docx_path))
    sections = []

    def new(kind, title=None, toc=None):
        s = {'kind': kind, 'title': title, 'toc': toc, 'items': []}
        sections.append(s)
        return s

    i = 0
    # --- title page: H1, H3 subtitle, author, imprint
    title = new('title')
    title['items'] = [
        {'t': 'p', 'style': 'Title', 'runs': plain('Marketing' + LSEP + 'by the Numbers')},
        {'t': 'p', 'style': 'Title Subtitle', 'runs': plain(blocks[1]['text'])},
        {'t': 'p', 'style': 'Title Author', 'runs': plain(blocks[2]['text'])},
    ]
    title['imprint'] = blocks[3]['text']
    i = 4
    # --- copyright (the "Copyright" H2 label is dropped; the page is self-evident)
    assert blocks[i]['text'] == 'Copyright'
    cp = new('copyright')
    i += 1
    while blocks[i]['text'] != 'Contents':
        cp['items'].append({'t': 'p', 'style': 'Copyright', 'runs': body_runs(blocks[i]['runs'])})
        i += 1
    # --- contents: entries are regenerated from the section list (same wording)
    i += 1
    toc_lines = []
    while blocks[i]['style'] != 'Heading1':
        toc_lines.append(blocks[i]['text'])
        i += 1
    new('contents', title='Contents')

    # --- running sections split at Kicker / Heading1
    cur = None
    list_no = 0
    band = None
    pending_kicker = None
    for b in blocks[i:]:
        if b['kind'] == 'table':
            cur['items'].append(table_item(b))
            list_no = 0
            band = None
            continue
        st, text = b['style'], b['text']
        if st not in ('FormulaLabel', 'FormulaLine'):
            band = None
        if st == 'Kicker':
            pending_kicker = text
            continue
        if st == 'Heading1':
            cur = new('chapter', title=text)
            if pending_kicker:
                cur['items'].append({'t': 'p', 'style': 'Kicker', 'runs': plain(pending_kicker)})
                cur['kicker'] = pending_kicker
                pending_kicker = None
            cur['items'].append({'t': 'p', 'style': 'H1', 'runs': plain(text)})
            list_no = 0
            continue
        if st == 'FormulaLabel':
            if band is None:
                band = {'t': 'band', 'pairs': []}
                cur['items'].append(band)
            band['pairs'].append([text, None])
            continue
        if st == 'FormulaLine':
            band['pairs'][-1][1] = text
            continue
        if b['num']:
            list_no += 1
            runs = [(f'{list_no}.', 'Inter Numeral'), ('\t', None)] + body_runs(b['runs'], False)
            cur['items'].append({'t': 'p', 'style': 'Numbered List', 'runs': runs})
            continue
        list_no = 0
        if st == 'Heading2':
            style = 'Worksheet Title' if text.startswith('Worksheet ') else 'H2'
            cur['items'].append({'t': 'p', 'style': style, 'runs': plain(text)})
        elif st == 'Heading3':
            cur['items'].append({'t': 'p', 'style': 'H3 Step', 'runs': plain(text)})
        elif text.startswith('— Allen Stafford'):
            cur['items'].append({'t': 'p', 'style': 'Sign-off', 'runs': plain(text.replace('\u2014 ', '\u2014'))})
        else:
            style = 'Body First' if st == 'FirstParagraph' else 'Body'
            cur['items'].append({'t': 'p', 'style': style, 'runs': body_runs(b['runs'])})

    # --- layout decisions applied in the model
    for s in sections:
        items = s['items']
        for k, it in enumerate(items):
            if it['t'] == 'band':
                for pair in it['pairs']:
                    # G2: the requested break ("…years they stay,") cannot fit one
                    # line at 12 pt in a 6x9 band, so it sets as three centered lines.
                    if pair[1].startswith('Average sale × times they buy'):
                        pair[1] = ('Average sale × times they buy per year' + LSEP +
                                   '× years they stay,' + LSEP +
                                   'then add the value of customers they refer')
                if it['pairs'][0][0] == 'THE TEST FOR EVERYTHING ELSE':
                    it['pairs'].append(['', CH8_SECOND_LINE])
            # Worksheet 8 steps 1 and 3 have no table: give them write-in lines
            if it['t'] == 'p' and it['style'] == 'Body First':
                txt = ''.join(t for t, _ in it['runs'])
                if txt.startswith('Write down the numbers you regularly see'):
                    items.insert(k + 1, {'t': 'rules', 'count': 5})
                elif txt.startswith('Write the short list of numbers'):
                    items.insert(k + 1, {'t': 'rules', 'count': 5})
        # Appendix: the reference table must sit whole on one page
        for it in items:
            if it['t'] == 'table' and it['kind'] == 'appendix':
                it['new_page'] = True

    # TOC labels follow the manuscript's contents list
    chapters = [s for s in sections if s['kind'] == 'chapter']
    for s in chapters:
        for line in toc_lines:
            if line.endswith(s['title']) or line == s['title']:
                s['toc'] = line
    return sections


if __name__ == '__main__':
    import sys
    for s in build_sections(sys.argv[1]):
        print(s['kind'], s.get('title'), s.get('toc'), len(s['items']))
