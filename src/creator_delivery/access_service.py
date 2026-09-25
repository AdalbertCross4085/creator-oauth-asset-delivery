from __future__ import annotations

from dataclasses import dataclass
from time import time
from typing import Protocol

from .content_processor import ProcessedContent, process_asset_content
from .signed_download import Asset, SignedDownload


class CaptchaVerifier(Protocol):
    def verify_captcha(self, token: str, action: str) -> dict[str, object]:
        pass


@dataclass(frozen=True)
class OAuthIdentity:
    user_id: str
    provider: str
    email: str


@dataclass(frozen=True)
class DeliveryResult:
    status: str
    preview: str
    content_digest: str
    download_url: str | None
    subscriber_update: str


class CreatorAccessService:
    def __init__(
        self,
        captcha: CaptchaVerifier,
        signer: SignedDownload,
        assets: dict[str, Asset],
        subscribers: set[str],
    ) -> None:
        self._captcha = captcha
        self._signer = signer
        self._assets = assets
        self._subscribers = subscribers

    def deliver(
        self, identity: OAuthIdentity, asset_id: str, captcha_token: str
    ) -> DeliveryResult:
        self._captcha.verify_captcha(captcha_token, action="claim_asset")
        asset = self._assets[asset_id]
        processed: ProcessedContent = process_asset_content(asset.content)
        has_access = not asset.subscriber_only or identity.user_id in self._subscribers

        if not has_access:
            return DeliveryResult(
                status="subscription_required",
                preview=processed.preview,
                content_digest=processed.digest,
                download_url=None,
                subscriber_update="none",
            )

        return DeliveryResult(
            status="ready",
            preview=processed.preview,
            content_digest=processed.digest,
            download_url=self._signer.create(asset, identity.user_id, int(time()) + 900),
            subscriber_update=f"asset_ready:{asset.asset_id}",
        )

