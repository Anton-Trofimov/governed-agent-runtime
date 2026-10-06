import hashlib
import importlib
import json
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REVISION = "0123456789abcdef0123456789abcdef01234567"
DIGEST = "sha256:provider-model-artifact"


def valid_proposal(index: int) -> str:
    return json.dumps(
        {
            "schema_version": "0.1.0",
            "proposal_id": f"proposal-live-bc005-{index}",
            "proposal_type": "PROVIDE_BOUNDED_HYPOTHESIS",
            "rationale": "Bounded proposal only.",
            "payload": {
                "hypotheses": [
                    {
                        "hypothesis_id": "hyp-live-bc005",
                        "statement": "Use the bounded scale-before-shift path.",
                        "source": "DETERMINISTIC_RULE",
                        "cause_status": "SUPPORTED",
                        "evidence_ids": [
                            "ev-bc005-rollout-health",
                            "ev-bc005-capacity-policy",
                            "ev-bc005-capacity-findings",
                        ],
                        "missing_evidence": [],
                    }
                ]
            },
        }
    )


class GitStub:
    clean = True

    def is_clean(self, project_root: Path) -> bool:
        return self.clean

    def resolve_head(self, project_root: Path) -> str:
        return REVISION


class FakeChatModel:
    def __init__(self, configuration: dict) -> None:
        self.model_identity = configuration["model_identity"]
        self.model_artifact_identity = None
        self.request_timeout_seconds = configuration["request_timeout_seconds"]
        self.provider_endpoint = "/api/chat"
        self.invocation_parameters = {
            "temperature": configuration["temperature"],
            "top_p": configuration["top_p"],
            "top_k": configuration["top_k"],
            "min_p": configuration["min_p"],
            "presence_penalty": configuration["presence_penalty"],
            "repeat_penalty": configuration["repeat_penalty"],
            "seed": configuration["seed"],
            "num_ctx": configuration["num_ctx"],
            "num_predict": configuration["num_predict"],
            "think": configuration["think"],
            "stream": False,
            "keep_alive": configuration["keep_alive"],
        }
        self.received_inputs: list[str] = []
        self.last_response_metadata = None
        self.last_response_envelope = None
        self.last_raw_response_body = None
        self.last_request_payload = None

    def resolve_provider_version(self) -> str:
        return "0.32.14-test"

    def resolve_model_artifact_identity(self) -> str:
        self.model_artifact_identity = DIGEST
        return DIGEST

    def __call__(self, serialized_input: str) -> str:
        index = len(self.received_inputs)
        self.received_inputs.append(serialized_input)
        content = valid_proposal(index)
        self.last_request_payload = {
            "model": self.model_identity,
            "messages": [{"role": "user", "content": serialized_input}],
        }
        self.last_response_envelope = {
            "model": self.model_identity,
            "message": {"thinking": "diagnostic", "content": content},
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 650,
            "eval_count": 950,
        }
        self.last_raw_response_body = json.dumps(self.last_response_envelope)
        self.last_response_metadata = {
            "model": self.model_identity,
            "thinking": "diagnostic",
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 650,
            "eval_count": 950,
        }
        return content


class Factory:
    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.models: list[FakeChatModel] = []

    def __call__(self, **configuration: object) -> FakeChatModel:
        config = deepcopy(configuration)
        self.calls.append(config)
        model = FakeChatModel(config)
        self.models.append(model)
        return model


def configure(monkeypatch: pytest.MonkeyPatch):
    live = importlib.import_module("governed_agent_runtime.bc005_live_evaluation")
    monkeypatch.setattr(live._probe, "validate_bc005_pre_run_design",
                        lambda root: {"gate_pass": True})
    factory = Factory()
    monkeypatch.setattr(live, "_SubprocessGitBoundary", GitStub)
    monkeypatch.setattr(live, "OllamaChatModel", factory)
    monkeypatch.setattr(
        live,
        "_run_required_verification",
        lambda root: {"status": "PASSED", "commands": ["test-only"]},
    )
    return live, factory


