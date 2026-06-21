"""Thread-safe LLM client with a semaphore queue and timeout."""
import threading
import time
import requests
from config import OLLAMA_BASE_URL, OLLAMA_MODEL

_sem = threading.Semaphore(1)  # 1 at a time — Qwen3 on CPU needs serialized access
_lock = threading.Lock()
_stats = {"total": 0, "errors": 0, "total_ms": 0.0}


def query_llm(prompt: str, model: str = OLLAMA_MODEL, timeout: int = 300,
              system: str = "") -> str:
    """
    Send a prompt to the local Ollama instance and return the response text.
    Blocks if 2 requests are already in flight (deadlock prevention via semaphore).
    """
    acquired = _sem.acquire(timeout=600)   # wait up to 10 min for a slot
    if not acquired:
        raise TimeoutError("LLM semaphore timeout — too many concurrent requests")
    t0 = time.time()
    try:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={"model": model, "messages": messages, "stream": False,
                  "think": False,   # disable Qwen3 chain-of-thought — keeps responses fast
                  "options": {"temperature": 0.3, "num_predict": 512}},
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["message"]["content"].strip()
        # strip any residual <think>…</think> block if thinking leaked through
        import re as _re
        text = _re.sub(r"<think>.*?</think>", "", text, flags=_re.DOTALL).strip()
        elapsed = (time.time() - t0) * 1000
        with _lock:
            _stats["total"] += 1
            _stats["total_ms"] += elapsed
        return text
    except Exception as e:
        with _lock:
            _stats["errors"] += 1
        raise
    finally:
        _sem.release()


def get_stats() -> dict:
    with _lock:
        s = dict(_stats)
    s["avg_ms"] = round(s["total_ms"] / s["total"], 1) if s["total"] else 0
    return s


def is_ollama_running() -> bool:
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


def list_models() -> list[str]:
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        r.raise_for_status()
        return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []
