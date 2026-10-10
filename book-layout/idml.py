"""Write the book model + page plan as an IDML package (opens in Affinity and InDesign)."""
import zipfile
from xml.sax.saxutils import escape, quoteattr

import model as M
import styles as S

PKG = 'xmlns:idPkg="http://ns.adobe.com/AdobeInDesign/idml/1.0/packaging" DOMVersion="16.0"'
HEAD = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
NOCS = 'CharacterStyle/$ID/[No character style]'


def a(v):
    return quoteattr(str(v))


def fmt(x):
    return ('%.3f' % x).rstrip('0').rstrip('.')


def color_ref(name):
    return 'Color/' + name


class Ids:
    def __init__(self):
        self.n = 0

    def __call__(self, prefix='u'):
        self.n += 1
        return '%s%x' % (prefix, self.n + 0x100)


ids = Ids()


# ----------------------------------------------------------------- resources
def graphic_xml():
    out = [HEAD, '<idPkg:Graphic %s>' % PKG,
           '<Color Self="Color/Black" Model="Process" Space="CMYK" ColorValue="0 0 0 100" '
           'ColorOverride="Specialblack" AlternateSpace="NoAlternateColor" AlternateColorValue="" '
           'Name="Black" ColorEditable="false" ColorRemovable="false" Visible="true" SwatchCreatorID="7937"/>',
           '<Color Self="Color/Paper" Model="Process" Space="CMYK" ColorValue="0 0 0 0" '
           'ColorOverride="Specialpaper" AlternateSpace="NoAlternateColor" AlternateColorValue="" '
           'Name="Paper" ColorEditable="true" ColorRemovable="false" Visible="true" SwatchCreatorID="7937"/>',
           '<Color Self="Color/Registration" Model="Registration" Space="CMYK" ColorValue="100 100 100 100" '
           'ColorOverride="Specialregistration" AlternateSpace="NoAlternateColor" AlternateColorValue="" '
           'Name="Registration" ColorEditable="false" ColorRemovable="false" Visible="true" SwatchCreatorID="7937"/>']
    for name, (k, rgb) in S.COLORS.items():
        out.append('<Color Self=%s Model="Process" Space="CMYK" ColorValue="0 0 0 %d" ColorOverride="Normal" '
                   'AlternateSpace="NoAlternateColor" AlternateColorValue="" Name=%s ColorEditable="true" '
                   'ColorRemovable="true" Visible="true" SwatchCreatorID="7937"/>'
                   % (a(color_ref(name)), k, a(name)))
    for name, (k, rgb) in S.COLORS.items():
        out.append('<Color Self=%s Model="Process" Space="RGB" ColorValue="%d %d %d" ColorOverride="Normal" '
                   'AlternateSpace="NoAlternateColor" AlternateColorValue="" Name=%s ColorEditable="true" '
                   'ColorRemovable="true" Visible="true" SwatchCreatorID="7937"/>'
                   % (a(color_ref(name + ' RGB')), rgb[0], rgb[1], rgb[2], a(name + ' (Gumroad RGB)')))
    out += ['<Swatch Self="Swatch/None" Name="None" ColorEditable="false" ColorRemovable="false" '
            'Visible="true" SwatchCreatorID="7937"/>',
            '<StrokeStyle Self="StrokeStyle/$ID/Solid" Name="$ID/Solid"/>',
            '</idPkg:Graphic>']
    return '\n'.join(out)


def fonts_xml():
    fams = {}
    for fam, style, ps in S.FONTS.values():
        fams.setdefault(fam, []).append((style, ps))
    out = [HEAD, '<idPkg:Fonts %s>' % PKG]
    for i, (fam, styles) in enumerate(fams.items()):
        fid = 'di%x' % (0x40 + i)
        out.append('<FontFamily Self=%s Name=%s>' % (a(fid), a(fam)))
        for style, ps in styles:
            out.append('<Font Self=%s FontFamily=%s Name=%s PostScriptName=%s Status="Installed" '
                       'FontStyleName=%s FontType="OpenTypeTT" WritingScript="0" FullName=%s '
                       'FullNameNative=%s FontStyleNameNative=%s PlatformName="$ID/" Version=""/>'
                       % (a(fid + 'Font' + ps), a(fam), a(fam + '\t' + style), a(ps), a(style),
                          a(fam + ' ' + style), a(fam + ' ' + style), a(style)))
        out.append('</FontFamily>')
    out.append('</idPkg:Fonts>')
    return '\n'.join(out)


