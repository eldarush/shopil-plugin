# ShopIL shared working context

This is AI Engineering assignment 1 with Dr. Paul Avrahami, separate from the annual capstone. The bundled course snapshot is from 2026-11-13; the observed deadline is 2026-11-25 00:00 Asia/Jerusalem (the night ending November 24). Check live Moodle for changes. Do not submit work without the user's instruction.

## Definition of the product

Build a Hebrew Gradio business assistant using historical ShopIL data plus continuously arriving orders/reviews. Batch finishes before chat; streaming continues during answers. The lecturer's dlt/DuckDB/dbt ETL and StreamEngine/SQLite labs are the starting point. Python/SQL computes metrics and creates evidence; Actor explains, Critic validates. Each question and all retries share one frozen snapshot. New questions see new stream state.

## Required contract

- ETL (25 points): orders merge by order_id/updated_at; reviews snapshot replace; idempotent reruns. Review cleaning counts 310 → 304 → 298 → 289 (rating, trimmed text, earliest valid duplicate). Aggregate paid orders and reviews separately before product join. 8 unique products, count 0/average NULL for products without reviews. Original values: 600 raw/staged orders, 549 valid, 402 paid, ₪97,210.10. Amount already includes quantity.
- Streaming (30): continuous producer, bounded asyncio.Queue, live and microbatch modes in identical source order with fresh comparison databases; each event gets its own SQLite transaction. Batch size OR timeout from first record; timeout works without new arrivals; final_drain is not business-window closure. Windows [start,end) of 60s, out-of-order 0, Grace 10. Watermark advances on accepted valid unique event times, never wall clock, and never decreases. Close at watermark >= end + Grace. Invalid input → dead_letters; too-late valid events → late_events. Atomically persist IDs, state, windows, side outputs and checkpoint. Replay/reopen must not duplicate. Teaching reference: ₪122 accepted + ₪13 late = ₪135 total. Product 5 alerts once at third negative review; fourth only increments count.
- Chat (25): defined queries produce sourced, timestamped, unit-aware evidence including checkpoint/watermark/window state. Batch is paid revenue in shekels; stream is order events in cents without payment status. Do not sum these without semantic/nonoverlap proof. Actor and Critic receive the same snapshot; Evaluation has is_acceptable bool and feedback str. At most 3 attempts total; real rejection/correction demonstration required. API/malformed-output errors terminate explicitly. Keep rejected drafts separate from approved history; manually verify two approved answers. Missing data is not zero.
- Experiments (15): ETL counts/IDs/rerun, live-vs-batch equality, max-size/max-wait/drain, hand-calculated window/boundary/reconciliation, two Grace values from 0/10/120, dedup/replay/reopen, chat/follow-up/missing-data and real correction, incoming event during a frozen question plus next-question update, three-rejection termination. Preserve inputs, commands, expected/actual results and limitations.
- Submission (5): code/inputs/prompts with attribution, reproducible README/environment example without keys, test/log/screenshot evidence, report <=3 pages excluding diagram/results, actual architecture showing checkpoint/transaction/snapshot boundaries.

LanceDB, Dagster, Kafka/Redpanda and crash experiments are optional. Instructor guides/solutions in the complete lab ZIPs are reference-only; implement reviews from starters. Do not confuse optional lab requirements, annual-project proposals, group planning assumptions, or instructor test reports with graded ShopIL requirements or your own validation.

## Coordination

Read the real assigned Jira ticket and applicable AGENTS.md/CLAUDE.md before coding. Resolve the signed-in user's Jira accountId and exact assignee accountId, never display names or the repository owner's identity. No task creation without a prompt and no auto-claiming unassigned tasks. Keep ticket scope, branch key, commits and PR aligned. Refresh ownership before every Jira write; another user's ticket remains read-only. Separate team workflow conventions from lecturer requirements.

Use Ponytail: smallest complete change, reuse the course code, no unnecessary frameworks, and meaningful checks for nontrivial behavior. Default branch flow: feature/SHOPIL-N-short-description → Conventional Commits containing SHOPIL-N → PR into main → current-head tests/review → authorized merge → verified acceptance evidence → Done. Do not bypass hooks or claim a convention check proves the application works.

Full details, diagrams, slides/notes, source hashes, Windows lab setup, synthetic datasets and notebooks are linked from requirements.md and course-index.md next to this file. Read the relevant originals for the ticket; all are installed with the plugin. Preserve third-party attribution.
