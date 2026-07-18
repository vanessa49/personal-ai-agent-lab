# Paper 1 Manuscript

## Source of truth

`main_updating_CHI.md` is the only canonical manuscript body. Despite its extension, it is LaTeX.

- `paper1_chi_review.tex`: anonymous, single-column review entry point
- `main.tex`: compatibility alias for the same anonymous review build
- `main_camera_ready.tex`: named, two-column preview; never upload for anonymous review
- `refs.bib`: bibliography
- `../output/pdf/paper1_chi_review.pdf`: compiled review PDF

Do not edit the older `paper__CHI_.pdf` or `paper__CHI_2.pdf`; they are historical compiled artifacts.

## Build

With a standard TeX installation:

```powershell
cd paper
latexmk -pdf paper1_chi_review.tex
```

With Tectonic:

```powershell
cd paper
tectonic --outdir ..\output\pdf paper1_chi_review.tex
```

The review entry defaults to `\documentclass[manuscript,review,anonymous]{acmart}`. The camera-ready wrapper explicitly switches the same canonical source to `sigconf` and supplies the author name.

## Evidence

Use [`CLAIM_EVIDENCE_MATRIX.md`](CLAIM_EVIDENCE_MATRIX.md) for manuscript-to-result traceability. The public aggregate evidence package lives in `../cognitive-trajectory/evidence/paper1/`.

Paper 2 behavioral evidence is outside this manuscript's scope and must not be copied into Paper 1 tables or claims.
