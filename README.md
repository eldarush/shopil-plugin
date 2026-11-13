# ShopIL Plugin

[![CI](https://github.com/eldarush/shopil-plugin/actions/workflows/ci.yml/badge.svg)](https://github.com/eldarush/shopil-plugin/actions/workflows/ci.yml)

A Claude Code and Codex plugin for Jira-owned development work: ticket-linked branches, Conventional Commits, verification before Done, the bundled Ponytail skill, and a complete snapshot of the downloaded ShopIL course materials.

## What it includes

- **Jira workflow:** read the real acceptance criteria; use actual transitions; tie PRs, tests and completion evidence back to the ticket.
- **Per-user ownership:** resolve the authenticated Jira `accountId` every session. Only modify tickets whose assignee exactly matches it. Unassigned and other people's tickets are read-only. Duplicate names do not match. Recheck ownership before each write, including completion. Never create tasks unless explicitly requested. No installer identity is hardcoded.
- **Git checks:** ticket-scoped branch names, Conventional Commit messages/PR titles, matching ticket keys, Jira link and validation in PRs, no direct main-branch commits/pushes through installed hooks, and blocked secret/database filenames.
- **Ponytail:** the user's MIT-marked skill bundled locally, requiring the smallest complete solution and meaningful checks.
- **ShopIL context:** 15 byte-verified originals (assignment, seven presentations, five PDFs, two complete lab ZIPs), 13 searchable text extracts including available slide notes, source/hash index, implementation requirements and Jira task mapping. Instructor solutions are explicitly reference-only. Annual-project documents are labeled supplemental, not ShopIL requirements.
- **CI and tests:** standard-library Python unit/integration tests on Windows/Linux and Python 3.11/3.13; real Git-hook rejection tests; ownership and account-switch scenarios; material checksums and reproducible release packaging.

## Install in Codex

With a Codex CLI that supports `plugin`:

```sh
codex plugin marketplace add eldarush/shopil-plugin --ref v2.0.0
codex plugin add shopil-plugin@shopil-plugins
```

Restart or open a new Codex session if the installed skills do not appear. Connect the Atlassian plugin using your own Jira account; use the existing GitHub connector or authenticated GitHub CLI for repository operations. This package never shares the author's credentials or stores access tokens. Each teammate installs and authenticates independently.

Trust the installed hooks using `/hooks` (CLI) or the desktop hook review UI. Re-review changed hook code on upgrades. Python 3.11+ must be available as `python` on PATH.

Invoke `$jira-workflow` for a task and `$shopil-project` for assignment context. The workflow explicitly reads its bundled `$ponytail` skill. The standalone Git checker supports configurable project keys; the native agent ownership hooks deliberately target SHOPIL.

The release ZIP contains the portable plugin root (`plugin.json`, `skills/`, license and notices). The repository also supplies a Codex marketplace for installation. GitHub publication is not approval or listing in OpenAI's universal plugin directory.

## Install in Claude Code

```sh
claude plugin marketplace add eldarush/shopil-plugin
claude plugin install shopil-plugin@shopil-plugins
```

Open a new session, review/trust the hooks when prompted, and connect Atlassian with your own account. Invoke `/shopil-plugin:jira-workflow` or `/shopil-plugin:shopil-project`. Python 3.11+ (`python` on PATH) and Git are required. See [setup](plugins/shopil-plugin/skills/jira-workflow/references/setup.md) for per-clone Git checks and CI.

## Native agent hooks

- SessionStart supplies the assignment contract, grading, deadline snapshot and installed paths to every original and extract when opened in a ShopIL repository.
- PostToolUse observes current-user and full-issue reads from the Atlassian connector. Only account IDs establish ownership. It never calls Jira itself.
- PreToolUse blocks covered Jira writes without matching fresh identity/assignee evidence. Proof expires after 120 seconds, is isolated by session and repository, and is consumed before each Jira write. Read the issue again before the next write. Creation, bulk changes, reassignment and unknown writes are blocked by default; explicitly requested creation/assignment must be done manually in Jira.
- Covered file edits and shell commands in a ShopIL repository require a ticket branch and an owned In Progress issue. A small read-only shell allowlist permits inspection before setup. Main-branch edits, common hook bypasses and direct shell Jira requests are rejected.

Hooks recognize a SHOPIL `.workflow-guard.json` or an origin named `shopil`/`shopil-plugin`. A teammate clone with another name needs the configuration. Use `getJiraIssue(view="full")`: compact responses containing only display names invalidate ownership evidence. On denial, refresh real reads; never manufacture hook state. Local minimal account/assignee metadata lives in the OS temporary directory `shopil-plugin-hooks`; no tokens or ticket descriptions are stored.

## Activate enforcement in an implementation repository

Installing this plugin does **not** modify another repository. Ask it to configure workflow checks there, then review the proposed changes. The [setup instructions](plugins/shopil-plugin/skills/jira-workflow/references/setup.md) describe copying the checker/config, integrating existing hooks, adding CI and applying branch rules. The separate `eldarush/shopil` repository is intentionally left empty by this project.

Default examples:

```text
feature/SHOPIL-13-reviews-loader
feat(etl): load reviews [SHOPIL-13]
fix(streaming)!: correct event contract [SHOPIL-17]
```

Configuration (`.workflow-guard.json`):

```json
{"project_keys": ["SHOPIL"], "main_branch": "main"}
```

The checker is `plugins/shopil-plugin/skills/jira-workflow/scripts/guard.py` and needs Python 3.11+ plus Git. Use the course guides' separate environments for the actual ETL/Streaming application.

```sh
python path/to/guard.py branch --repo path/to/repo
python path/to/guard.py pre-commit --repo path/to/repo
python path/to/guard.py jira --repo path/to/repo --issue-file /safe/issue.json --identity-file /safe/current-user.json --ticket SHOPIL-13 --phase work
```

For Jira checks, unwrap fresh connector/API responses into issue `{key, fields}` and current-user `{accountId}` objects. Keep these private snapshots outside tracked files. `start` accepts To Do or In Progress, `work` and `finish` require In Progress. All phases require exact ownership. A direct, explicit request to assign one specific ticket to yourself is the only documented assignment exception; it requires checking assignability and reading back ownership before any further update.

## Enforcement boundaries

Skills and native hooks are workflow guardrails, not a security sandbox. Supported tool names/envelopes are tested, but arbitrary shell programs, disabled/untrusted hooks, unsupported host tools and host startup failures can bypass coverage. Claude PreToolUse is configured to block hook failures; Codex host failures may fail open. Verify hooks are active in your actual host before relying on them. Live Claude/Codex agent sessions and live LLM behavior are not exercised by this repository's CI. Server-side enforcement needs required PR/CI checks and GitHub branch protection. The checker validates Jira response snapshots; it does not authenticate or call Jira, and cannot atomically prevent a reassignment between reading an issue and updating it. Use Jira permissions/workflow validators for a server-side ownership guarantee. No task is marked Done by a commit keyword or a green convention check alone.

The filename guard is not a secret-content scanner. Review diffs and use repository secret scanning where available. Do not execute untrusted PR code with secrets. The supplied downstream CI template loads policy from the trusted base branch. This plugin repository's own CI tests proposed plugin code with read-only permissions and no secrets; policy changes still require code review.

The project guide distinguishes mandatory assignment work from optional labs. Bundled instructor reports are not evidence of your application's test results. CI here tests the plugin and assets, not the ShopIL application or live LLM behavior.

## Develop and verify

No runtime or test dependencies beyond Python 3.11+ and Git:

```sh
python -m unittest discover -s tests -v
python scripts/package_plugin.py
```

The second command writes a deterministic plugin ZIP and SHA-256 file under `dist/`. GitHub Actions executes the same tests and package build on four OS/Python combinations. The test suite creates isolated temporary repositories, exercises actual hooks, and makes no Jira API writes.

## Migration from jira-workflow-guard

This repository preserves the original Git history, `v1.0.0` tag, course file bytes, extracted text, skills, checker and tests. The legacy release assets are retained unchanged under `v1.0.0`; use `v2.0.0` for the renamed plugin and native hooks. The old GitHub repository is retired after verification. Historical PR/CI records are exported under `migration/` because GitHub does not transfer their identities between repositories.

Remove the old plugin if installed, then remove its marketplace registration:

```sh
codex plugin remove jira-workflow-guard@eldarush-workflows
codex plugin marketplace remove eldarush-workflows
```

Install the new marketplace/plugin using the commands above. Existing implementation-repository hooks referencing an old plugin cache must be reviewed and reinstalled from a copied checker; never overwrite another hook manager.

## Sources and licensing

Original plugin code/documentation: [MIT](LICENSE). See [third-party notices](plugins/shopil-plugin/THIRD_PARTY_NOTICES.md) for Ponytail and course materials. The root manifest's MIT license does not relicense lecturer documents/code. Source links and original hashes are included in the [course index](plugins/shopil-plugin/skills/shopil-project/references/course-index.md).

Packaging follows the [OpenAI plugin documentation](https://developers.openai.com/plugins/build/plugins); commit subjects follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/), with additional ticket/type rules for this project.
