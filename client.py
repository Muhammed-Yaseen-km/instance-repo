import json
import re
import requests
import base64
from typing import Generator, Any
from config import get_model, get_system, settings

# === Helpers ===

def _encode_image(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def _ollama(endpoint: str, payload: dict, stream: bool = False) -> requests.Response:
    return requests.post(
        f"{settings.OLLAMA_HOST}/api/{endpoint}",
        json={**payload, "stream": stream},
        stream=stream,
        timeout=settings.TIMEOUT
    )

def _openrouter(messages: list[dict]) -> str:
    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {settings.OPENROUTER_KEY}"},
        json={"model": settings.OPENROUTER_MODEL, "messages": messages},
        timeout=settings.TIMEOUT
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def _stream_response(r: requests.Response, key: str) -> Generator[str, None, None]:
    r.raise_for_status()
    for line in r.iter_lines():
        if line:
            data = json.loads(line)
            yield data.get(key, "") if isinstance(data.get(key), str) else data.get(key, {}).get("content", "")

# === Core API ===

def infer(
    prompt: str,
    task: str = "chat",
    model: str = None,
    images: list[str] = None,
    stream: bool = False,
    temperature: float = 0.7,
    system: str = None,
) -> str | Generator[str, None, None]:
    model = model or get_model(task) or settings.MODELS["general"]
    payload = {
        "model": model,
        "prompt": prompt,
        "options": {"temperature": temperature},
        "system": system or get_system(task),
    }
    if images:
        payload["images"] = [_encode_image(p) if not p.startswith("data:") else p.split(",")[1] for p in images]

    try:
        r = _ollama("generate", payload, stream)
        if stream:
            return _stream_response(r, "response")
        r.raise_for_status()
        return r.json().get("response", "")
    except Exception as e:
        if settings.OPENROUTER_KEY:
            return _openrouter([{"role": "system", "content": payload.get("system", "")}, {"role": "user", "content": prompt}])
        raise e

def chat(messages: list[dict], model: str = None, stream: bool = False, system: str = None) -> str | Generator[str, None, None]:
    model = model or get_model("chat") or settings.MODELS["general"]
    msgs = [{"role": "system", "content": system}] + messages if system else messages

    try:
        r = _ollama("chat", {"model": model, "messages": msgs}, stream)
        if stream:
            return _stream_response(r, "message")
        r.raise_for_status()
        return r.json().get("message", {}).get("content", "")
    except Exception as e:
        if settings.OPENROUTER_KEY:
            return _openrouter(msgs)
        raise e

def health() -> dict:
    result = {"ollama": "offline", "models": [], "ready": False}
    try:
        r = requests.get(f"{settings.OLLAMA_HOST}/api/tags", timeout=5)
        loaded = [m["name"] for m in r.json().get("models", [])]
        result.update(ollama="online", models=loaded, models_required=list(settings.MODELS.values()))
        result["models_missing"] = [m for m in result["models_required"] if m not in loaded]
        result["ready"] = len(result["models_missing"]) == 0
    except requests.RequestException:
        pass  # Ollama offline, keep defaults
    result["openrouter"] = "configured" if settings.OPENROUTER_KEY else "not_configured"
    return result

# === Structured Output ===

def _extract_json(text: str) -> str:
    for p in [r"```json\s*([\s\S]*?)\s*```", r"```\s*([\s\S]*?)\s*```", r"(\{[\s\S]*\})", r"(\[[\s\S]*\])"]:
        if m := re.search(p, text):
            return m.group(1).strip()
    return text.strip()

def _validate(data: Any, schema: dict) -> list[str]:
    errors = []
    if schema.get("type") == "object" and "properties" in schema:
        for key, prop in schema["properties"].items():
            if key not in data:
                if key in schema.get("required", []):
                    errors.append(f"Missing: {key}")
            elif prop.get("type") == "string" and not isinstance(data[key], str):
                errors.append(f"{key} must be string")
            elif prop.get("type") == "number" and not isinstance(data[key], (int, float)):
                errors.append(f"{key} must be number")
            elif prop.get("type") == "array" and not isinstance(data[key], list):
                errors.append(f"{key} must be array")
    return errors

def structured(prompt: str, schema: dict, model: str = None, retries: int = 2) -> dict:
    system = "Return ONLY valid JSON matching the schema. No markdown."
    full_prompt = f"Extract from:\n{prompt}\n\nSchema: {json.dumps(schema)}"

    for attempt in range(retries + 1):
        response = infer(prompt=full_prompt, task="extract", model=model, system=system, temperature=0.1)
        try:
            data = json.loads(_extract_json(response))
            errors = _validate(data, schema)
            if not errors:
                return {"success": True, "data": data}
            if attempt == retries:
                return {"success": False, "data": data, "errors": errors}
        except json.JSONDecodeError as e:
            if attempt == retries:
                return {"success": False, "raw": response, "error": str(e)}
    return {"success": False, "error": "Max retries exceeded"}

# === Model Warmup ===

def warmup(models: list[str] = None) -> dict:
    models = models or list(settings.MODELS.values())
    results = {}

    for model in models:
        try:
            r = requests.post(
                f"{settings.OLLAMA_HOST}/api/generate",
                json={"model": model, "prompt": "Hi", "stream": False},
                timeout=600  # 10 min for cold start
            )
            r.raise_for_status()
            results[model] = "ready"
        except Exception as e:
            results[model] = f"failed: {str(e)[:50]}"

    return {"models": results, "all_ready": all(v == "ready" for v in results.values())}

def pull(model: str) -> dict:
    try:
        r = requests.post(
            f"{settings.OLLAMA_HOST}/api/pull",
            json={"name": model},
            timeout=1800  # 30 min for download
        )
        r.raise_for_status()
        return {"model": model, "status": "pulled"}
    except Exception as e:
        return {"model": model, "status": "failed", "error": str(e)}
