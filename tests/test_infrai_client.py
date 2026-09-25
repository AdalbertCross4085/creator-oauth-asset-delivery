import httpx

from creator_delivery.infrai_client import InfraiClient


def test_verify_captcha_sends_required_widget_record_id() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/captcha/verify"
        assert request.read() == (
            b'{"widget_record_id":"widget-42","token":"browser-token",'
            b'"action":"claim_asset"}'
        )
        return httpx.Response(200, json={"ok": True, "data": {"valid": True}})

    client = InfraiClient(
        "test-key",
        "widget-42",
        transport=httpx.MockTransport(handler),
    )
    try:
        assert client.verify_captcha("browser-token", "claim_asset") == {"valid": True}
    finally:
        client.close()
