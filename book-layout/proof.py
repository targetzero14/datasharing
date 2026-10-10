"""Typeset the book model with ReportLab to (a) plan pagination for the IDML
and (b) produce a PDF proof that shows the intended layout.

The proof is an approximation of what Affinity will set (different
hyphenation/justification engine), so page plans carry a little slack.
"""
import os
from xml.sax.saxutils import escape

from reportlab.lib.colors import CMYKColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Frame, KeepTogether, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus.flowables import Flowable, HRFlowable

import model as M
import styles as S

FONT_DIR = os.environ.get('FONT_DIR', os.path.join(os.path.dirname(__file__), '..', 'fonts'))
FONT_FILES = {
    'serif': 'EBG-Regular.ttf', 'serif-it': 'EBG-Italic.ttf', 'serif-semi': 'EBG-SemiBold.ttf',
    'sans': 'Jost-Regular.ttf', 'sans-medium': 'Jost-Medium.ttf', 'sans-semi': 'Jost-SemiBold.ttf',
}
for key, fn in FONT_FILES.items():
    pdfmetrics.registerFont(TTFont(key, os.path.join(FONT_DIR, fn)))


def color(name):
    if name == 'Black':
        return CMYKColor(0, 0, 0, 1)
    if name == 'Paper':
        return CMYKColor(0, 0, 0, 0)
    return CMYKColor(0, 0, 0, S.COLORS[name][0] / 100.0)


ALIGN = {'left': TA_LEFT, 'center': TA_CENTER, 'right': TA_RIGHT}
_pstyles = {}


def pstyle(name):
    if name not in _pstyles:
        r = S.resolved(name)
        kw = dict(fontName=r['font'], fontSize=r['size'], leading=r['lead'],
                  spaceBefore=r['before'], spaceAfter=r['after'],
                  textColor=color(r['color']), alignment=ALIGN[r['align']],
                  leftIndent=r['left'], allowWidows=0, allowOrphans=0,
                  underlineWidth=0.5, underlineOffset=-2.5)
        if r['hyph']:
            kw.update(hyphenationLang='en_US', embeddedHyphenation=1, uriWasteReduce=0.3)
        if name == 'Numbered List':
            kw.update(bulletFontName='sans', bulletFontSize=r['size'], bulletIndent=0)
        _pstyles[name] = ParagraphStyle(name, **kw)
    return _pstyles[name]


def track(text, amount):
    """Tracking is set in the IDML styles; the proof leaves caps untracked."""
    return text


def markup(runs, style):
    r = S.resolved(style)
    out = []
    for text, cs in runs:
        if r['caps']:
            text = text.upper()
        t = escape(track(text, r['track'])).replace(M.LSEP, '<br/>')
        if cs == 'Fill-in Rule':
            out.append('<u>%s</u>' % t)
        elif cs:
            out.append('<font name="%s">%s</font>' % (S.CHAR[cs]['font'], t))
        else:
            out.append(t)
    return ''.join(out)


def para(item):
    style = item['style']
    runs = item['runs']
    if style == 'Numbered List':
        bullet = runs[0][0]
        return Paragraph(markup(runs[2:], style), pstyle(style), bulletText=bullet)
    return Paragraph(markup(runs, style), pstyle(style))


class Whole(Flowable):
    """Never split: moves to the next frame as a unit."""
    def __init__(self, flows):
        super().__init__()
        self.flows = flows

    def wrap(self, aw, ah):
        self.sizes = [f.wrap(aw, 10000) for f in self.flows]
        return aw, sum(h for _, h in self.sizes)

    def split(self, aw, ah):
        return []

    def draw(self):
        y = sum(h for _, h in self.sizes)
        for f, (w, h) in zip(self.flows, self.sizes):
            y -= h
            f.drawOn(self.canv, 0, y)


class NeedSpace(Flowable):
    """Push to the next frame unless `need` points remain (keep-with-next)."""
    def __init__(self, need):
        super().__init__()
        self.need = need

    def wrap(self, aw, ah):
        self._ah = ah
        return (aw, 0) if ah >= self.need else (aw, ah + 1)

    def split(self, aw, ah):
        return []

    def draw(self):
        pass


def cell_flow(paras, style):
    return [Paragraph(markup(p, style), pstyle(style)) for p in paras]


def cell_style(kind, rtype, ci):
    if kind == 'appendix':
        if rtype == 'header':
            return 'Appendix Header Center' if ci in (0, 4) else 'Appendix Header'
        return {0: 'Appendix Body Center', 1: 'Appendix Number', 4: 'Appendix Body Center'}.get(ci, 'Appendix Body')
    if rtype == 'header':
        return 'Table Header'
    if rtype == 'result':
        return 'Table Result'
    return 'Table Body'


