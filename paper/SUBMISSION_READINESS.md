# Paper 1 Submission Readiness

Snapshot date: 2026-07-18

## Ready artifacts

- Anonymous single-column review PDF: `output/pdf/paper1_chi_review.pdf`
- Canonical LaTeX body: `paper/main_updating_CHI.md`
- Anonymous review entry: `paper/paper1_chi_review.tex`
- Bibliography: `paper/refs.bib`
- Claim-to-evidence matrix: `paper/CLAIM_EVIDENCE_MATRIX.md`
- Public aggregate evidence: `cognitive-trajectory/evidence/paper1/`
- Submission-form copy: `paper/SUBMISSION_FORM_COPY.md`

## Completed checks

- Default review build uses `manuscript,review,anonymous`.
- PDF compiles successfully with bibliography.
- PDF is 16 US-letter pages and has no author metadata field.
- Author name, email, local paths, and GitHub identity are absent from the review PDF/source entry.
- Figures, tables, algorithms, references, and page flow were visually inspected after rendering.
- All current manuscript numbers map to the deduplicated 1,122-session evidence snapshot.
- Historical 3,048-graph metrics, the 29.5% overlap claim, length-control claims, and Paper 2 behavioral results are excluded.
- The evidence summary contains aggregate metrics and hashes only, not raw personal text.

## Submission-time fields that cannot be completed in the repository

These are portal and venue choices, not manuscript defects:

1. Confirm the target CHI cycle/track and its deadline-specific call.
2. Enter the full author list/order and affiliations in PCS.
3. Complete conflicts, reviewer suggestions, funding, and ACM policy declarations.
4. Confirm the final wording for ethics/consent and research-involving-humans disclosures with the authors' institutional requirements.
5. Upload only the anonymous review package; exclude `main_camera_ready.tex` and any Git history or supplement that reveals identity if the venue requires anonymous supplements.

## Packaging recommendation

Review upload:

- `paper1_chi_review.pdf`

Optional anonymous supplement:

- code/evidence repository snapshot without raw conversations
- `EVIDENCE_MANIFEST.md`
- `paper1_results_summary.json`
- sample data and reproduction guide

Camera-ready materials should be generated only after acceptance and after author metadata is restored through `main_camera_ready.tex`.
