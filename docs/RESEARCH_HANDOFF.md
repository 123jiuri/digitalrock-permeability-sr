# Research handoff and release policy

This project is maintained as two linked but separate artifacts:

1. **Public code repository**: reusable preprocessing, symbolic-regression,
   formula-family, evaluation, and audit code. It contains no digital-rock
   images or private result archives.
2. **Data and experiment archive**: descriptor tables, split definitions,
   experiment outputs, source data for figures and supplementary tables, and
   the raw digital-rock images. The raw images are kept outside ordinary Git
   history because the current archive is approximately 17.6 GB.

The bridge between the two artifacts is the experiment registry and data
registry. Every future experiment should receive a stable experiment ID and
record its input table, script or commit, configuration, output directory,
evaluation split, and manuscript location.

## Current manuscript evidence chain

| ID | Question | Main output |
|---|---|---|
| E01 | What descriptor structures recur across sandstone searches? | Recurrent three-descriptor family involving (r_c), ̄(l_{\mathrm{chord}}), and (F) |
| E02 | How is one representative equation selected? | Training-only complexity-7 representative equation |
| E03 | Does the structure persist under controlled perturbations? | Noise, complexity-ceiling, and target-permutation audits |
| E04 | Do the selected descriptors provide complementary information? | Targeted and descriptor-group ablations |
| E05 | How does the explicit equation compare with predictive baselines? | Grouped-CV model comparison on the 20-descriptor input |
| E06 | Does the sandstone relation transfer to carbonate rocks? | Direct coefficient transfer and carbonate-specific recalibration |
| E07 | Does the descriptor-role structure recur in carbonate searches? | Confirmatory recovery of the sandstone-defined structure |
| E08 | How sensitive is the (L_{\mathrm{eff}}^2T_{\mathrm{eff}}) organization to free exponents? | Free-exponent and parent-cluster bootstrap analyses |
| E09 | How should the relation be positioned relative to classical formulations? | Controlled mappings and explicitly labelled proxy comparisons |

## Data policy

- Raw `.raw` digital-rock images remain in the controlled local archive and
  should be distributed through an appropriate repository or data DOI.
- Descriptor tables, split membership, formula archives, metrics, and source
  data should be released in machine-readable CSV/JSON form.
- Generated figures are not primary data; each quantitative figure must point
  to a source-data file and a generating script.
- No target-set or held-out-set information may be used for representative
  equation selection.

## GitHub publication gate

Before pushing, confirm that the repository contains the cleaned public code,
an environment file, a smoke test, documentation for the input schema, and a
data-availability statement. Do not push raw images, private manuscript files,
temporary caches, credentials, or absolute local paths.