JUST = {'left': 'LeftAlign', 'center': 'CenterAlign', 'right': 'RightAlign'}


def para_style_xml(name):
    r = S.resolved(name)
    fam, style, _ = S.FONTS[r['font']]
    attrs = dict(Self='ParagraphStyle/' + name, Name=name, Imported='false',
                 NextStyle='ParagraphStyle/' + name, KeyboardShortcut='0 0',
                 FontStyle=style, PointSize=fmt(r['size']),
                 SpaceBefore=fmt(r['before']), SpaceAfter=fmt(r['after']),
                 FillColor=color_ref(r['color']), Justification=JUST[r['align']],
                 Capitalization='AllCaps' if r['caps'] else 'Normal', Tracking=r['track'],
                 LeftIndent=fmt(r['left']), FirstLineIndent=fmt(r['first']),
                 Hyphenation='true' if r['hyph'] else 'false',
                 KeepWithNext='2' if r['keep_next'] else '0',
                 AlignToBaseline='false')
    if r['figs']:
        attrs['OTFFigureStyle'] = r['figs']
    if name in ('Body', 'Body First', 'Numbered List', 'Sign-off'):
        attrs.update(KeepLinesTogether='true', KeepFirstLines='2', KeepLastLines='2',
                     HyphenateCapitalizedWords='false', HyphenateLadderLimit='2')
    if name.startswith('H') or name in ('Kicker', 'Worksheet Title', 'Title'):
        attrs['BalanceRaggedLines'] = 'true'
    ra = r.get('rule_above')
    if ra:
        attrs.update(RuleAbove='true', RuleAboveLineWeight=fmt(ra['weight']),
                     RuleAboveColor=color_ref(ra['color']), RuleAboveOffset=fmt(ra['offset']),
                     RuleAboveWidth='ColumnWidth', RuleAboveType='StrokeStyle/$ID/Solid',
                     RuleAboveTint='100')
    rb = r.get('rule_below')
    if rb:
        attrs.update(RuleBelow='true', RuleBelowLineWeight=fmt(rb['weight']),
                     RuleBelowColor=color_ref(rb['color']), RuleBelowOffset=fmt(rb['offset']),
                     RuleBelowWidth='ColumnWidth', RuleBelowType='StrokeStyle/$ID/Solid',
                     RuleBelowTint='100',
                     RuleBelowRightIndent=fmt(M.TW - rb['length']))
    props = ['<BasedOn type="string">$ID/[No paragraph style]</BasedOn>',
             '<PreviewColor type="enumeration">Nothing</PreviewColor>',
             '<AppliedFont type="string">%s</AppliedFont>' % escape(fam),
             '<Leading type="unit">%s</Leading>' % fmt(r['lead'])]
    if r['tabs']:
        items = []
        for t in r['tabs']:
            align, pos = ('LeftAlign', t) if not isinstance(t, tuple) else (
                'RightAlign' if t[0] == 'right' else 'LeftAlign', t[1])
            items.append('<ListItem type="record"><Alignment type="enumeration">%s</Alignment>'
                         '<AlignmentCharacter type="string">.</AlignmentCharacter>'
                         '<Leader type="string"></Leader><Position type="unit">%s</Position>'
                         '</ListItem>' % (align, fmt(pos)))
        props.append('<TabList type="list">%s</TabList>' % ''.join(items))
    return '<ParagraphStyle %s><Properties>%s</Properties></ParagraphStyle>' % (
        ' '.join('%s=%s' % (k, a(v)) for k, v in attrs.items()), ''.join(props))


def char_style_xml(name):
    c = S.CHAR[name]
    attrs = dict(Self='CharacterStyle/' + name, Name=name, Imported='false', KeyboardShortcut='0 0')
    props = '<BasedOn type="string">$ID/[No character style]</BasedOn>' \
            '<PreviewColor type="enumeration">Nothing</PreviewColor>'
    if 'font' in c:
        fam, style, _ = S.FONTS[c['font']]
        attrs['FontStyle'] = style
        props += '<AppliedFont type="string">%s</AppliedFont>' % escape(fam)
    if 'underline' in c:
        attrs.update(Underline='true', UnderlineWeight=fmt(c['underline']),
                     UnderlineOffset='2.5', UnderlineColor='Color/Black',
                     UnderlineType='StrokeStyle/$ID/Solid')
    return '<CharacterStyle %s><Properties>%s</Properties></CharacterStyle>' % (
        ' '.join('%s=%s' % (k, a(v)) for k, v in attrs.items()), props)