def test_bc005_live_boundary_persists_preload_and_three_measured_attempts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    live, factory = configure(monkeypatch)
    evidence = tmp_path / "bc005-staging"

    result = live.run_bc005_live_evaluation(
        ROOT,
        evidence_directory=evidence,
        human_pre_run_approved=True,
        approved_revision=REVISION,
    )

    assert len(factory.calls) == 1
    assert factory.calls[0]["think"] is True
    assert factory.calls[0]["temperature"] == 1.0
    assert factory.calls[0]["seed"] == 18
    assert factory.calls[0]["num_ctx"] == 32768
    assert factory.calls[0]["num_predict"] == 8192
    assert len(factory.models[0].received_inputs) == 4

    manifest = json.loads((evidence / "manifest.json").read_text())
    assert manifest["bounded_change_id"] == "BC-005"
    assert manifest["human_pre_run_approved"] is True
    assert manifest["approved_revision"] == REVISION
    assert manifest["traceability_gate"]["gate_pass"] is True
    assert manifest["expected_measured_call_count"] == 3
    assert manifest["model_artifact_identity"] == DIGEST
    assert manifest["written_evidence_files"] == manifest["expected_evidence_files"]
    assert len(manifest["prospective_artifact_sha256"]) == 3
    assert len(result["measured_runs"]) == 3
    assert (evidence / "preload/bc-005-s12-preload.raw.json").exists()

    schema_path = ROOT / "schemas/model-proposal.schema.json"
    assert manifest["model_proposal_schema"]["sha256"] == hashlib.sha256(
        schema_path.read_bytes()
    ).hexdigest()


def test_bc005_live_human_gate_blocks_before_provider_construction(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    live, factory = configure(monkeypatch)

    with pytest.raises(ValueError, match="human pre-run"):
        live.run_bc005_live_evaluation(
            ROOT,
            evidence_directory=tmp_path / "bc005-staging",
            human_pre_run_approved=False,
            approved_revision=REVISION,
        )

    assert factory.calls == []


def test_bc005_live_dirty_git_blocks_before_provider_construction(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    live, factory = configure(monkeypatch)
    GitStub.clean = False
    try:
        with pytest.raises(ValueError, match="clean"):
            live.run_bc005_live_evaluation(
                ROOT,
                evidence_directory=tmp_path / "bc005-staging",
                human_pre_run_approved=True,
                approved_revision=REVISION,
            )
    finally:
        GitStub.clean = True
    assert factory.calls == []


def test_bc005_live_approval_revision_mismatch_blocks_before_provider_construction(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    live, factory = configure(monkeypatch)

    with pytest.raises(ValueError, match="not bound to the evaluated revision"):
        live.run_bc005_live_evaluation(
            ROOT,
            evidence_directory=tmp_path / "bc005-staging",
            human_pre_run_approved=True,
            approved_revision="ffffffffffffffffffffffffffffffffffffffff",
        )

    assert factory.calls == []


def test_bc005_real_pending_gate_blocks_even_with_pre_run_flag(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    live = importlib.import_module("governed_agent_runtime.bc005_live_evaluation")
    original_load = live._probe._load_json

    def pending_traceability(path):
        value = original_load(path)
        if path.name == "traceability.json":
            value["mappings"][2]["semantic_review_disposition"] = "PENDING"
        return value

    monkeypatch.setattr(live._probe, "_load_json", pending_traceability)
    factory = Factory()
    monkeypatch.setattr(live, "OllamaChatModel", factory)
    with pytest.raises(ValueError, match="traceability gate"):
        live.run_bc005_live_evaluation(
            ROOT, evidence_directory=tmp_path / "blocked",
            human_pre_run_approved=True, approved_revision=REVISION,
        )
    assert factory.calls == []
    assert not (tmp_path / "blocked").exists()
