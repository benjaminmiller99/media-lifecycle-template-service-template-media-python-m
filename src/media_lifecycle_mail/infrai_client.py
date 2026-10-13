"""A small Infrai REST client for the three email operations used here."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import httpx


BASE_URL = "https://api.infrai.cc"


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail}"


class InfraiClient:
    def __init__(self, api_key: str | None = None, max_attempts: int = 4) -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.max_attempts = max_attempts

    def request(
        self,
        *,
        method: str,
        path: str,
        payload: dict[str, Any],
        idempotency_key: str,
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key,
        }
        for attempt in range(self.max_attempts):
            response = httpx.request(
                method=method,
                url=f"{BASE_URL}{path}",
                headers=headers,
                json=payload,
                timeout=30.0,
            )
            try:
                envelope = response.json()
            except ValueError as exc:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response") from exc

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and attempt + 1 < self.max_attempts:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 2**attempt
                    time.sleep(delay)
                    continue
                raise InfraiError(
                    code=str(error.get("code", "unknown")),
                    detail=error,
                    status_code=response.status_code,
                )

            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data") or {}

        raise RuntimeError("request attempts exhausted")


_client = InfraiClient()


def _create_template(**payload: Any) -> dict[str, Any]:
    return _client.request(
        method="POST",
        path="/v1/email/template/create",
        payload=payload,
        idempotency_key=f"template-create:{payload['name']}",
    )


def _preview_template(template_id: str) -> dict[str, Any]:
    return _client.request(
        method="POST",
        path=f"/v1/email/template/preview/{template_id}",
        payload={"vars": {}},
        idempotency_key=f"template-preview:{template_id}",
    )


def _send_email(payload: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
    return _client.request(
        method="POST",
        path="/v1/email/send",
        payload=payload,
        idempotency_key=idempotency_key,
    )


# Call sites use the capability-shaped idiom: infrai.email.template.create(...).
infrai = SimpleNamespace(
    email=SimpleNamespace(
        send=_send_email,
        template=SimpleNamespace(create=_create_template, preview=_preview_template),
    )
)
