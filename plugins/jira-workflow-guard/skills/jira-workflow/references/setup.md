# Repository setup

Use only for a user-requested setup. A plugin install alone does not authorize repository changes. Do not install this into an intentionally empty repository without a new request.

1. Inspect existing instructions, CI, Git hooks, and branch rules. Preserve them.
2. Copy `assets/workflow-guard.example.json` to the target root as `.workflow-guard.json`, set the real project key and default branch, and review the configuration. Copy `scripts/guard.py` to `tools/workflow_guard.py` so checks do not depend on a particular machine's plugin cache.
3. For local hooks, run `python tools/workflow_guard.py install-hooks` at the target root. This writes only missing `pre-commit`, `commit-msg`, and `pre-push` files under Git's hooks directory. It refuses an existing core.hooksPath or existing hooks. Integrate existing hook managers manually; never delete their hooks. The generated hooks use this checkout's Python and script absolute paths; rerun setup in each new clone. Remove only these generated hook files to uninstall them. Git for Windows includes the shell required by the hooks.
4. Add/merge the provided PR template. Copy `assets/workflow-guard.yml` into `.github/workflows/` only if that filename is unused. It loads the checker and configuration from the PR base and treats PR metadata as JSON data, never interpolated shell code. The base branch must contain `tools/workflow_guard.py` and `.workflow-guard.json` before enabling this workflow (bootstrap in a reviewed PR first).
5. Add the project's real build/tests to its existing CI. ShopIL needs component tests plus integration experiments, not merely the plugin's convention checks. Keep secrets out of fork PRs; never use pull_request_target to execute PR code. Retain least-privilege job permissions.
6. Within authorization, configure GitHub branch protection/rulesets: require PRs, required `Workflow conventions` and real test jobs, current-head checks, resolved conversations, and the team's review count. Prefer squash merging with a compliant PR title. Prevent force-push/deletion. Do not claim enforcement before reading back the saved rules. Administrators with bypass permissions remain a limitation.

Branch examples: `feature/SHOPIL-13-reviews-loader`, `fix/SHOPIL-23-replay`, `ci/SHOPIL-47-workflow-checks`.

The main branch name and project keys are configurable; commit types and branch prefixes are documented project defaults. `guard.py` does not call networks, run application tests, manage Jira transitions, or prove that a Jira snapshot is fresh. The agent must use the connected Atlassian tools for current ticket state and GitHub for actual CI/review/merge results.

Review acceptance criteria for material requirements that regex checks cannot enforce: data semantics, appropriate tests, working CI, documentation, source attribution, no unrequested scope, and no false Done status.
