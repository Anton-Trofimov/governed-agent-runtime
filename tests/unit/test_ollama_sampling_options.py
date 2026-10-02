from governed_agent_runtime.ollama_model_adapter import OllamaChatModel


def test_ollama_chat_model_omits_unspecified_optional_sampling_options() -> None:
    model = OllamaChatModel(
        base_url="http://127.0.0.1:11434",
        model_identity="qwen3.8:27b",
        model_schema={},
        temperature=0.6,
        seed=18,
        num_ctx=8192,
        num_predict=2048,
        think=True,
        keep_alive="10m",
        request_timeout_seconds=300,
    )

    assert model._request_options() == {
        "temperature": 0.6,
        "seed": 18,
        "num_ctx": 8192,
        "num_predict": 2048,
    }


def test_ollama_chat_model_includes_explicit_sampling_options() -> None:
    model = OllamaChatModel(
        base_url="http://127.0.0.1:11434",
        model_identity="qwen3.8:27b",
        model_schema={},
        temperature=1.0,
        top_p=0.95,
        top_k=20,
        min_p=0.0,
        presence_penalty=0.0,
        repeat_penalty=1.0,
        seed=18,
        num_ctx=32768,
        num_predict=8192,
        think=True,
        keep_alive="10m",
        request_timeout_seconds=300,
    )

    assert model._request_options() == {
        "temperature": 1.0,
        "seed": 18,
        "num_ctx": 32768,
        "num_predict": 8192,
        "top_p": 0.95,
        "top_k": 20,
        "min_p": 0.0,
        "presence_penalty": 0.0,
        "repeat_penalty": 1.0,
    }
