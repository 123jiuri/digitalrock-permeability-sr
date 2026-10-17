# Code-only upload checklist

- Verify repository visibility remains private before and after the push.
- Include only source, configuration, documentation, tests and the existing license.
- Inspect `git diff --cached --name-status` and every staged file; do not rely only on `.gitignore`.
- Exclude all numeric tables, IDs paired with observations, labels, run metadata, logs, checkpoints and scientific outputs.
- Scan staged text for access tokens, credentials, absolute user/workspace paths and private URLs.
- Run the synthetic unit suite with the locked research interpreter.
- Check that the formal configuration matches the archived ten-fold, twelve-seed protocol.
- Record local parity/dry-run checks outside the repository; do not commit their inputs or results.
- Preserve the earlier package in Git history; use a normal fast-forward push, never force-push or rewrite history.
- Do not tag a release as scientifically reproduced unless a full controlled rerun has been completed and audited.
