---
name: shopil-project
description: Implement, review, or explain the ShopIL AI business-assistant assignment using bundled course slides, assignment, lab archives, requirements, and Jira task mapping.
---

# ShopIL project context

Read [requirements.md](references/requirements.md) first. For workflow use [jira-workflow](../jira-workflow/SKILL.md); for coding use the bundled [Ponytail](../ponytail/SKILL.md). Read only the detailed course material relevant to the current task.

The [course index](references/course-index.md) links every bundled original and extracted text, source URLs, SHA-256 hashes, and source roles. Assets are a snapshot from 2026-11-13. Check live Moodle/Jira for newer instructions and deadlines when consequential; never pretend the snapshot is current. Do not store credentials, private account messages, or unrelated courses in this package.

Use the assignment as the authority for required behavior, the lab code as the supported implementation base, and slide references for explanation. Syllabus and annual-project documents are supplemental context and must not be mistaken for ShopIL's grading or deliverables. SHOPIL is assignment 1, not the separate annual capstone.

Lab ZIPs are complete lecturer snapshots. Their instructor guides, `exercises/solution/`, and notebook solution sections are reference-only; the assignment explicitly excludes the instructor solution from independent work. Start reviews work from `exercises/starter/`. Attribute copied starter components and modifications. Unpack archives only into a dedicated working directory; do not execute them merely to read a requirement. Re-running the lab's exercise-start command can overwrite your implementation.

Use [jira-map.md](references/jira-map.md) to navigate tasks, then fetch the actual live ticket before acting. Snapshot status and assignee are deliberately omitted. Do not infer task completion from this mapping or imported instructor results.

Project runtime setup and dependency pinning belong to their Jira tasks. The local workflow checker uses Python 3.11+; the supplied course Windows guides specify their own Python 3.13.12 environments. Do not conflate these environments or claim that bundling the labs means the application was tested.