def styles_xml():
    out = [HEAD, '<idPkg:Styles %s>' % PKG,
           '<RootCharacterStyleGroup Self="rcsg">',
           '<CharacterStyle Self="CharacterStyle/$ID/[No character style]" Imported="false" '
           'Name="$ID/[No character style]"/>']
    out += [char_style_xml(n) for n in S.CHAR]
    out += ['</RootCharacterStyleGroup>', '<RootParagraphStyleGroup Self="rpsg">',
            '<ParagraphStyle Self="ParagraphStyle/$ID/[No paragraph style]" Name="$ID/[No paragraph style]" '
            'Imported="false" FontStyle="Regular" PointSize="11" FillColor="Color/Black" '
            'Hyphenation="true"><Properties><Leading type="unit">15.5</Leading>'
            '<AppliedFont type="string">Source Serif 4</AppliedFont></Properties></ParagraphStyle>',
            '<ParagraphStyle Self="ParagraphStyle/$ID/NormalParagraphStyle" Name="$ID/NormalParagraphStyle" '
            'Imported="false" NextStyle="ParagraphStyle/$ID/NormalParagraphStyle" KeyboardShortcut="0 0">'
            '<Properties><BasedOn type="string">$ID/[No paragraph style]</BasedOn></Properties></ParagraphStyle>']
    out += [para_style_xml(n) for n in S.PARA]
    out += ['</RootParagraphStyleGroup>',
            '<RootCellStyleGroup Self="rcesg"><CellStyle Self="CellStyle/$ID/[None]" Name="$ID/[None]" '
            'AppliedParagraphStyle="ParagraphStyle/$ID/[No paragraph style]"/></RootCellStyleGroup>',
            '<RootTableStyleGroup Self="rtsg">'
            '<TableStyle Self="TableStyle/$ID/[No table style]" Name="$ID/[No table style]"/>'
            '<TableStyle Self="TableStyle/$ID/[Basic Table]" Name="$ID/[Basic Table]"/></RootTableStyleGroup>',
            '<RootObjectStyleGroup Self="rosg">'
            '<ObjectStyle Self="ObjectStyle/$ID/[None]" Name="$ID/[None]"/>'
            '<ObjectStyle Self="ObjectStyle/$ID/[Normal Graphics Frame]" Name="$ID/[Normal Graphics Frame]"/>'
            '<ObjectStyle Self="ObjectStyle/$ID/[Normal Text Frame]" Name="$ID/[Normal Text Frame]"/>'
            '</RootObjectStyleGroup>',
            '</idPkg:Styles>']
    return '\n'.join(out)


def prefs_xml(npages):
    return HEAD + '\n'.join([
        '<idPkg:Preferences %s>' % PKG,
        '<DocumentPreference PageHeight="%s" PageWidth="%s" PagesPerDocument="%d" FacingPages="true" '
        'DocumentBleedTopOffset="0" DocumentBleedBottomOffset="0" DocumentBleedInsideOrLeftOffset="0" '
        'DocumentBleedOutsideOrRightOffset="0" DocumentBleedUniformSize="true" SlugTopOffset="0" '
        'SlugBottomOffset="0" SlugInsideOrLeftOffset="0" SlugRightOrOutsideOffset="0" '
        'DocumentSlugUniformSize="false" PreserveLayoutWhenShuffling="true" AllowPageShuffle="true" '
        'OverprintBlack="true" PageBinding="LeftToRight" ColumnDirection="Horizontal" '
        'ColumnGuideLocked="true" MasterTextFrame="false" SnippetImportUsesOriginalLocation="false" '
        'Intent="PrintIntent" StartPageNumber="1"/>' % (fmt(M.PH), fmt(M.PW), npages),
        '<MarginPreference ColumnCount="1" ColumnGutter="12" Top="%s" Bottom="%s" Left="%s" Right="%s" '
        'ColumnDirection="Horizontal" ColumnsPositions="0 %s"/>'
        % (fmt(M.M_TOP), fmt(M.M_BOT), fmt(M.M_IN), fmt(M.M_OUT), fmt(M.TW)),
        '<GridPreference DocumentGridShown="false" DocumentGridSnapto="false" HorizontalGridlineDivision="72" '
        'VerticalGridlineDivision="72" HorizontalGridSubdivision="8" VerticalGridSubdivision="8" '
        'GridsInBack="true" BaselineGridShown="false" BaselineStart="%s" BaselineDivision="%s" '
        'BaselineViewThreshold="75" BaselineGridRelativeOption="TopOfPageOfBaselineGridRelativeOption"/>'
        % (fmt(M.M_TOP), fmt(S.BODY_LEAD)),
        '<ViewPreference HorizontalMeasurementUnits="Inches" VerticalMeasurementUnits="Inches" '
        'TypographicMeasurementUnits="Points" TextSizeMeasurementUnits="Points" '
        'LineMeasurementUnits="Points" PointsPerInch="72"/>',
        '</idPkg:Preferences>'])


