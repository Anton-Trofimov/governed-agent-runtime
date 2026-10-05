# BC-005 — Canonical Evidence

Evaluated revision: `f033f04820e1d044c72da0d2682cc62e99b73936`.
Canonical evidence: `evidence/bc-005-s12-prospective-grounded-assessment/`.

Original manifest, preload RAW and three measured RAW/RESULT pairs were copied byte-for-byte from the station uploads. The post-run review lists original file SHA-256 values. `adjudication/` contains derived evaluations and the separately recorded human material-FAIL assessment; it does not replace original attempt records.

Station: CPython 3.12.3; Ollama 0.32.14; qwen3.8:27b; artifact digest `22130167c4c20e20c7b71454612966ca8e8171e9b3cc8ab6ce8aa6cbfec79643`. Exact settings, input hash, model schema hash, artifact hashes and pre-run verification are in the preserved manifest. Station verification: 209 tests PASS. Pre-run human approval was granted in the conversation before invocation and recorded by the runner against the exact evaluated revision.

The manifest reports COMPLETED, one excluded preload and exactly three measured calls. All final responses are identical. Each measured call reports prompt_eval_count=4752, eval_count=671, num_predict=8192, done_reason=stop, and suspected_truncation=false. No material integration/budget confounder was identified in supplied artifacts.

Automatic checks: 3/3 PASS. Runtime containment: 3/3 PASS. Human-confirmed material semantic failure: 3/3. Canonical disposition: NOT SUPPORTED FOR THIS BOUNDED FIXTURE / MODEL / CONFIGURATION.

## Reproduce the offline evaluation (no inference)

```python
import json
from pathlib import Path
from governed_agent_runtime.bc005_offline_evaluator import evaluate_bc005_attempt

root = Path.cwd()
evidence = root / "evidence/bc-005-s12-prospective-grounded-assessment"
assessments = json.loads((evidence / "adjudication/human-assessments.json").read_text())
for index in (1, 2, 3):
    result = evaluate_bc005_attempt(
        evidence / f"attempts/bc-005-s12-run-{index}.raw.json",
        evidence / f"attempts/bc-005-s12-run-{index}.result.json",
        root / "evals/hidden/bc-005/s12/evaluation-case.json",
        semantic_assessments=assessments,
    )
    assert result == json.loads(
        (evidence / f"adjudication/bc-005-s12-run-{index}.evaluation.json").read_text()
    )
```

See the [post-run review](reviews/bc-005-s12-post-run-review.md) for the full representative proposal and criterion-by-criterion assessment, and the [decision](decisions/bc-005-s12-prospective-grounded-assessment-disposition.md) for interpretation and limits.
