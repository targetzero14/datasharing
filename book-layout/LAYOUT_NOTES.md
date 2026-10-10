# Marketing by the Numbers: 6×9 KDP layout notes

## Files
- **Marketing_by_the_Numbers_KDP_6x9.idml**: the layout. In Affinity, use **File → Open** and pick the .idml.
- **Marketing_by_the_Numbers_KDP_6x9_proof.pdf**: a reference proof of the intended layout, made with a different typesetter. Use it to compare against what Affinity shows. Don't upload it to KDP.

## Before opening
Install **Inter** (Regular, SemiBold, Bold) and **Source Serif 4** (Regular, Italic, SemiBold) from Google Fonts. If a font is missing, Affinity substitutes another and the line breaks will differ.

## What's built
- 73 pages at 6×9 with KDP margins: 0.75" top, 0.85" bottom, 0.75" inside, 0.55" outside. Facing pages, no bleed.
- Page numbers: roman for the front matter (i–vi), then arabic starting at 1 on the Introduction.
- Every chapter, plus the front-matter sections, opens on a right-hand page. Openers start 5 body lines down the page.
- Masters: **A-Body** has a centered 9 pt Inter folio. **B-No Folio** is used for the title page, copyright page, openers and blank pages.
- One linked story per chapter, so text reflows inside a chapter without pushing later chapters. Blank left-hand pages at chapter ends are linked into the story as spare room.
- 32 paragraph styles and 5 character styles, named after the TSA tags (Body, H1, H2, Worksheet Title, H3 Step, Kicker, Formula Label/Line, Table Body/Result/Header, Folio, and so on).
- Swatches are set to black-only KDP values: Navy = K100, Honey Gold = K60, Mid Gray = K100, Light Gray = K12, Hairline = K40. The brand RGB versions are also included ("… (Gumroad RGB)") for the 8.5×11 build.
- Formula bands G1–G8 are built as one-cell tables placed in the text, so they move with it: Light Gray fill, 0.5 pt black rules, 14 pt padding.
- 27 worksheet tables plus the Appendix table. Underscore runs are replaced with 0.5 pt fill-in rules (an underline character style), answer rows are at least 0.35" tall, alternating rows are banded, and result rows have a 1 pt rule above.
- Contents page numbers are filled in from this page plan.

## Decisions I made (easy to change)
1. **Ch 3 band** reads "Customers ÷ leads × 100", matching the Appendix (default).
2. **Ch 6 and Ch 7 bands** stay where the manuscript places them (default).
3. **Ch 8 band** includes the optional second line, "If it doubled tomorrow, would your revenue change?" (default).
4. **Chain diagram (G9)** is not built (default).
5. **Ch 2 band (G2):** the requested break after "years they stay," can't fit on one line at 12 pt in a 6×9 band, since that phrase alone is about 334 pt wide and the band has about 310 pt. It now sets as three centered lines. The alternative is a local 11 pt size, which fits on two lines.
6. **Baseline grid:** the grid is set up (15.5 pt from the top margin), but body text is **not** snapped to it. With snapping on, the spec's 5 pt space after each paragraph turns into a full 15.5 pt blank line. To use the grid, set Body's space after to 0 or 15.5 and turn on snapping in the Body style.
7. **Body alignment:** ragged right with hyphenation on. The spec doesn't say whether to justify; switching is one setting in the Body style.
8. **Em dashes** are closed up in running text and tables, per the TSA assembly note. The source still had spaces around them. Headings, step heads and Contents entries keep spaced dashes.
9. **Copyright page:** the "Copyright" label is dropped and the text sits at the bottom of the page.
10. **Title page:** the title breaks as "Marketing / by the Numbers", with a 72 pt rule under it.
11. **Appendix table:** uses the TSA fallback size of 9/12, starts on a new page and fits on one page.
12. **Worksheet 8, Steps 1 and 3:** five write-in rules added under each, because those steps had nowhere to write.
13. **Worksheet 1, Step 1, first row:** fixed a split in the source, where "L | ast 90 days" now reads "Last 90 days".

## Check after opening in Affinity
- **Overflow:** look for red overflow markers at chapter ends. The page plan comes from the proof's typesetter and may differ slightly from Affinity's.
- **Paragraph rules:** the gold (KDP: black) rule above Worksheet titles and the short rule under the title are paragraph rules. If Affinity's import drops them, add them in the *Worksheet Title* and *Title* styles (Paragraph Decorations).
- **Table fills and strokes** were set cell by cell. Check one worksheet table and one band.
- **Fill-in rules** are underlined non-breaking spaces. If any line is missing, check the *Fill-in Rule* character style.
- **Folios** come from the master text frames' page-number field.
- Before exporting, run Separations Preview (black only) and export PDF/X-1a:2001 with fonts embedded.

## Still open for Allen
- Revision letters: the files supplied are one revision earlier than the TSA calls for.
- Worksheet "Think it through" questions have no space to write answers. Add write-in lines?
- Should worksheets start on a fresh page, so they're easier to photocopy? (This adds pages.)
