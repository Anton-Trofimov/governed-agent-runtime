"""Two isolated Ollama requests. Default is offline verification; never auto-retry."""
import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from jsonschema import Draft202012Validator

KIT = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def check_kit():
    for line in (KIT / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split("  ", 1)
        if sha((KIT / name).read_bytes()) != digest:
            raise ValueError(f"Kit hash mismatch: {name}")
    config = json.loads((KIT / "config.json").read_text())
    prompt = (KIT / "judge-system.txt").read_text()
    if sha(prompt.encode()) != config["system_sha256"]:
        raise ValueError("System prompt hash mismatch")
    original = json.loads((KIT / "original-input.exact.json").read_text())
    if "final_review_instruction" not in original:
        raise ValueError("Missing D1 instruction")
    schema = json.loads((KIT / "judge-output.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    requests = []
    for case in config["cases"]:
        body = json.loads((KIT / f"request-{case}.json").read_text())
        assert [m["role"] for m in body["messages"]] == ["system", "user"]
        assert body["messages"][0]["content"] == prompt
        payload = json.loads(body["messages"][1]["content"])
        assert payload["original_task_input"] == original
        assert payload["candidate_response"] == (KIT / f"candidate-{case}.exact.json").read_text()
        assert set(payload) == {"original_task_input", "candidate_response"}
        assert body["format"] == schema and "tools" not in body
        assert body["model"] == config["expected_model"]
        requests.append(body)
    assert {k: v for k, v in requests[0].items() if k != "messages"} == {
        k: v for k, v in requests[1].items() if k != "messages"
    }
    return config, schema


def get_json(endpoint, route):
    with urlopen(endpoint + route, timeout=15) as response:
        return json.load(response)


def preflight(config):
    version = get_json(config["endpoint"], "/api/version")
    tags = get_json(config["endpoint"], "/api/tags")
    matches = [m for m in tags["models"] if m.get("name") == config["expected_model"]]
    if version.get("version") != config["expected_ollama_version"]:
        raise ValueError(f"Ollama version mismatch: {version}")
    if len(matches) != 1 or matches[0].get("digest") != config["expected_digest"]:
        raise ValueError("Model digest mismatch; no inference sent")
    return {"version": version, "model": matches[0]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--approved-system-sha256")
    parser.add_argument("--evidence-root", type=Path,
                        default=Path.home() / "projects/evidence/governed-agent-runtime/bc-005-d3")
    args = parser.parse_args()
    config, schema = check_kit()
    print("Offline kit verification: PASS", flush=True)
    print("System SHA256:", config["system_sha256"], flush=True)
    if not args.run:
        print("No network requests or inference. Review judge-system.txt before --run.")
        return
    if args.approved_system_sha256 != config["system_sha256"]:
        parser.error("--run requires the reviewed --approved-system-sha256")
    server = preflight(config)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    output = args.evidence_root / stamp
    # Prevent accidental repeated measurement from this same kit, even after timeout.
    with (KIT / ".measurement-started.json").open("x") as lock:
        json.dump({"run_id": stamp, "evidence_directory": str(output)}, lock)
    output.mkdir(parents=True, exist_ok=False)
    manifest = {"diagnostic_id": config["diagnostic_id"], "status": "STARTED",
                "config": config, "preflight": server, "started_at": stamp,
                "python": sys.version, "approved_system_sha256": args.approved_system_sha256,
                "kit_sha256sums_sha256": sha((KIT / "SHA256SUMS").read_bytes()),
                "attempted_inference_calls": 0, "completed_response_count": 0,
                "preload_calls": 0, "cases": {}}
    write_json(output / "manifest.json", manifest)
    print("Evidence:", output, flush=True)
    try:
        for case in config["cases"]:
            manifest["cases"][case] = {"preflight": preflight(config)}
            data = (KIT / f"request-{case}.json").read_bytes()
            (output / f"request-{case}.json").write_bytes(data)
            manifest["cases"][case]["request_sha256"] = sha(data)
            manifest["attempted_inference_calls"] += 1
            write_json(output / "manifest.json", manifest)
            print(f"Request {case}: started (timeout {config['timeout_seconds']}s)", flush=True)
            request = Request(config["endpoint"] + "/api/chat", data=data,
                              headers={"Content-Type": "application/json"}, method="POST")
            try:
                with urlopen(request, timeout=config["timeout_seconds"]) as response:
                    raw = response.read()
            except HTTPError as exc:
                (output / f"response-{case}.http-error.raw").write_bytes(exc.read())
                raise
            (output / f"response-{case}.raw.json").write_bytes(raw)
            envelope = json.loads(raw)
            manifest["cases"][case]["response_sha256"] = sha(raw)
            if envelope.get("done") is not True or envelope.get("done_reason") != "stop":
                raise ValueError(f"{case}: incomplete/truncated response; raw retained")
            final = envelope["message"]["content"]
            (output / f"judge-{case}.exact.json").write_bytes(final.encode())
            parsed = json.loads(final)
            Draft202012Validator(schema).validate(parsed)
            if (parsed["verdict"] == "PASS" and parsed["issues"]) or (
                parsed["verdict"] == "FAIL" and not parsed["issues"]
            ):
                raise ValueError(f"{case}: verdict/issues contract mismatch")
            manifest["completed_response_count"] += 1
            manifest["cases"][case]["verdict"] = parsed["verdict"]
            print(f"Request {case}: {parsed['verdict']} (not human adjudicated)", flush=True)
            write_json(output / "manifest.json", manifest)
        manifest["status"] = "COMPLETED_PENDING_HUMAN_REVIEW"
    except BaseException as exc:
        manifest["status"] = "STOPPED_NO_AUTO_RETRY"
        manifest["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        manifest["ended_at"] = datetime.now(UTC).isoformat()
        write_json(output / "manifest.json", manifest)
        print("Status:", manifest["status"], "Evidence:", output, flush=True)


if __name__ == "__main__":
    main()
