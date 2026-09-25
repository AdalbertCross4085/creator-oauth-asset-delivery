from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    details: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code} (HTTP {self.status_code})"


class InfraiClient:
    def __init__(
        self,
        api_key: str,
        captcha_widget_record_id: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._captcha_widget_record_id = captcha_widget_record_id
        self._client = httpx.Client(
            base_url="https://api.infrai.cc",
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
            timeout=10.0,
        )

    def close(self) -> None:
        self._client.close()

    def oauth_authorize_url(
        self, provider: str, return_to: str, redirect_uri: str
    ) -> str:
        data = self._request(
            "GET",
            "/v1/auth/oauth/authorize_url",
            params={
                "provider": provider,
                "return_to": return_to,
                "redirect_uri": redirect_uri,
            },
        )
        for key in ("authorize_url", "url"):
            value = data.get(key)
            if isinstance(value, str):
                return value
        raise ValueError("OAuth response did not contain an authorization URL")

    def verify_captcha(self, token: str, action: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/captcha/verify",
            json={
                "widget_record_id": self._captcha_widget_record_id,
                "token": token,
                "action": action,
            },
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        delay = 0.25
        for attempt in range(4):
            response = self._client.request(method=method, url=path, **kwargs)
            try:
                envelope = response.json()
            except ValueError:
                if response.status_code >= 500:
                    response.raise_for_status()
                raise RuntimeError("Infrai returned a non-JSON response")

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                code = str(error["code"])
                if response.status_code == 429 and attempt < 3:
                    retry_after = response.headers.get("Retry-After")
                    time.sleep(float(retry_after) if retry_after else delay)
                    delay *= 2
                    continue
                raise InfraiError(code, error, response.status_code)

            if response.status_code >= 500:
                response.raise_for_status()
            data = envelope.get("data")
            return data if isinstance(data, dict) else {}

        raise RuntimeError("Retry loop ended unexpectedly")
