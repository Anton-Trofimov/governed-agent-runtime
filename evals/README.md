# Evaluations

This directory contains evaluation assets and review-support data.

- `hidden/` contains hidden evaluator truth and must never enter the model context or runtime execution decision path.
- `traceability/` contains explicit expectation-to-model-visible-basis mappings used by the development/evaluation harness. These mappings are review metadata, not model-visible operational context.

Historical diagnostic traceability bundles may reference frozen evaluation/model-context artifacts read-only; they do not rewrite historical evidence or dispositions.