def table_flow(item):
    kind, widths, rows = item['kind'], item['widths'], item['rows']
    data, cmds = [], [('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]
    pad = 4 if kind == 'appendix' else 6
    cmds += [('LEFTPADDING', (0, 0), (-1, -1), pad), ('RIGHTPADDING', (0, 0), (-1, -1), pad),
             ('TOPPADDING', (0, 0), (-1, -1), 4 if kind == 'appendix' else 6),
             ('BOTTOMPADDING', (0, 0), (-1, -1), 4 if kind == 'appendix' else 6)]
    heights = []
    band_idx = 0
    for ri, row in enumerate(rows):
        line = []
        for ci, cell in enumerate(row['cells']):
            st = cell_style(kind, row['type'], ci)
            line.append(cell_flow(cell, st))
        data.append(line)
        if row['type'] == 'header':
            cmds.append(('BACKGROUND', (0, ri), (-1, ri), color('Navy')))
            heights.append(None)
        else:
            if band_idx % 2 == 0:
                cmds.append(('BACKGROUND', (0, ri), (-1, ri), color('Light Gray')))
            band_idx += 1
            cmds.append(('LINEBELOW', (0, ri), (-1, ri), 0.5, color('Hairline')))
            heights.append(None)
        if row['type'] == 'result':
            cmds.append(('LINEABOVE', (0, ri), (-1, ri), 1, color('Navy')))
    if rows[0]['type'] != 'header':
        cmds.append(('LINEABOVE', (0, 0), (-1, 0), 0.5, color('Hairline')))
    t = Table(data, colWidths=widths, rowHeights=heights,
              repeatRows=1 if rows[0]['type'] == 'header' else 0, hAlign='LEFT')
    t.setStyle(TableStyle(cmds))
    return t


def band_flow(item):
    flows = []
    for k, (label, line) in enumerate(item['pairs']):
        if label:
            st = 'Formula Label Second' if k else 'Formula Label'
            flows.append(Paragraph(markup([(label, None)], st), pstyle(st)))
        st = 'Formula Line Second' if (k and not label) else 'Formula Line'
        flows.append(Paragraph(markup([(line, None)], st), pstyle(st)))
    t = Table([[flows]], colWidths=[M.TW], hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), color('Light Gray')),
        ('LINEABOVE', (0, 0), (-1, 0), 0.5, color('Black')),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, color('Black')),
        ('LEFTPADDING', (0, 0), (-1, -1), 14), ('RIGHTPADDING', (0, 0), (-1, -1), 14),
        ('TOPPADDING', (0, 0), (-1, -1), 14), ('BOTTOMPADDING', (0, 0), (-1, -1), 14)]))
    return [Spacer(1, 14), t, Spacer(1, 14)]


def rules_flow(item):
    t = Table([['']] * item['count'], colWidths=[M.TW], rowHeights=[25.2] * item['count'],
              hAlign='LEFT')
    t.setStyle(TableStyle([('LINEBELOW', (0, 0), (-1, -1), 0.5, color('Black'))]))
    return [Spacer(1, 4), t, Spacer(1, 8)]


def flowables(section):
    out = []
    items = section['items']
    for k, it in enumerate(items):
        if it['t'] == 'p':
            r = S.resolved(it['style'])
            f = para(it)
            if it['style'] == 'Worksheet Title':
                out.append(NeedSpace(130))
                out.append(Spacer(1, 22))
                out.append(HRFlowable(width='100%', thickness=1, color=color('Black'),
                                      spaceBefore=0, spaceAfter=9, hAlign='LEFT'))
                f.style = ParagraphStyle('wt0', parent=f.style, spaceBefore=0)
            elif r['keep_next']:
                nxt = items[k + 1] if k + 1 < len(items) else None
                need = r['before'] + r['lead'] + r['after'] + 2 * S.BODY_LEAD
                if nxt and nxt['t'] in ('table', 'band'):
                    need += 60
                out.append(NeedSpace(need))
            out.append(f)
        elif it['t'] == 'table':
            t = table_flow(it)
            if it.get('new_page'):
                out.append(NeedSpace(M.TH - 1))
            sp = [Spacer(1, 6), t, Spacer(1, 10)]
            out.extend([Whole(sp)] if it['kind'] != 'appendix' else sp)
        elif it['t'] == 'band':
            out.append(Whole(band_flow(it)))
        elif it['t'] == 'rules':
            out.extend(rules_flow(it))
    return out


