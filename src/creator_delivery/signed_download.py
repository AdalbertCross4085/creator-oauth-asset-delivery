from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from urllib.parse import urlencode


@dataclass(frozen=True)
class Asset:
    asset_id: str
    title: str
    download_path: str
    subscriber_only: bool
    content: str


class SignedDownload:
    def __init__(self, signing_secret: str, public_origin: str) -> None:
        self._secret = signing_secret.encode()
        self._origin = public_origin.rstrip("/")

    def create(self, asset: Asset, user_id: str, expires_at: int) -> str:
        message = f"{asset.asset_id}:{user_id}:{expires_at}".encode()
        signature = hmac.new(self._secret, message, hashlib.sha256).hexdigest()
        query = urlencode(
            {"asset_id": asset.asset_id, "user_id": user_id, "expires": expires_at, "sig": signature}
        )
        return f"{self._origin}{asset.download_path}?{query}"

