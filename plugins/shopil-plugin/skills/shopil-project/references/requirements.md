# ShopIL implementation contract

Authority: [Assignment 1](https://moodle.colman.ac.il/mod/assign/view.php?id=45837), original and complete extracted text in the [course index](course-index.md). Snapshot 2026-11-13. Due date observed in Moodle: **2026-11-25 00:00 Asia/Jerusalem**, i.e. the night ending November 24. Recheck Moodle before planning a submission. This is not the annual capstone. Do not submit work through Moodle without the user's instruction.

## Architecture and scope

Complete the course reviews starter and the chat integration using lecturer code and notebooks. Batch completes before the chat. Streaming continues during chat answers. Data flows: source CSV/JSON → dlt → DuckDB raw → dbt staging/marts; producer → bounded asyncio.Queue → StreamEngine → SQLite; Python queries → a frozen evidence package → Actor → Critic → bounded retry → Hebrew Gradio answer. SQL/code performs arithmetic; the LLM explains computed results. The local engine/SQLite path is sufficient for full credit. LanceDB, Dagster, Redpanda/Kafka and crash-before/after-commit experiments are optional.

## A. Batch ETL — 25 points (SHOPIL-11–16)

- Use `ETL_Course_Lab_HE.ipynb`, ShopIL synthetic data and `exercises/starter/` from the ETL ZIP. `scripts/generate_data.py` supplies the inputs; no external dataset is required. Instructor solution sections are excluded from independent work.
- Load customers, orders and products with dlt into DuckDB raw; inspect dbt staging/marts. Orders use merge by `order_id` with `updated_at`; reviews snapshot uses replace. Reload the same source and prove no target duplication.
- Complete reviews resource/checker. Preserve 310 raw review rows, including source duplicates. Verify nested product normalization and tags child table.
- `stg_reviews`: rating 1–5; nonempty trimmed text; keep the earliest valid `created_at` per duplicate `review_id`. Record counts and surviving IDs after each rule: 310 → 304 → 298 → 289.
- `mart_product_reviews`: one row/product; review count, average rating, negative count (rating <=2), paid order count and revenue. Aggregate reviews and paid orders separately before joining products to prevent fan-out. `amount` already includes quantity; never multiply it again. Preserve products with no reviews: count 0, average NULL.
- Original reference values: 600 orders in raw/staging; 549 valid `marts.fct_orders`; 402 paid orders, revenue **₪97,210.10**; 8 unique products. Explain differences for changed experimental inputs separately.
- ETL slides 22–25: reload policies; 28–35: models/metrics; 50–54: reviews exercise. Use isolated lab environments and verify which DuckDB file the chat reads; notebook examples can use a separate `notebook_lab` workspace.

## B. Streaming — 30 points (SHOPIL-17–25)

- Use `Streaming_Lab_HE.ipynb` and `StreamEngine`; continuous producer, bounded asyncio.Queue, SQLite persistence, visible produced/consumed counters.
- Event contract: `event_id`, `kind`, timezone-aware `event_time`, `product_id`; integer `amount_cents` for orders; `rating` and `text` for reviews. Source offset is not the business event ID.
- Invalid input goes to `dead_letters` with raw input, offset, reason. Valid events arriving after window closure go to `late_events`. Follow the course engine's checkpoint progression.
- Run `run_live` and `run_microbatch` over the same source order and fresh databases. Never sort by event time. Both must have identical canonical results. Every event commits its own transaction, even within a collected batch.
- A microbatch releases at max size OR max wait, whichever first. The timer starts when the first record is pulled. Show a partial batch timing out with no further arrival, plus orderly `final_drain`. Record sizes/reasons and reconcile their sum with consumed events. A collection batch is not a business time window.
- Start with 60-second tumbling windows `[start,end)`, out-of-order allowance 0s, Grace 10s. `watermark = max(previous_watermark, max_seen_event_time - out_of_order)`. Only valid, unique, accepted events advance max time. Wall clock and batch timers do not advance it. Close when watermark >= end + grace. Revenue windows publish upon final closure.
- At finite demo EOF, `finalize_demo` closes remaining windows with `demo_end_of_input` without changing watermark; final draining alone is not window finalization.
- Persist event IDs, counters, windows, side outputs and checkpoint in the same SQLite transaction. Duplicate event_id at a new offset cannot add revenue. Replaying persisted offsets, including after reopening the DB, leaves durable state unchanged. Do not claim exactly-once external message delivery.
- Teaching fixture: 17 deliveries, accepted revenue **₪122**, late revenue **₪13**, full unique-valid total **₪135**. Reconcile these within the stream, not against historical paid revenue. Product 5 gets one alert at the third negative review in a window; the fourth increments the count without a second alert.
- Streaming slides 7–10: ingestion; 19–26: time/reliability; 28–29: transactions; 39–41: comparison/alerts; 25, 36, 41: reference experiments.

## C. Evidence and chat — 25 points (SHOPIL-26–36)

- Gradio chat in Hebrew. Python layer runs predefined queries against ETL/stream results. Include question, relevant rows, table names, product/review IDs, units and time ranges. Stream evidence also includes checkpoint, watermark and window status. Clean review text may be fetched by product.
- Create one consistent evidence snapshot per user question. Actor, Critic and all correction attempts receive the exact same snapshot even while the stream advances. A new question reads fresh state. Include snapshot ID/time or checkpoint with answers and logs.
- Historical revenue = paid orders in shekels. Stream order events = integer cents and no payment-status field. Keep metrics separate. Joining by product requires ID mapping validation; combining amounts also requires compatible semantics and proof of no overlap.
- Actor explains evidence with source/time and distinguishes missing data, zero, and open windows. Current evidence overrides stale numerical facts in chat history.
- Critic receives question, same evidence and candidate answer; validates numbers, units, sources, time and window state. Pydantic `Evaluation` requires `is_acceptable: bool` and `feedback: str`. Schema validity is not proof of truth: manually check two accepted answers against SQL results.
- At most **3 total attempts**, including the first. On rejection, supply draft, feedback and unchanged evidence. On approval, display/save the answer. After three rejections, state no approved answer was obtained. API errors and malformed evaluation terminate with a logged error. Rejected drafts go to audit logs, not approved conversation history.
- Log snapshot ID, every draft, feedback, decision and terminal state. Demonstrate at least one real Actor/Critic rejection→correction→reevaluation. A deliberately faulty draft is allowed. A mock evaluator may test three rejections if labeled clearly.
- Agents lecture 2 slides 19–21 explain this evaluation loop. No fine-tuning, RL training, specific model provider, or two different model vendors is mandated by the assignment.

## D. Required experiments — 15 points (SHOPIL-37–43)

For each: input, configuration, expected result, actual result, evidence and explanation. Comparisons use identical inputs/order and fresh DBs.

1. Loading/cleaning: counts, IDs, product metrics, idempotent rerun.
2. Live vs microbatch: canonical results, produced/consumed, sizes, release reasons; orderly completion processes everything ingested.
3. Batch size/time/end: max_size, max_wait without a new event, final_drain; sizes sum to consumed.
4. Time: manually calculate a window and boundary; inspect late_events; reconcile with full batch truth of the same unique-valid events.
5. Policy: choose two Grace values from **0, 10, 120**, hold other parameters fixed; explain lateness and closure timing.
6. Reliability: duplicate ID at a new offset, replayed offset, reopen DB.
7. Chat: existing fact, follow-up, missing fact; rejected draft, actual feedback, correction and reevaluation.
8. Concurrent update: accept a new valid unique event during answer generation; current question keeps snapshot, next question sees changed state; test three-rejection termination too.

## E. Submission — 5 points (SHOPIL-44–46)

- ZIP or repository: completed assignment code, inputs, retrieval/chat, Actor/Critic instructions, experiments. Separate reused course code from original work.
- README: Python/dependencies, Batch prep, both streaming modes, chat, tests; env-variable example without real credentials. Windows/Cursor/uv are allowed, not mandatory editor choices.
- Evidence: dbt and exercise-checker output, load/clean counts, windows/side outputs, ingestion/batching metrics, reconciliation, Actor/Critic logs, screenshots of active ingestion and a sourced/timestamped answer.
- Report: at most **3 pages excluding diagram and results**. Explain merge/replace, batch vs window, watermark/Grace, dedup, Critic correction, and manual checks.
- Diagram: actual sources/destinations, evidence/feedback, checkpoint location, transaction boundary, snapshot creation point.

## Project conventions and boundaries

Workflow additions in this plugin (Conventional Commits, branch prefixes, PR template, ownership gate) are team conventions, not lecturer grading requirements. The syllabus's group guidance and annual-project context must be verified from their own sources; do not infer a number of assignments from the number of lab sections. Jira task descriptions may contain older planning assumptions: resolve conflicts in favor of current user instructions and the actual assignment.

CI for this plugin proves its checks and bundled-file integrity. It does not prove the ShopIL application works. Run application tests in the implementation repository once code exists; retain a real-model integration demonstration for the graded chat behavior.
