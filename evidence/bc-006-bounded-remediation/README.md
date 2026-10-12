# BC-006 accepted measured evidence

One nominal synthetic trajectory, human-accepted on 2026-10-12 (Europe/Moscow).

- [Original manifest](run-001/manifest.json): evaluated revision, approval, model configuration and outcome.
- `run-001/step-*.input.json`: exact model-visible contexts and messages.
- `run-001/step-*.provider.json`: exact requests, raw provider responses (including thinking) and metadata.
- `run-001/step-*.outcome.json` and [trace](run-001/trace.jsonl): decisions, confirmations, results and terminal verification.
- [Integrity manifest](integrity.json): original uploaded archive SHA-256 and hashes of all 17 extracted files.
- [Accepted review](../../reports/reviews/bc-006-run-001-measured-review.md).
- [Closure decision](../../reports/decisions/bc-006-bounded-remediation-disposition.md).

All 17 files under `run-001/` are byte-for-byte copies of the uploaded evidence.
Do not edit them to update disposition or wording; those belong in linked reports.
The archive is retained in the originating evidence transfer; extracted files and
its digest are preserved here without duplicating a binary archive in Git.

Result: 5 model calls, 9 counted tools (including 3 preparations and final read),
3 individually confirmed writes, 0 rejections, runtime-verified COMPLETED.
Recovery after rejection: NOT OBSERVED. No natural operator UX, independent
strategy selection, general reliability, production or comparative-model claim.
