import importlib
import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
PROPOSAL_SCHEMA = json.loads(
    (ROOT / "schemas/model-proposal.schema.json").read_text(encoding="utf-8")
)

RAW_MODEL_RESPONSE = json.dumps(
    {
        "schema_version": "0.1.0",
        "proposal_id": "proposal-ollama-contract-001",
        "proposal_type": "PROVIDE_BOUNDED_HYPOTHESIS",
        "rationale": "The supplied evidence supports a bounded hypothesis.",
        "payload": {
            "hypotheses": [
                {
                    "hypothesis_id": "hypothesis-runtime-001",
                    "statement": "The new version is associated with elevated errors.",
                    "source": "DETERMINISTIC_RULE",
                    "cause_status": "SUPPORTED",
                    "evidence_ids": ["evidence-runtime-001"],
                    "missing_evidence": [],
                }
            ]
        },
    },
    sort_keys=True,
    separators=(",", ":"),
)

PROVIDER_METADATA = {
    "model": "qwen3.8:27b",
    "created_at": "2026-08-18T12:00:00Z",
    "done": True,
    "done_reason": "stop",
    "total_duration": 12_000_000_000,
    "load_duration": 2_000_000_000,
    "prompt_eval_count": 2048,
    "prompt_eval_duration": 4_000_000_000,
    "eval_count": 128,
    "eval_duration": 6_000_000_000,
}
MODEL_ARTIFACT_DIGEST = "sha256:provider-model-artifact"


def ollama_adapter_module() -> ModuleType:
    module_name = "governed_agent_runtime.ollama_model_adapter"
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as error:
        if error.name != module_name:
            raise
        pytest.fail(
            f"missing local Ollama model boundary: {module_name}",
            pytrace=False,
        )


@contextmanager
def fake_ollama_server() -> Iterator[tuple[str, list[dict]]]:
    requests: list[dict] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            requests.append({"path": self.path, "method": "GET"})
            if self.path == "/api/version":
                response = {"version": "0.12.3-test"}
            else:
                response = {
                    "models": [
                        {
                            "name": "qwen3.8:27b",
                            "model": "qwen3.8:27b",
                            "digest": MODEL_ARTIFACT_DIGEST,
                        }
                    ]
                }
            encoded = json.dumps(response).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def do_POST(self) -> None:
            content_length = int(self.headers["Content-Length"])
            body = self.rfile.read(content_length)
            requests.append(
                {
                    "path": self.path,
                    "method": "POST",
                    "payload": json.loads(body),
                }
            )
            response = {
                **PROVIDER_METADATA,
                "response": RAW_MODEL_RESPONSE,
                "context": list(range(100)),
            }
            encoded = json.dumps(response).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}", requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_ollama_generate_adapter_preserves_request_and_response_boundary() -> None:
    adapter_module = ollama_adapter_module()
    serialized_smoke_input = json.dumps(
        {
            "instructions": "Return one Model Proposal JSON object.",
            "context_package": {
                "context_package_id": "context-package-smoke-001"
            },
        },
        sort_keys=True,
        separators=(",", ":"),
    )

    with fake_ollama_server() as (base_url, requests):
        model = adapter_module.OllamaGenerateModel(
            base_url=base_url,
            model_identity="qwen3.8:27b",
            model_schema=PROPOSAL_SCHEMA,
            temperature=0,
            seed=18,
            num_ctx=8192,
            num_predict=512,
            keep_alive="10m",
            request_timeout_seconds=5,
        )

        returned_response = model(serialized_smoke_input)

    assert len(requests) == 1
    request = requests[0]
    assert request["path"] == "/api/generate"
    assert request["method"] == "POST"
    assert request["payload"] == {
        "model": "qwen3.8:27b",
        "prompt": serialized_smoke_input,
        "stream": False,
        "think": False,
        "format": PROPOSAL_SCHEMA,
        "keep_alive": "10m",
        "options": {
            "temperature": 0,
            "seed": 18,
            "num_ctx": 8192,
            "num_predict": 512,
        },
    }
    assert model.last_request_payload == request["payload"]
    assert model.last_request_payload["prompt"] == serialized_smoke_input

    assert model.model_identity == "qwen3.8:27b"
    assert model.invocation_parameters == {
        "temperature": 0,
        "seed": 18,
        "num_ctx": 8192,
        "num_predict": 512,
        "think": False,
        "stream": False,
        "keep_alive": "10m",
    }

    assert returned_response == RAW_MODEL_RESPONSE
    assert model.last_response_metadata == PROVIDER_METADATA
    assert "context" not in model.last_response_metadata


def test_ollama_generate_adapter_propagates_explicit_thinking_mode() -> None:
    adapter_module = ollama_adapter_module()

    with fake_ollama_server() as (base_url, requests):
        model = adapter_module.OllamaGenerateModel(
            base_url=base_url,
            model_identity="qwen3.8:27b",
            model_artifact_identity="sha256:current-model-artifact",
            model_schema=PROPOSAL_SCHEMA,
            temperature=0,
            seed=18,
            num_ctx=8192,
            num_predict=2048,
            think=True,
            keep_alive="10m",
            request_timeout_seconds=300,
        )
        model("canonical-input")

    assert requests[0]["payload"]["think"] is True
    assert model.invocation_parameters["think"] is True
    assert model.model_artifact_identity == "sha256:current-model-artifact"


def test_ollama_adapter_resolves_artifact_identity_from_provider_inventory() -> None:
    adapter_module = ollama_adapter_module()

    with fake_ollama_server() as (base_url, requests):
        model = adapter_module.OllamaGenerateModel(
            base_url=base_url,
            model_identity="qwen3.8:27b",
            model_artifact_identity="untrusted-caller-value",
            model_schema=PROPOSAL_SCHEMA,
            temperature=0,
            seed=18,
            num_ctx=8192,
            num_predict=2048,
            think=True,
            keep_alive="10m",
            request_timeout_seconds=300,
        )
        resolved = model.resolve_model_artifact_identity()

    assert requests == [{"path": "/api/tags", "method": "GET"}]
    assert resolved == MODEL_ARTIFACT_DIGEST
    assert model.model_artifact_identity == MODEL_ARTIFACT_DIGEST


def test_ollama_adapter_resolves_authoritative_provider_version() -> None:
    adapter_module = ollama_adapter_module()

    with fake_ollama_server() as (base_url, requests):
        model = adapter_module.OllamaGenerateModel(
            base_url=base_url,
            model_identity="qwen3.8:27b",
            model_schema=PROPOSAL_SCHEMA,
            temperature=0,
            seed=18,
            num_ctx=8192,
            num_predict=2048,
            think=True,
            keep_alive="10m",
            request_timeout_seconds=300,
        )
        provider_version = model.resolve_provider_version()

    assert requests == [{"path": "/api/version", "method": "GET"}]
    assert provider_version == "0.12.3-test"
