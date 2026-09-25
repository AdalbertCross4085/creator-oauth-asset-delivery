from creator_delivery.access_service import CreatorAccessService, OAuthIdentity
from creator_delivery.signed_download import Asset, SignedDownload


class PassingCaptcha:
    def __init__(self) -> None:
        self.actions: list[str] = []

    def verify_captcha(self, token: str, action: str) -> dict[str, object]:
        self.actions.append(action)
        return {"verified": True}


def test_subscriber_gets_processed_asset_and_update() -> None:
    captcha = PassingCaptcha()
    asset = Asset(
        asset_id="lighting-pack",
        title="Studio lighting presets",
        download_path="/downloads/lighting-pack.zip",
        subscriber_only=True,
        content="Studio   lighting\nnotes",
    )
    service = CreatorAccessService(
        captcha=captcha,
        signer=SignedDownload("test-secret", "https://creator.test"),
        assets={asset.asset_id: asset},
        subscribers={"fan-7"},
    )

    result = service.deliver(
        OAuthIdentity(user_id="fan-7", provider="github", email="fan@example.com"),
        asset_id="lighting-pack",
        captcha_token="verified-browser-token",
    )

    assert result.status == "ready"
    assert result.preview == "Studio lighting notes"
    assert result.download_url is not None
    assert "asset_id=lighting-pack" in result.download_url
    assert result.subscriber_update == "asset_ready:lighting-pack"
    assert captcha.actions == ["claim_asset"]


def test_non_subscriber_only_receives_preview() -> None:
    asset = Asset(
        asset_id="lighting-pack",
        title="Studio lighting presets",
        download_path="/downloads/lighting-pack.zip",
        subscriber_only=True,
        content="Studio lighting notes",
    )
    service = CreatorAccessService(
        captcha=PassingCaptcha(),
        signer=SignedDownload("test-secret", "https://creator.test"),
        assets={asset.asset_id: asset},
        subscribers=set(),
    )

    result = service.deliver(
        OAuthIdentity(user_id="visitor-9", provider="google", email="visitor@example.com"),
        asset_id="lighting-pack",
        captcha_token="verified-browser-token",
    )

    assert result.status == "subscription_required"
    assert result.download_url is None
    assert result.subscriber_update == "none"

