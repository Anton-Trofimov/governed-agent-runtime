"""Provider boundaries for local Ollama Generate and Chat invocations."""

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
_OPTIONAL_SAMPLING_FIELDS = (
    "top_p",
    "top_k",
    "min_p",
    "presence_penalty",
    "repeat_penalty",
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
        top_p: float | None = None,
        top_k: int | None = None,
        min_p: float | None = None,
        presence_penalty: float | None = None,
        repeat_penalty: float | None = None,
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
        optional_sampling = {
            "top_p": top_p,
            "top_k": top_k,
            "min_p": min_p,
            "presence_penalty": presence_penalty,
            "repeat_penalty": repeat_penalty,
        }
        self.invocation_parameters.update(
            {
                name: value
                for name, value in optional_sampling.items()
                if value is not None
            }
        )
        self.last_request_payload: dict[str, Any] | None = None
        self.last_response_metadata: dict[str, Any] | None = None
        self.last_response_envelope: dict[str, Any] | None = None
        self.last_raw_response_body: str | None = None
        self.provider_endpoint = "/api/generate"

    def resolve_provider_version(self) -> str:
        """Resolve the authoritative Ollama server version."""
        request = Request(
            f"{self.base_url}/api/version",
            method="GET",
        )
        with urlopen(
            request,
            timeout=self.request_timeout_seconds,
        ) as response:
            response_payload = json.loads(response.read().decode("utf-8"))

        provider_version = response_payload.get("version")
        if not isinstance(provider_version, str) or not provider_version:
            raise ValueError("Ollama provider version is unavailable")
        return provider_version

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
            "options": self._request_options(),
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
            self.last_raw_response_body = response.read().decode("utf-8")
            response_payload = json.loads(self.last_raw_response_body)

        self.last_response_envelope = deepcopy(response_payload)
        self.last_response_metadata = {
            field: response_payload[field]
            for field in _RESPONSE_METADATA_FIELDS
            if field in response_payload
        }
        return response_payload["response"]

    def _request_options(self) -> dict[str, Any]:
        options = {
            "temperature": self.invocation_parameters["temperature"],
            "seed": self.invocation_parameters["seed"],
            "num_ctx": self.invocation_parameters["num_ctx"],
            "num_predict": self.invocation_parameters["num_predict"],
        }
        options.update(
            {
                field: self.invocation_parameters[field]
                for field in _OPTIONAL_SAMPLING_FIELDS
                if field in self.invocation_parameters
            }
        )
        return options


class OllamaChatModel(OllamaGenerateModel):
    """Call one configured Ollama model through ``POST /api/chat``."""

    def __init__(self, *, system_message: str | None = None, **configuration: Any) -> None:
        super().__init__(**configuration)
        self.system_message = system_message
        self.provider_endpoint = "/api/chat"

    def __call__(self, serialized_input: str) -> str:
        """Return submitted chat content while retaining the full envelope."""
        self.last_response_metadata = None
        self.last_response_envelope = None
        self.last_raw_response_body = None
        payload = {
            "model": self.model_identity,
            "messages": [{"role": "user", "content": serialized_input}],
            "stream": self.invocation_parameters["stream"],
            "think": self.invocation_parameters["think"],
            "format": self.model_schema,
            "keep_alive": self.invocation_parameters["keep_alive"],
            "options": self._request_options(),
        }
        if self.system_message is not None:
            payload["messages"].insert(0, {"role": "system", "content": self.system_message})
        self.last_request_payload = payload
        request = Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=self.request_timeout_seconds) as response:
            self.last_raw_response_body = response.read().decode("utf-8")
            response_payload = json.loads(self.last_raw_response_body)

        self.last_response_envelope = deepcopy(response_payload)
        self.last_response_metadata = {
            field: response_payload[field]
            for field in _RESPONSE_METADATA_FIELDS
            if field in response_payload
        }
        message = response_payload["message"]
        if "thinking" in message:
            self.last_response_metadata["thinking"] = message["thinking"]
        return message["content"]
