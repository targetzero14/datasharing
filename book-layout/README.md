# Book layout generator (6×9 KDP → Affinity via IDML)

Builds an Affinity-importable IDML and a PDF proof from the tagged master manuscript (.docx).

```
pip install reportlab pyphen fonttools brotli
FONT_DIR=/path/to/ttfs python3 build.py Manuscript_Tagged.docx out/
```

`FONT_DIR` must hold EBG-Regular/Italic/SemiBold.ttf and Jost-Regular/Medium/SemiBold.ttf (used for the proof and page planning).

- `parse_docx.py`: reads the docx and drops layout tags and notes
- `model.py`: book structure, plus the layout decisions applied to the text
- `styles.py`: the style sheet (TSA spec, KDP black-only values)
- `proof.py`: typesets with ReportLab to plan pages and draw the proof PDF
- `idml.py`: writes the IDML package

See `LAYOUT_NOTES.md` for what's built and which decisions were made.
