# Handoff for the main LOPO code

The active entry point is `scripts/run_symbolic_regression.py`, with
`configs/sandstone_lopo.json`. Its scope is the open sandstone search and immediate
post-search algebraic summaries. Read `README.md` and `docs/input_schema.md` first.

The previous generic interface and its cross-experiment registries were retired
from the current working tree because they describe older split-based workflows
and unrelated experiments. They remain recoverable at Git commit `40690cb`.
No raw or processed study data are included in this revision.

Use one new output directory per fixed input/configuration/code/environment
identity. Keep any data release and scientific result archive separate from this
code repository. Future work on independent tests or controls should be added as
an explicitly scoped revision rather than implied by this search-only package.
