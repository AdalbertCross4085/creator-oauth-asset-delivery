from __future__ import annotations

import os
from typing import Literal

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field

from .access_service import CreatorAccessService, OAuthIdentity
from .infrai_client import InfraiClient, InfraiError
from .signed_download import Asset, SignedDownload


class ClaimAssetRequest(BaseModel):
    user_id: str = Field(min_length=1)
    provider: Literal["google", "github"]
    email: EmailStr
    asset_id: str = Field(min_length=1)
    captcha_token: str = Field(min_length=1)


class ClaimAssetResponse(BaseModel):
    status: Literal["ready", "subscription_required"]
    preview: str
    content_digest: str
    download_url: str | None
    subscriber_update: str


def create_app(
    transport: httpx.BaseTransport | None = None,
    subscribers: set[str] | None = None,
) -> FastAPI:
    api_key = os.environ["INFRAI_API_KEY"]
    captcha_widget_record_id = os.environ["INFRAI_CAPTCHA_WIDGET_RECORD_ID"]
    signing_secret = os.environ["DOWNLOAD_SIGNING_SECRET"]
    public_origin = os.environ.get("PUBLIC_ORIGIN", "http://localhost:8000")
    callback_url = f"{public_origin}/oauth/callback"
    client = InfraiClient(api_key, captcha_widget_record_id, transport=transport)
    assets = {
        "lighting-pack": Asset(
            asset_id="lighting-pack",
            title="Studio lighting presets",
            download_path="/downloads/lighting-pack.zip",
            subscriber_only=True,
            content="A practical preset pack for consistent indoor creator shoots.",
        )
    }
    service = CreatorAccessService(
        captcha=client,
        signer=SignedDownload(signing_secret, public_origin),
        assets=assets,
        subscribers=subscribers if subscribers is not None else {"creator-fan-42"},
    )
    app = FastAPI(title="Creator OAuth delivery")

    @app.on_event("shutdown")
    def close_client() -> None:
        client.close()

    @app.get("/login/{provider}")
    def login(provider: Literal["google", "github"]) -> RedirectResponse:
        try:
            url = client.oauth_authorize_url(
                provider=provider,
                return_to="/assets/lighting-pack",
                redirect_uri=callback_url,
            )
            return RedirectResponse(url=url, status_code=302)
        except InfraiError as error:
            raise HTTPException(status_code=error.status_code, detail=error.details) from error

    @app.post("/assets/claim", response_model=ClaimAssetResponse)
    def claim_asset(request: ClaimAssetRequest) -> ClaimAssetResponse:
        identity = OAuthIdentity(
            user_id=request.user_id,
            provider=request.provider,
            email=str(request.email),
        )
        try:
            result = service.deliver(identity, request.asset_id, request.captcha_token)
        except InfraiError as error:
            raise HTTPException(status_code=error.status_code, detail=error.details) from error
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Asset not found") from error
        return ClaimAssetResponse(**result.__dict__)

    return app


app = create_app()