# ----------------------------------------------------------------- stories
def csr(text, cs=None, br=False):
    style = 'CharacterStyle/' + cs if cs else NOCS
    body = '<Content>%s</Content>' % escape(text) if text else ''
    return '<CharacterStyleRange AppliedCharacterStyle=%s>%s%s</CharacterStyleRange>' % (
        a(style), body, '<Br/>' if br else '')


def psr(style, runs, br=True, extra=''):
    parts = []
    for k, (text, cs) in enumerate(runs):
        parts.append(csr(text, cs, br=br and k == len(runs) - 1))
    if not runs:
        parts.append(csr('', None, br=br))
    return '<ParagraphStyleRange AppliedParagraphStyle=%s%s>%s</ParagraphStyleRange>' % (
        a('ParagraphStyle/' + style), extra, ''.join(parts))


def cell_xml(tid, col, row, paras, style, fill, top, bottom, insets, valign='CenterAlign'):
    """paras: list of runs; top/bottom: (weight, color) or None."""
    attrs = dict(Self='%si%d_%d' % (tid, col, row), Name='%d:%d' % (col, row), RowSpan='1',
                 ColumnSpan='1', AppliedCellStyle='CellStyle/$ID/[None]', AppliedCellStylePriority='0',
                 FillColor=fill or 'Swatch/None', FillTint='100' if fill else '-1',
                 TopInset=fmt(insets[0]), LeftInset=fmt(insets[1]), BottomInset=fmt(insets[2]),
                 RightInset=fmt(insets[3]), VerticalJustification=valign,
                 LeftEdgeStrokeWeight='0', RightEdgeStrokeWeight='0',
                 LeftEdgeStrokeColor='Swatch/None', RightEdgeStrokeColor='Swatch/None')
    for edge, val in (('Top', top), ('Bottom', bottom)):
        if val:
            attrs.update({edge + 'EdgeStrokeWeight': fmt(val[0]),
                          edge + 'EdgeStrokeColor': color_ref(val[1]),
                          edge + 'EdgeStrokeType': 'StrokeStyle/$ID/Solid',
                          edge + 'EdgeStrokeTint': '100'})
        else:
            attrs.update({edge + 'EdgeStrokeWeight': '0', edge + 'EdgeStrokeColor': 'Swatch/None'})
    body = ''.join(psr(st, runs, br=k < len(paras) - 1) for k, (st, runs) in enumerate(paras))
    return '<Cell %s>%s</Cell>' % (' '.join('%s=%s' % (k, a(v)) for k, v in attrs.items()), body)


def table_xml(widths, rows, header_rows=0, space=(6, 10), keep=True, min_h=None):
    """rows: list of dicts {cells: [[(style, runs), ...] per cell], fill, top, bottom, insets}"""
    tid = ids('t')
    out = ['<Table Self=%s HeaderRowCount="%d" FooterRowCount="0" BodyRowCount="%d" ColumnCount="%d" '
           'AppliedTableStyle="TableStyle/$ID/[Basic Table]" TableDirection="LeftToRightDirection" '
           'SpaceBefore="%s" SpaceAfter="%s" TopBorderStrokeWeight="0" BottomBorderStrokeWeight="0" '
           'LeftBorderStrokeWeight="0" RightBorderStrokeWeight="0" StrokeOrder="BestJoins">'
           % (a(tid), header_rows, len(rows) - header_rows, len(widths), fmt(space[0]), fmt(space[1]))]
    for ri, r in enumerate(rows):
        mh = r.get('min_h', min_h)
        out.append('<Row Self="%sRow%d" Name="%d" AutoGrow="true" %s KeepWithNextRow="%s"/>'
                   % (tid, ri, ri, ('MinimumHeight="%s" SingleRowHeight="%s"' % (fmt(mh), fmt(mh))) if mh else '',
                      'true' if keep and ri < len(rows) - 1 else 'false'))
    for ci, w in enumerate(widths):
        out.append('<Column Self="%sColumn%d" Name="%d" SingleColumnWidth="%s"/>' % (tid, ci, ci, fmt(w)))
    for ri, r in enumerate(rows):
        for ci, paras in enumerate(r['cells']):
            out.append(cell_xml(tid, ci, ri, paras, None, r.get('fill'), r.get('top'), r.get('bottom'),
                                r.get('insets', (6, 6, 6, 6)), r.get('valign', 'CenterAlign')))
    out.append('</Table>')
    return ''.join(out)


def worksheet_table(item):
    kind = item['kind']
    rows = []
    band = 0
    pad = (4, 4, 4, 4) if kind == 'appendix' else (6, 6, 6, 6)
    for ri, r in enumerate(item['rows']):
        cells = []
        for ci, cell in enumerate(r['cells']):
            st = cell_style(kind, r['type'], ci)
            cells.append([(st, runs) for runs in cell])
        row = dict(cells=cells, insets=pad)
        if r['type'] == 'header':
            row.update(fill='Color/Navy', valign='BottomAlign')
        else:
            if band % 2 == 0:
                row['fill'] = 'Color/Light Gray'
            band += 1
            row['bottom'] = (0.5, 'Hairline')
            if ri == 0:
                row['top'] = (0.5, 'Hairline')
            if kind != 'appendix':
                row['min_h'] = 25.2      # answer cells >= 0.35"
        if r['type'] == 'result':
            row['top'] = (1, 'Navy')
        rows.append(row)
    header = 1 if item['rows'][0]['type'] == 'header' else 0
    return table_xml(item['widths'], rows, header_rows=header, keep=kind != 'appendix')


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


def band_table(item):
    paras = []
    for k, (label, line) in enumerate(item['pairs']):
        if label:
            paras.append(('Formula Label Second' if k else 'Formula Label', [(label, None)]))
        paras.append(('Formula Line Second' if (k and not label) else 'Formula Line', [(line, None)]))
    row = dict(cells=[paras], fill='Color/Light Gray', top=(0.5, 'Black'), bottom=(0.5, 'Black'),
               insets=(14, 14, 14, 14))
    return table_xml([M.TW], [row], space=(14, 14))


def rules_table(item):
    rows = [dict(cells=[[('Table Body', [])]], bottom=(0.5, 'Black'), min_h=25.2,
                 insets=(4, 0, 4, 0)) for _ in range(item['count'])]
    return table_xml([M.TW], rows, space=(4, 8))


def story_items(items):
    out = []
    for it in items:
        if it['t'] == 'p':
            out.append(psr(it['style'], it['runs']))
        else:
            if it['t'] == 'table':
                tx = worksheet_table(it)
            elif it['t'] == 'band':
                tx = band_table(it)
            else:
                tx = rules_table(it)
            extra = ' StartParagraph="NextFrame"' if it.get('new_page') else ''
            out.append('<ParagraphStyleRange AppliedParagraphStyle="ParagraphStyle/Table Anchor"%s>'
                       '<CharacterStyleRange AppliedCharacterStyle=%s>%s<Br/></CharacterStyleRange>'
                       '</ParagraphStyleRange>' % (extra, a(NOCS), tx))
    # drop the trailing paragraph break of the story
    if out:
        last = out[-1]
        k = last.rfind('<Br/>')
        out[-1] = last[:k] + last[k + 5:]
    return ''.join(out)


def story_xml(sid, body):
    return HEAD + ('<idPkg:Story %s><Story Self=%s AppliedTOCStyle="n" TrackChanges="false" '
                   'StoryTitle="$ID/" AppliedNamedGrid="n">'
                   '<StoryPreference OpticalMarginAlignment="false" OpticalMarginSize="12" '
                   'FrameType="TextFrameType" StoryOrientation="Horizontal" '
                   'StoryDirection="LeftToRightDirection"/>%s</Story></idPkg:Story>' % (PKG, a(sid), body))


