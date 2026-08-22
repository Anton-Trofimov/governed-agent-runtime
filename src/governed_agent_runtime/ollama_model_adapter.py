"""Provider boundary for one local Ollama Generate API invocation."""

import json
from copy import deepcopy
from typing import Any
from urllib.request import Request, urlopen

_RESPONSE_METADATA_FIELDS = (
    "model",
    "created_at",
    "done",
    "done_reason",
    "total_duration",
    "load_duration",
    "prompt_eval_count",
    "prompt_eval_duration",
    "eval_count",
    "eval_duration",
    "thinking",
)


class OllamaGenerateModel:
    """Call one configured Ollama model through ``POST /api/generate``."""

    def __init__(
        self,
        *,
        base_url: str,
        model_identity: str,
        model_schema: dict[str, Any],
        temperature: float,
        seed: int,
        num_ctx: int,
        num_predict: int,
        keep_alive: str,
        request_timeout_seconds: float,
        think: bool = False,
        model_artifact_identity: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_identity = model_identity
        self.model_artifact_identity = model_artifact_identity
        self.model_schema = deepcopy(model_schema)
        self.request_timeout_seconds = request_timeout_seconds
        self.invocation_parameters = {
            "temperature": temperature,
            "seed": seed,
            "num_ctx": num_ctx,
            "num_predict": num_predict,
            "think": think,
            "stream": False,
            "keep_alive": keep_alive,
        }
        self.last_request_payload: dict[str, Any] | None = None
        self.last_response_metadata: dict[str, Any] | None = None

    def resolve_model_artifact_identity(self) -> str:
        """Resolve and retain this model tag's digest from Ollama inventory."""
        request = Request(
            f"{self.base_url}/api/tags",
            method="GET",
        )
        with urlopen(
            request,
            timeout=self.request_timeout_seconds,
        ) as response:
            response_payload = json.loads(response.read().decode("utf-8"))

        matches = [
            model
            for model in response_payload.get("models", [])
            if self.model_identity in (model.get("name"), model.get("model"))
        ]
        if len(matches) != 1 or not matches[0].get("digest"):
            raise ValueError(
                "Ollama inventory did not provide one immutable digest for "
                f"model {self.model_identity!r}"
            )
        artifact_identity = matches[0]["digest"]
        if not isinstance(artifact_identity, str):
            raise TypeError("Ollama model digest must be a string")
        self.model_artifact_identity = artifact_identity
        return artifact_identity

    def __call__(self, serialized_input: str) -> str:
        """Send the exact application input once and return Ollama's response."""
        payload = {
            "model": self.model_identity,
            "prompt": serialized_input,
            "stream": self.invocation_parameters["stream"],
            "think": self.invocation_parameters["think"],
            "format": self.model_schema,
            "keep_alive": self.invocation_parameters["keep_alive"],
            "options": {
                "temperature": self.invocation_parameters["temperature"],
                "seed": self.invocation_parameters["seed"],
                "num_ctx": self.invocation_parameters["num_ctx"],
                "num_predict": self.invocation_parameters["num_predict"],
            },
        }
        self.last_request_payload = payload
        request = Request(
            f"{self.base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urlopen(
            request,
            timeout=self.request_timeout_seconds,
        ) as response:
            response_payload = json.loads(response.read().decode("utf-8"))

        self.last_response_metadata = {
            field: response_payload[field]
            for field in _RESPONSE_METADATA_FIELDS
            if field in response_payload
        }
        return response_payload["response"]
