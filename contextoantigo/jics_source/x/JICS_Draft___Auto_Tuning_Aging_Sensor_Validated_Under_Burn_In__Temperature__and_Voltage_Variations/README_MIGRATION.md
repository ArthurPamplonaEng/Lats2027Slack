# JICS migrated project

This project was migrated from the SBCCI/IEEE conference LaTeX source to the Journal of Integrated Circuits and Systems (JICS) LaTeX template.

Root file: `main.tex`

Migration scope performed here:
- Replaced `IEEEtran` conference class with `JICS_LaTexGuidelines.cls`.
- Added the JICS geometry block from the official bare template.
- Converted the author/title/header block to the JICS template structure.
- Converted `IEEEkeywords` to the JICS `indexterms` environment.
- Preserved the original technical body text, figures, tables, citations, and bibliography entries.
- Kept `IEEEtran` bibliography style, as used in the JICS bare LaTeX example.

Placeholders to review before submission:
- `vol. XX, n. XX, 2026` in `\markboth`.
- `Digital Object Identifier 10.29292/jics.vXXiX.X`.
- Contact e-mail in the author block, if JICS requests a different corresponding author.
