# Migration record

The former public repository was `eldarush/jira-workflow-guard`. The new canonical repository is `eldarush/shopil-plugin`.

- Original main commit and `v1.0.0`: `06fb12e0f1f04f737faf5b59f929b351ab6adc60`.
- Original feature branch: `feature/SHOPIL-47-workflow-plugin`, commit `37d75cf638354d8fc38b3386a0fb67e8dcc8e05e`.
- Both histories and the original release tag are retained. Legacy ZIP/checksum assets are published unchanged under `v1.0.0`; they contain the former plugin name. Install the new `v2.0.0` release.
- All 15 course originals and 13 extracts compare byte-for-byte. Ponytail, the Git checker, licenses and notices are retained (plugin-name substitution where applicable). All prior tests remain, with native hook tests added.
- `verification.json` records source hashes and comparison results. `legacy-github-metadata.json` preserves public repository settings, release metadata, the original PR and discussions/reviews, and CI run metadata as of 2026-11-13.

GitHub PR numbers, run IDs, stars and creation timestamps cannot be transferred into a newly created repository. The export preserves their historical record; old URLs may no longer resolve after deletion. New CI runs and branch protection are configured on the new repository. The separate ShopIL application repository is not modified by this migration.