class Book:
    """Lays sections out page by page; records a page plan for the IDML writer."""

    def __init__(self, sections, path):
        self.sections = sections
        self.c = Canvas(path, pagesize=(M.PW, M.PH))
        self.c.setTitle('Marketing by the Numbers — 6x9 KDP proof')
        self.pages = []          # dicts: section, role, label, frame (top, height)
        self.toc_pages = {}

    def page_box(self, recto, opener):
        x = M.M_IN if recto else M.M_OUT
        top = M.M_TOP + (M.SINK if opener else 0)
        return x, top, M.TW, M.TH - (M.SINK if opener else 0)

    def label(self, idx):
        if self.arabic_start is None or idx < self.arabic_start:
            return roman(idx + 1)
        return str(idx - self.arabic_start + 1)

    def folio(self, idx):
        self.c.setFont('sans', 9.5)
        self.c.setFillColor(color('Mid Gray'))
        self.c.drawCentredString((M.M_IN if idx % 2 == 0 else M.M_OUT) + M.TW / 2,
                                 39.5, self.label(idx))

    def blank(self, si):
        self.pages.append(dict(section=si, role='blank'))
        self.c.showPage()

    def to_recto(self, si):
        if len(self.pages) % 2 == 1:
            self.blank(si)

    def frame_page(self, si, flows, role, top=None, height=None):
        idx = len(self.pages)
        recto = idx % 2 == 0
        x, ftop, w, h = self.page_box(recto, role == 'opener')
        if top is not None:
            ftop, h = top, height
        f = Frame(x, M.PH - ftop - h, w, h, leftPadding=0, rightPadding=0,
                  topPadding=0, bottomPadding=0, showBoundary=0)
        added = 0
        while flows:
            head = flows[0]
            if f.add(head, self.c, trySplit=0):
                flows.pop(0)
                added += 1
                continue
            parts = f.split(head, self.c)
            if parts and 'Break' in type(parts[0]).__name__:
                flows[0:1] = parts[1:]
                added += 1
                break
            if parts and f.add(parts[0], self.c, trySplit=0):
                flows[0:1] = parts[1:]
                added += 1
            break
        if not added and flows:
            raise RuntimeError('cannot place %r on page %d' % (flows[0], idx))
        if role == 'body':
            self.folio(idx)
        self.pages.append(dict(section=si, role=role, frame=(ftop, h)))
        self.c.showPage()

    def run(self, arabic_from):
        self.arabic_start = None
        for si, s in enumerate(self.sections):
            if s['kind'] == 'chapter' and s['title'] == arabic_from and self.arabic_start is None:
                self.to_recto(si)
                self.arabic_start = len(self.pages)
            if s['kind'] == 'title':
                self.draw_title(si, s)
                continue
            if s['kind'] == 'copyright':
                self.draw_copyright(si, s)
                continue
            self.to_recto(si)
            s['start'] = len(self.pages)
            flows = self.contents_flows() if s['kind'] == 'contents' else flowables(s)
            role = 'opener'
            while flows:
                self.frame_page(si, flows, role)
                role = 'body'
            s['npages'] = len(self.pages) - s['start']
        self.c.save()
        return self.pages

    def draw_title(self, si, s):
        flows = [para(it) for it in s['items']]
        # gold (KDP: thin black) rule under the title, ahead of the subtitle
        rule = HRFlowable(width=72, thickness=0.75, color=color('Honey Gold'),
                          spaceBefore=16, spaceAfter=0, hAlign='LEFT')
        flows.insert(1, rule)
        top = M.M_TOP + 108
        f = Frame(M.M_IN, M.PH - top - 300, M.TW, 300, 0, 0, 0, 0)
        f.addFromList(flows, self.c)
        f2 = Frame(M.M_IN, M.M_BOT, M.TW, 30, 0, 0, 0, 0)
        f2.addFromList([Paragraph(escape(s['imprint']), pstyle('Title Imprint'))], self.c)
        self.pages.append(dict(section=si, role='title'))
        self.c.showPage()

    def draw_copyright(self, si, s):
        flows = [para(it) for it in s['items']]
        h = sum(fl.wrap(M.TW, 1000)[1] + fl.style.spaceAfter for fl in flows)
        f = Frame(M.M_OUT, M.M_BOT, M.TW, h + 2, 0, 0, 0, 0)
        f.addFromList(flows, self.c)
        self.pages.append(dict(section=si, role='copyright'))
        self.c.showPage()

    def contents_flows(self):
        flows = [Paragraph('Contents', pstyle('H1'))]
        rows = []
        for s in self.sections:
            if s['kind'] == 'chapter' and s.get('toc'):
                num = self.toc_pages.get(s['title'], '')
                rows.append([Paragraph(escape(s['toc']), pstyle('Contents Entry')),
                             Paragraph('<font name="sans">%s</font>' % num,
                                       ParagraphStyle('tn', parent=pstyle('Contents Entry'),
                                                      alignment=TA_RIGHT))])
        t = Table(rows, colWidths=[M.TW - 30, 30], hAlign='LEFT')
        t.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0),
                               ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                               ('TOPPADDING', (0, 0), (-1, -1), 0),
                               ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                               ('VALIGN', (0, 0), (-1, -1), 'TOP')]))
        flows.append(t)
        return flows


def roman(n):
    vals = [(10, 'x'), (9, 'ix'), (5, 'v'), (4, 'iv'), (1, 'i')]
    out = ''
    for v, s in vals:
        while n >= v:
            out += s
            n -= v
    return out


ARABIC_FROM = 'You Don’t Have a Marketing Problem'


def typeset(sections, pdf_path):
    """Two passes: the second fills real page numbers into the contents."""
    book = Book(sections, pdf_path)
    book.run(ARABIC_FROM)
    toc = {s['title']: book.label(s['start']) for s in sections if s['kind'] == 'chapter'}
    book2 = Book(sections, pdf_path)
    book2.toc_pages = toc
    pages = book2.run(ARABIC_FROM)
    return book2, pages, toc
