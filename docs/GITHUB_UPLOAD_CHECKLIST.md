# GitHub upload checklist

## Public repository

- [ ] Remove absolute local paths from public scripts.
- [ ] Keep the repository limited to reusable code, schema examples, tests,
      documentation, and small smoke-test outputs.
- [ ] Add a pinned environment file and a one-command smoke test.
- [ ] Add the experiment and data registries.
- [ ] Add a clear data-availability statement and raw-image access policy.
- [ ] Run source preflight and Python import/smoke tests.
- [ ] Review `git diff --stat` and `git status` before the first push.

## Data archive

- [ ] Preserve canonical descriptor tables and split membership.
- [ ] Preserve all final CSV/JSON/Markdown experiment outputs.
- [ ] Preserve raw `.raw` files separately with an inventory and checksums.
- [ ] Preserve figure source-data files and figure-generation scripts.
- [ ] Record the archive date and manuscript version.

## Push gate

The remote URL and GitHub authentication must be supplied or already
configured before `git push` is run. No remote is currently configured for the
public package.
