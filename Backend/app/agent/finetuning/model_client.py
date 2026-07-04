from __future__ import annotations

import httpx

from core.config import settings


class FinetunedModelError(Exception):
    """Raised when the fine-tuned model endpoint is unreachable or errors out."""


def is_configured() -> bool:
    """True when a base URL and model name are configured for the finetuned lane."""
    return bool(settings.finetuned_base_url and settings.finetuned_model_name)


#Call the fine-tuned model and return the assistant message text.
async def chat_completion(
    messages: list[dict],
    temperature: float = 0.2,
    max_tokens: int = 2048,
) -> str:
    url = f"{settings.finetuned_base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": settings.finetuned_model_name,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    headers = {"Content-Type": "application/json"}
    if settings.finetuned_api_key:
        headers["Authorization"] = f"Bearer {settings.finetuned_api_key}"

    print("\n================ FINETUNED PROMPT SENT TO MODEL ================")
    print(f"model={settings.finetuned_model_name} | temperature={temperature} | max_tokens={max_tokens}")
    for _m in messages:
        print(f"--- {_m.get('role')} ---")
        print(_m.get("content"))
    print("================================================================\n")

    try:
        async with httpx.AsyncClient(timeout=settings.finetuned_timeout_sec) as client:
            resp = await client.post(url, json=payload, headers=headers)
    except httpx.HTTPError as exc:
        raise FinetunedModelError(f"could not reach finetuned model at {url}: {exc}") from exc

    if resp.status_code >= 400:
        raise FinetunedModelError(
            f"finetuned model returned HTTP {resp.status_code}: {resp.text.strip()[:300]}"
        )

    try:
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise FinetunedModelError(f"unexpected response from finetuned model: {exc}") from exc

    return content or ""