# ----------------------------------------------------------------- spreads
def frame_xml(fid, sid, x0, y0, x1, y1, prev='n', nxt='n', valign='TopAlign'):
    pts = ''.join('<PathPointType Anchor="{0} {1}" LeftDirection="{0} {1}" RightDirection="{0} {1}"/>'
                  .format(fmt(x), fmt(y)) for x, y in ((x0, y0), (x0, y1), (x1, y1), (x1, y0)))
    return ('<TextFrame Self=%s ParentStory=%s PreviousTextFrame=%s NextTextFrame=%s ContentType="TextType" '
            'AppliedObjectStyle="ObjectStyle/$ID/[Normal Text Frame]" ItemTransform="1 0 0 1 0 0" '
            'ItemLayer="uLayer" Locked="false" Visible="true" Name="$ID/">'
            '<Properties><PathGeometry><GeometryPathType PathOpen="false"><PathPointArray>%s'
            '</PathPointArray></GeometryPathType></PathGeometry></Properties>'
            '<TextFramePreference TextColumnCount="1" TextColumnGutter="12" FirstBaselineOffset="AscentOffset" '
            'MinimumFirstBaselineOffset="0" VerticalJustification="%s" VerticalThreshold="0" '
            'IgnoreWrap="false" AutoSizingType="Off" UseFixedColumnWidth="false">'
            '<Properties><InsetSpacing type="list"><ListItem type="unit">0</ListItem>'
            '<ListItem type="unit">0</ListItem><ListItem type="unit">0</ListItem>'
            '<ListItem type="unit">0</ListItem></InsetSpacing></Properties></TextFramePreference>'
            '</TextFrame>' % (a(fid), a(sid), a(prev), a(nxt), pts, valign))


def page_x(idx_or_recto, recto=None):
    """Spread-coordinate x of the text area's left edge."""
    return M.M_IN if recto else -M.PW + M.M_OUT


def margin_xml():
    return ('<MarginPreference ColumnCount="1" ColumnGutter="12" Top="%s" Bottom="%s" Left="%s" Right="%s" '
            'ColumnDirection="Horizontal" ColumnsPositions="0 %s"/>'
            % (fmt(M.M_TOP), fmt(M.M_BOT), fmt(M.M_IN), fmt(M.M_OUT), fmt(M.TW)))


def page_xml(pid, name, master, recto):
    return ('<Page Self=%s Name=%s AppliedMaster=%s ItemTransform="1 0 0 1 %s -324" '
            'GeometricBounds="0 0 %s %s" OverrideList="" MasterPageTransform="1 0 0 1 0 0" '
            'TabOrder="" GridStartingPoint="TopOutside" UseMasterGrid="true">%s</Page>'
            % (a(pid), a(name), a(master), '0' if recto else '-432', fmt(M.PH), fmt(M.PW), margin_xml()))


