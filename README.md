# ShopIL Plugin

[![CI](https://github.com/eldarush/shopil-plugin/actions/workflows/ci.yml/badge.svg)](https://github.com/eldarush/shopil-plugin/actions/workflows/ci.yml)

A Claude Code and Codex plugin for Jira-owned development work: ticket-linked branches, Conventional Commits, verification before Done, the bundled Ponytail skill, and a complete snapshot of the downloaded ShopIL course materials.

## Intended use

Install this plugin in each teammate's coding agent, then open your clone of the ShopIL application repository. It gives the agent the course context and shared development rules for implementing the Hebrew business assistant: batch ETL, continuous streaming, evidence-backed Actor/Critic chat, experiments and submission documentation.

This repository distributes the plugin. Your implementation belongs in the team's application repository. Each teammate signs into Atlassian independently; the plugin uses that authenticated account's ID and only permits covered updates to that user's assigned SHOPIL tickets. It never treats every installer as the repository owner.

The course bundle is a snapshot from **November 13, 2026**. The observed assignment deadline is **November 25, 2026 at 00:00 Asia/Jerusalem** (the night ending November 24); check Moodle for changes. The source-indexed assignment is authoritative for coursework. Branch names, Conventional Commits and Jira ownership gates are the team's development conventions.

## What it includes

- **Jira workflow:** read the real acceptance criteria; use actual transitions; tie PRs, tests and completion evidence back to the ticket.
- **Per-user ownership:** resolve the authenticated Jira `accountId` every session. Only modify tickets whose assignee exactly matches it. Unassigned and other people's tickets are read-only. Duplicate names do not match. Recheck ownership before each write, including completion. Never create tasks unless explicitly requested. No installer identity is hardcoded.
- **Git checks:** ticket-scoped branch names, Conventional Commit messages/PR titles, matching ticket keys, Jira link and validation in PRs, no direct main-branch commits/pushes through installed hooks, and blocked secret/database filenames.
- **Ponytail:** the user's MIT-marked skill bundled locally, requiring the smallest complete solution and meaningful checks.
- **ShopIL context:** 15 byte-verified originals (assignment, seven presentations, five PDFs, two complete lab ZIPs), 13 searchable text extracts including available slide notes, source/hash index, implementation requirements and Jira task mapping. Instructor solutions are explicitly reference-only. Annual-project documents are labeled supplemental, not ShopIL requirements.
- **CI and tests:** standard-library Python unit/integration tests on Windows/Linux and Python 3.14.10; real Git-hook rejection tests; ownership and account-switch scenarios; material checksums and reproducible release packaging.

## Install in Codex

### Python runtime

Use the latest stable **Python 3.14.x**, currently **3.14.10** (verified November 13, 2026), for the plugin, its Git checker and tests. The verified patch is pinned in `.python-version`, CI and the downstream workflow template so installations and validation agree. A future 3.14 patch requires updating and testing the pin; Python 3.15 is not selected.

On Windows, install the [official Python install manager](https://www.python.org/downloads/) if needed, then run:

```powershell
pymanager install 3.14.10
py -3.14 --version
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
```

The version checks should print `Python 3.14.10`. On Linux/macOS, install [Python 3.14.10](https://www.python.org/downloads/release/python-31410/), then create and activate a virtual environment with `python3.14 -m venv .venv` and `source .venv/bin/activate`.

Native hooks use the current interpreter if it is 3.14.10, otherwise they probe `py -3.14` on Windows and `python3.14`/`python3` on PATH. They reject an unavailable or mismatched runtime. The initial `python` command can be an older Python 3 interpreter; actual hook policy runs on 3.14.10. Standalone Git checks and packaging require 3.14.10 directly. Install per-clone Git hooks from the activated environment so they retain that interpreter's absolute path.

This runtime update validates the plugin. Keep lecturer lab environments separate until their third-party application dependencies have been tested on 3.14.10.

With a Codex CLI that supports `plugin`:

```sh
codex plugin marketplace add eldarush/shopil-plugin --ref v2.1.0
codex plugin add shopil-plugin@shopil-plugins
```

Restart or open a new Codex session if the installed skills do not appear. Connect the Atlassian plugin using your own Jira account; use the existing GitHub connector or authenticated GitHub CLI for repository operations. This package never shares the author's credentials or stores access tokens. Each teammate installs and authenticates independently.

Trust the installed hooks using `/hooks` (CLI) or the desktop hook review UI. Re-review changed hook code on upgrades. Python 3.14.10 must be installed. The hook launcher selects it even if the host's `python` points to an older interpreter; see the runtime setup below.

Invoke `$jira-workflow` for a task and `$shopil-project` for assignment context. The workflow explicitly reads its bundled `$ponytail` skill. The standalone Git checker supports configurable project keys; the native agent ownership hooks deliberately target SHOPIL.

The release ZIP contains the portable plugin root (`plugin.json`, `.claude-plugin/`, `hooks/`, `skills/`, license and notices). The repository supplies marketplaces for both hosts. GitHub publication is not approval or listing in a host's official plugin directory.

## Install in Claude Code

```sh
claude plugin marketplace add eldarush/shopil-plugin
claude plugin install shopil-plugin@shopil-plugins
```

Open a new session, review/trust the hooks when prompted, and connect Atlassian with your own account. Invoke `/shopil-plugin:jira-workflow` or `/shopil-plugin:shopil-project`. Python 3.14.10 and Git are required. A `python` command is needed to bootstrap the hook launcher, which selects the pinned runtime. See [setup](plugins/shopil-plugin/skills/jira-workflow/references/setup.md) for per-clone Git checks and CI.

## Daily team workflow

1. Open the application checkout and select an existing ticket assigned to you. Read its acceptance criteria and the relevant assignment sections. If the ticket is unassigned or belongs to someone else, keep it read-only; arrange assignment in Jira. Do not create new tickets unless explicitly asked.
2. Ask the agent to use `jira-workflow` and `shopil-project`. It reads your current Atlassian identity and the full issue, discovers available transitions, and moves your ticket to In Progress within your authorized task.
3. Work on `feature/SHOPIL-N-short-description` (or an appropriate `fix`, `test`, `docs`, `ci` prefix). Use Ponytail to keep the change small and complete. Run the actual component/integration checks required by the ticket, not just the plugin tests.
4. When authorized, commit with a Conventional Commit containing the ticket key, push the branch, and open a PR with the Jira link and test evidence. Pass current-head CI and the team's review requirements before merging.
5. Refresh Jira ownership, record the real PR/test results, and move only your ticket to Done after its acceptance criteria are met. A green convention check alone is not completion.

Example task prompt, replacing the key with your own assigned ticket:

> Use jira-workflow, shopil-project and Ponytail for SHOPIL-13. Read my current Jira identity and the full ticket, then implement its acceptance criteria using the bundled assignment and lab starters. Run the relevant tests. Do not create tickets or change other people's tasks. Ask before publishing unless I have already authorized it.

For first-time repository configuration, explicitly request: “Configure this checkout's Git hooks, PR template and CI using the plugin; preserve existing setup.” The detailed [setup guide](plugins/shopil-plugin/skills/jira-workflow/references/setup.md) covers bootstrap order and branch protection. Installing the plugin activates host hooks only after trust; it does not install Git hooks or change GitHub rules in every clone.

## Contents and where to look

| Component | Purpose |
| --- | --- |
| [jira-workflow](plugins/shopil-plugin/skills/jira-workflow/SKILL.md) | Ticket ownership, branches, commits, PRs, tests and truthful completion |
| [shopil-project](plugins/shopil-plugin/skills/shopil-project/SKILL.md) | Assignment requirements, grading, lab setup and relevant source selection |
| [Ponytail](plugins/shopil-plugin/skills/ponytail/SKILL.md) | Small, complete implementations with meaningful verification |
| [Requirements](plugins/shopil-plugin/skills/shopil-project/references/requirements.md) | Full ETL, streaming, chat, experiments and submission contract |
| [Course index](plugins/shopil-plugin/skills/shopil-project/references/course-index.md) | 15 originals, 13 extracts, lab notebooks/starters, source links and hashes |
| [Jira map](plugins/shopil-plugin/skills/shopil-project/references/jira-map.md) | Task-to-requirement snapshot; always read live ownership and status |
| [Native hooks](plugins/shopil-plugin/hooks/agent_hook.py) | Session context and observed per-user Jira/branch checks |
| [Git checker](plugins/shopil-plugin/skills/jira-workflow/scripts/guard.py) | Local commit/push checks and PR convention validation |

The source bundle includes the assignment DOCX, six AI lecture presentations, the syllabus, two complete lecturer lab archives, and supplemental annual-project material (one presentation and four proposal PDFs). Supplemental capstone files do not add ShopIL requirements. Instructor solutions are reference material, not your own implementation or test evidence.

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

The checker is `plugins/shopil-plugin/skills/jira-workflow/scripts/guard.py` and needs Python 3.14.10 plus Git. Use the course guides' separate environments for the actual ETL/Streaming application.

```sh
python path/to/guard.py branch --repo path/to/repo
python path/to/guard.py pre-commit --repo path/to/repo
python path/to/guard.py jira --repo path/to/repo --issue-file /safe/issue.json --identity-file /safe/current-user.json --ticket SHOPIL-13 --phase work
```

For standalone Jira checks, unwrap fresh connector/API responses into issue `{key, fields}` and current-user `{accountId}` objects. Keep these private snapshots outside tracked files. `start` accepts To Do or In Progress, `work` and `finish` require In Progress. All phases require exact ownership. Native hooks observe these reads automatically. Explicitly requested creation or assignment must be performed manually in Jira because the native hooks block automated exceptions; read back ownership before any further automated update.

## Enforcement boundaries

Skills and native hooks are workflow guardrails, not a security sandbox. Supported tool names/envelopes are tested, but arbitrary shell programs, disabled/untrusted hooks, unsupported host tools and host startup failures can bypass coverage. Claude PreToolUse is configured to block hook failures; Codex host failures may fail open. Verify hooks are active in your actual host before relying on them. Live Claude/Codex agent sessions and live LLM behavior are not exercised by this repository's CI. Server-side enforcement needs required PR/CI checks and GitHub branch protection. The checker validates Jira response snapshots; it does not authenticate or call Jira, and cannot atomically prevent a reassignment between reading an issue and updating it. Use Jira permissions/workflow validators for a server-side ownership guarantee. No task is marked Done by a commit keyword or a green convention check alone.

The filename guard is not a secret-content scanner. Review diffs and use repository secret scanning where available. Do not execute untrusted PR code with secrets. The supplied downstream CI template loads policy from the trusted base branch. This plugin repository's own CI tests proposed plugin code with read-only permissions and no secrets; policy changes still require code review.

The project guide distinguishes mandatory assignment work from optional labs. Bundled instructor reports are not evidence of your application's test results. CI here tests the plugin and assets, not the ShopIL application or live LLM behavior.

## Develop and verify

No runtime or test dependencies beyond Python 3.14.10 and Git:

```sh
python -m unittest discover -s tests -v
python scripts/package_plugin.py
```

The second command writes a deterministic plugin ZIP and SHA-256 file under `dist/`. GitHub Actions executes the same tests and package build on both operating systems with the pinned Python version. The test suite creates isolated temporary repositories, exercises actual hooks, and makes no Jira API writes.

## Migration from jira-workflow-guard

This repository preserves the original Git history, historical `v1.0.0` tag, course file bytes, extracted text, skills, checker and tests. Only the updated `v2.1.0` release is published; the old release is not offered for installation. The old GitHub repository is retired after verification. Historical release/PR/CI records are exported under `migration/` because GitHub does not transfer their identities between repositories.

Remove the old plugin if installed, then remove its marketplace registration:

```sh
codex plugin remove jira-workflow-guard@eldarush-workflows
codex plugin marketplace remove eldarush-workflows
```

Install the new marketplace/plugin using the commands above. Existing implementation-repository hooks referencing an old plugin cache must be reviewed and reinstalled from a copied checker; never overwrite another hook manager.

## Sources and licensing

Original plugin code/documentation: [MIT](LICENSE). See [third-party notices](plugins/shopil-plugin/THIRD_PARTY_NOTICES.md) for Ponytail and course materials. The root manifest's MIT license does not relicense lecturer documents/code. Source links and original hashes are included in the [course index](plugins/shopil-plugin/skills/shopil-project/references/course-index.md).

Packaging follows the [OpenAI plugin documentation](https://developers.openai.com/plugins/build/plugins); commit subjects follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/), with additional ticket/type rules for this project.
