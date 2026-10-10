"""Single source of truth for the KDP 6x9 style sheet (from the manuscript's TSA tags).

Both the PDF proof renderer and the IDML writer read from here.
KDP edition = black ink only: Navy -> K100, Honey Gold -> K60, Mid Gray -> K100,
Light Gray -> K12. The brand RGB values are kept as extra swatches for Gumroad.
"""

# swatch name -> (KDP grey %K, Gumroad RGB)
COLORS = {
    'Navy':       (100, (27, 42, 74)),
    'Honey Gold': (60,  (224, 160, 40)),
    'Mid Gray':   (100, (107, 114, 128)),
    'Light Gray': (12,  (242, 244, 247)),
    'Hairline':   (40,  (196, 203, 214)),
}

# font key -> (family, style name as installed from Google Fonts, PostScript name)
FONTS = {
    'serif':      ('Source Serif 4', 'Regular',  'SourceSerif4-Regular'),
    'serif-it':   ('Source Serif 4', 'Italic',   'SourceSerif4-Italic'),
    'serif-semi': ('Source Serif 4', 'SemiBold', 'SourceSerif4-SemiBold'),
    'inter':      ('Inter',          'Regular',  'Inter-Regular'),
    'inter-semi': ('Inter',          'SemiBold', 'Inter-SemiBold'),
    'inter-bold': ('Inter',          'Bold',     'Inter-Bold'),
}

BODY_LEAD = 15.5

# paragraph styles; omitted keys inherit from 'based'
PARA = {
    'Body': dict(font='serif', size=11, lead=BODY_LEAD, after=5, color='Black',
                 align='left', hyph=True, figs='ProportionalLining'),
    'Body First': dict(based='Body'),
    'Sign-off': dict(based='Body', before=5),
    'Numbered List': dict(based='Body', left=18, first=-18, tabs=[18]),
    'Kicker': dict(font='inter-semi', size=10, lead=12, after=10, color='Honey Gold',
                   caps=True, track=180, hyph=False, keep_next=True),
    'H1': dict(font='inter-bold', size=22, lead=24, after=28, color='Navy',
               hyph=False, keep_next=True),
    'H2': dict(font='inter-semi', size=14, lead=16, before=20, after=7, color='Navy',
               hyph=False, keep_next=True),
    'Worksheet Title': dict(font='inter-bold', size=16, lead=18, before=31, after=10,
                            color='Navy', hyph=False, keep_next=True,
                            rule_above=dict(weight=1, color='Black', offset=20)),
    'H3 Step': dict(font='inter-semi', size=11.5, lead=14, before=14, after=5,
                    color='Navy', hyph=False, keep_next=True),
    'Formula Label': dict(font='inter-semi', size=8.5, lead=11, after=5, color='Mid Gray',
                          caps=True, track=150, align='center', hyph=False, keep_next=True),
    'Formula Label Second': dict(based='Formula Label', before=12),
    'Formula Line': dict(font='inter-semi', size=12, lead=16, color='Navy',
                         align='center', hyph=False, figs='ProportionalLining'),
    'Formula Line Second': dict(based='Formula Line', before=8),
    'Table Body': dict(font='inter', size=9.5, lead=13, color='Black', hyph=False,
                       figs='TabularLining'),
    'Table Body Center': dict(based='Table Body', align='center'),
    'Table Number': dict(based='Table Body', font='inter-semi', color='Navy'),
    'Table Result': dict(based='Table Body', font='inter-bold', color='Navy'),
    'Table Header': dict(font='inter-semi', size=8.5, lead=11, color='Paper', caps=True,
                         track=60, hyph=False),
    'Table Header Center': dict(based='Table Header', align='center'),
    # Appendix reference table: TSA fallback size (9/12) so it holds one 6x9 page
    'Appendix Body': dict(based='Table Body', size=9, lead=12),
    'Appendix Body Center': dict(based='Appendix Body', align='center'),
    'Appendix Number': dict(based='Appendix Body', font='inter-semi', color='Navy'),
    'Appendix Header': dict(based='Table Header', size=8, lead=10),
    'Appendix Header Center': dict(based='Appendix Header', align='center'),
    'Table Anchor': dict(font='inter', size=4, lead=4, color='Black', hyph=False),
    'Folio': dict(font='inter', size=9, lead=11, color='Mid Gray', align='center'),
    'Title': dict(font='inter-bold', size=30, lead=34, after=0, color='Navy', hyph=False,
                  rule_below=dict(weight=0.75, color='Honey Gold', offset=16, length=72)),
    'Title Subtitle': dict(font='inter', size=13, lead=17, before=34, after=40,
                           color='Mid Gray', hyph=False),
    'Title Author': dict(font='inter-semi', size=12, lead=15, color='Navy', hyph=False),
    'Title Imprint': dict(font='inter', size=9, lead=12, color='Mid Gray', hyph=False),
    'Copyright': dict(font='serif', size=8.5, lead=12, after=6, color='Black', hyph=False),
    'Contents Entry': dict(font='serif', size=11, lead=15.5, after=9, color='Black',
                           hyph=False, tabs=[('right', 338.4)]),
}

CHAR = {
    'Run-in': dict(font='serif-semi'),
    'Semibold': dict(font='serif-semi'),
    'Italic': dict(font='serif-it'),
    'Inter Numeral': dict(font='inter'),
    'Fill-in Rule': dict(underline=0.5),
}


def resolved(name):
    s = PARA[name]
    base = resolved(s['based']) if 'based' in s else dict(
        before=0, after=0, align='left', caps=False, track=0, left=0, first=0,
        hyph=False, keep_next=False, figs=None, tabs=None)
    out = dict(base)
    out.update({k: v for k, v in s.items() if k != 'based'})
    return out