def write(sections, pages, labels, arabic_start, out_path):
    stories = {}            # sid -> xml body
    frames_by_page = {i: [] for i in range(len(pages))}

    def y(top):
        return -M.PH / 2 + top

    # -- story per section
    sec_story = {}
    for si, s in enumerate(sections):
        sid = ids('st')
        sec_story[si] = sid
        if s['kind'] == 'title':
            stories[sid] = story_items(s['items'])
            imp = ids('st')
            stories[imp] = story_items([{'t': 'p', 'style': 'Title Imprint', 'runs': [(s['imprint'], None)]}])
            s['imprint_story'] = imp
        elif s['kind'] == 'contents':
            items = [{'t': 'p', 'style': 'H1', 'runs': [('Contents', None)]}]
            for c in sections:
                if c['kind'] == 'chapter' and c.get('toc'):
                    items.append({'t': 'p', 'style': 'Contents Entry',
                                  'runs': [(c['toc'], None), ('\t', None),
                                           (labels[c['start']], 'Inter Numeral')]})
            stories[sid] = story_items(items)
        else:
            stories[sid] = story_items(s['items'])

    # -- frames from the page plan
    chains = {}
    for idx, pg in enumerate(pages):
        recto = idx % 2 == 0
        x0 = page_x(idx, recto)
        si = pg['section']
        s = sections[si]
        role = pg['role']
        if role == 'title':
            top = M.M_TOP + 108
            frames_by_page[idx].append(frame_xml(ids('tf'), sec_story[si], x0, y(top), x0 + M.TW, y(top + 300)))
            frames_by_page[idx].append(frame_xml(ids('tf'), s['imprint_story'], x0, y(M.PH - M.M_BOT - 30),
                                                 x0 + M.TW, y(M.PH - M.M_BOT)))
        elif role == 'copyright':
            frames_by_page[idx].append(frame_xml(ids('tf'), sec_story[si], x0, y(M.M_TOP), x0 + M.TW,
                                                 y(M.PH - M.M_BOT), valign='BottomAlign'))
        elif role in ('opener', 'body'):
            top, h = pg['frame']
            chains.setdefault(si, []).append((idx, ids('tf'), x0, y(top), x0 + M.TW, y(top + h)))
        elif role == 'blank' and si > 0 and sections[si - 1]['kind'] == 'chapter' and si - 1 in chains:
            # padding verso: threaded as overflow slack for the chapter before it
            chains[si - 1].append((idx, ids('tf'), x0, y(M.M_TOP), x0 + M.TW, y(M.PH - M.M_BOT)))
        elif role == 'blank' and si == len(sections):
            pass
    for si, chain in chains.items():
        for k, (idx, fid, x0, y0, x1, y1) in enumerate(chain):
            prev = chain[k - 1][1] if k else 'n'
            nxt = chain[k + 1][1] if k + 1 < len(chain) else 'n'
            frames_by_page[idx].append(frame_xml(fid, sec_story[si], x0, y0, x1, y1, prev, nxt))

    # -- masters
    folio_l, folio_r = ids('st'), ids('st')
    for sid in (folio_l, folio_r):
        stories[sid] = ('<ParagraphStyleRange AppliedParagraphStyle="ParagraphStyle/Folio">'
                        '<CharacterStyleRange AppliedCharacterStyle=%s><Content><?ACE 18?></Content>'
                        '</CharacterStyleRange></ParagraphStyleRange>' % a(NOCS))
    fy0, fy1 = y(M.PH - M.M_BOT + 14), y(M.PH - M.M_BOT + 30)
    master_a = (HEAD + '<idPkg:MasterSpread %s><MasterSpread Self="mA" Name="A-Body" NamePrefix="A" '
                'BaseName="Body" ShowMasterItems="true" PageCount="2" OverriddenPageItemProps="" '
                'PrimaryTextFrame="n" ItemTransform="1 0 0 1 0 0">' % PKG
                + page_xml('mApL', 'A', 'n', False).replace(' TabOrder="" GridStartingPoint="TopOutside" UseMasterGrid="true"', '')
                + page_xml('mApR', 'A', 'n', True).replace(' TabOrder="" GridStartingPoint="TopOutside" UseMasterGrid="true"', '')
                + frame_xml(ids('tf'), folio_l, -M.PW + M.M_OUT, fy0, -M.M_IN, fy1)
                + frame_xml(ids('tf'), folio_r, M.M_IN, fy0, M.PW - M.M_OUT, fy1)
                + '</MasterSpread></idPkg:MasterSpread>')
    master_b = (HEAD + '<idPkg:MasterSpread %s><MasterSpread Self="mB" Name="B-No Folio" NamePrefix="B" '
                'BaseName="No Folio" ShowMasterItems="true" PageCount="2" OverriddenPageItemProps="" '
                'PrimaryTextFrame="n" ItemTransform="1 0 0 1 0 0">' % PKG
                + page_xml('mBpL', 'B', 'n', False).replace(' TabOrder="" GridStartingPoint="TopOutside" UseMasterGrid="true"', '')
                + page_xml('mBpR', 'B', 'n', True).replace(' TabOrder="" GridStartingPoint="TopOutside" UseMasterGrid="true"', '')
                + '</MasterSpread></idPkg:MasterSpread>')

    # -- spreads: [p0] then pairs
    groups = [[0]] + [list(range(i, min(i + 2, len(pages)))) for i in range(1, len(pages), 2)]
    spreads = []
    page_ids = {}
    for g in groups:
        spid = ids('sp')
        parts = []
        for idx in g:
            pid = ids('pg')
            page_ids[idx] = pid
            master = 'mA' if pages[idx]['role'] == 'body' else 'mB'
            parts.append(page_xml(pid, labels[idx], master, idx % 2 == 0))
        for idx in g:
            parts.extend(frames_by_page[idx])
        binding = 0 if g[0] % 2 == 0 else 1
        spreads.append((spid, HEAD + '<idPkg:Spread %s><Spread Self=%s PageCount="%d" BindingLocation="%d" '
                        'AllowPageShuffle="true" ShowMasterItems="true" ItemTransform="1 0 0 1 0 0" '
                        'FlattenerOverride="Default" PageTransitionType="None">%s</Spread></idPkg:Spread>'
                        % (PKG, a(spid), len(g), binding, ''.join(parts))))

    # -- designmap
    story_ids = list(stories)
    sections_xml = (
        '<Section Self="usec1" Length="%d" Name="" ContinueNumbering="false" IncludeSectionPrefix="false" '
        'PageNumberStyle="LowerRoman" PageStart=%s SectionPrefix="" Marker="" PageNumberStart="1"/>'
        '<Section Self="usec2" Length="%d" Name="" ContinueNumbering="false" IncludeSectionPrefix="false" '
        'PageNumberStyle="Arabic" PageStart=%s SectionPrefix="" Marker="" PageNumberStart="1"/>'
        % (arabic_start, a(page_ids[0]), len(pages) - arabic_start, a(page_ids[arabic_start])))
    design = [HEAD, '<?aid style="50" type="document" readerVersion="6.0" featureSet="257" product="16.0(32)" ?>',
              '<Document %s Self="d" StoryList=%s Name="Marketing by the Numbers - KDP 6x9.indd" '
              'ZeroPoint="0 0" ActiveLayer="uLayer" CMYKProfile="U.S. Web Coated (SWOP) v2" '
              'RGBProfile="sRGB IEC61966-2.1" SolidColorIntent="UseColorSettings" '
              'AfterBlendingIntent="UseColorSettings" DefaultImageIntent="UseColorSettings" '
              'RGBPolicy="PreserveEmbeddedProfiles" CMYKPolicy="CombinationOfPreserveAndSafeCmyk" '
              'AccurateLABSpots="false">' % (PKG, a(' '.join(story_ids))),
              '<idPkg:Graphic src="Resources/Graphic.xml"/>',
              '<idPkg:Fonts src="Resources/Fonts.xml"/>',
              '<idPkg:Styles src="Resources/Styles.xml"/>',
              '<idPkg:Preferences src="Resources/Preferences.xml"/>',
              '<idPkg:Tags src="XML/Tags.xml"/>',
              '<Layer Self="uLayer" Name="Layer 1" Visible="true" Locked="false" IgnoreWrap="false" '
              'ShowGuides="true" LockGuides="false" UI="true" Expendable="true" Printable="true">'
              '<Properties><LayerColor type="enumeration">LightBlue</LayerColor></Properties></Layer>',
              '<idPkg:MasterSpread src="MasterSpreads/MasterSpread_mA.xml"/>',
              '<idPkg:MasterSpread src="MasterSpreads/MasterSpread_mB.xml"/>']
    design += ['<idPkg:Spread src="Spreads/Spread_%s.xml"/>' % spid for spid, _ in spreads]
    design.append(sections_xml)
    design.append('<idPkg:BackingStory src="XML/BackingStory.xml"/>')
    design += ['<idPkg:Story src="Stories/Story_%s.xml"/>' % sid for sid in story_ids]
    design.append('</Document>')

    tags = (HEAD + '<idPkg:Tags %s><XMLTag Self="XMLTag/Root" Name="Root"><Properties>'
            '<TagColor type="enumeration">LightBlue</TagColor></Properties></XMLTag></idPkg:Tags>' % PKG)
    backing = (HEAD + '<idPkg:BackingStory %s><XmlStory Self="ubs" AppliedTOCStyle="n" TrackChanges="false" '
               'StoryTitle="$ID/" AppliedNamedGrid="n"><XMLElement Self="di2" MarkupTag="XMLTag/Root"/>'
               '<ParagraphStyleRange AppliedParagraphStyle="ParagraphStyle/$ID/NormalParagraphStyle">'
               '<CharacterStyleRange AppliedCharacterStyle=%s/></ParagraphStyleRange></XmlStory>'
               '</idPkg:BackingStory>' % (PKG, a(NOCS)))
    container = (HEAD + '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
                 '<rootfiles><rootfile full-path="designmap.xml" media-type="text/xml"/></rootfiles></container>')

    with zipfile.ZipFile(out_path, 'w') as z:
        z.writestr(zipfile.ZipInfo('mimetype'), 'application/vnd.adobe.indesign-idml-package',
                   compress_type=zipfile.ZIP_STORED)
        def put(name, data):
            z.writestr(name, data.encode('utf8'), compress_type=zipfile.ZIP_DEFLATED)
        put('designmap.xml', '\n'.join(design))
        put('META-INF/container.xml', container)
        put('Resources/Graphic.xml', graphic_xml())
        put('Resources/Fonts.xml', fonts_xml())
        put('Resources/Styles.xml', styles_xml())
        put('Resources/Preferences.xml', prefs_xml(len(pages)))
        put('XML/Tags.xml', tags)
        put('XML/BackingStory.xml', backing)
        put('MasterSpreads/MasterSpread_mA.xml', master_a)
        put('MasterSpreads/MasterSpread_mB.xml', master_b)
        for spid, xml in spreads:
            put('Spreads/Spread_%s.xml' % spid, xml)
        for sid, body in stories.items():
            put('Stories/Story_%s.xml' % sid, story_xml(sid, body))
