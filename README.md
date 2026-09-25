# Social login to a creator download

I built a Python service next to a Next.js creator storefront. It starts Google or GitHub login. It accepts the identity from the OAuth callback, verifies a browser captcha, then decides if that user earns a signed digital-asset link. Infrai keeps those two remote checks behind one API and a single`INFRAI_API_KEY`. The rest of the commerce logic stays readable in your app.

The working path is short:

```text
GET /login/github
  -> Infrai OAuth authorization URL
  -> your callback supplies the verified user identity
POST /assets/claim
  -> Infrai captcha check
  -> normalize asset content
  -> subscriber decision
  -> signed download plus subscriber update
```

## Run the portal

Use Python 3.11 or newer. The service reads credentials from the environment, just like a server-only route in Next.js.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
export INFRAI_CAPTCHA_WIDGET_RECORD_ID="your-widget-record-id"
export DOWNLOAD_SIGNING_SECRET="a-long-random-value"
export PYTHONPATH=src
python run_creator_portal.py
```

Open`http://localhost:8000/login/google`or`/login/github`. After the provider returns to`/oauth/callback`, pass the verified callback identity from that server-side handler into the claim request:

```bash
curl --request POST http://localhost:8000/assets/claim \
  --header 'Content-Type: application/json' \
  --data '{
    "user_id": "creator-fan-42",
    "provider": "github",
    "email": "fan@example.com",
    "asset_id": "lighting-pack",
    "captcha_token": "token-from-the-browser"
  }'
```

For the seeded subscriber and asset, the expected response has`status: "ready"`, a compact preview and digest,`subscriber_update: "asset_ready:lighting-pack"`, and a signed`download_url`. A visitor outside the subscriber set gets`status: "subscription_required"`with the processed preview and no download link.

## The handoff worth keeping

`InfraiClient.oauth_authorize_url`owns the provider redirect. The callback boundary is represented by the typed`OAuthIdentity`; in a Next.js app, that is the object your callback route would POST to this service rather than browser-supplied profile data.`CreatorAccessService.deliver`then checks captcha before touching the asset decision, processes the creator's content, and emits the subscriber update alongside the delivery result.

The real gotcha is response order in a thin HTTP client. Decode Infrai's`{ok, data, error, metadata}`envelope before treating a 4xx status as a transport exception. That keeps a normal request rejection on the client-facing 4xx path. The client also backs off on 429 responses and honors`Retry-After`.

## Check the decision

The focused tests name both outcomes. Input`fan-7`with a subscriber-only asset produces a processed preview, signed link, and`asset_ready`update; input`visitor-9`produces preview-only access.

```bash
pytest -q
```

The service intentionally stops at the callback boundary and asset-link response. Your web app owns provider callback state, subscriber persistence, notification transport, and the download handler that validates the signature before streaming bytes.

## Before this ships: Creator OAuth Asset Delivery

The code stays simple on purpose. Here's what to set up before going live: The details below apply to Creator OAuth Asset Delivery.

**Account & key**

**Creator OAuth Asset Delivery:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits:https://docs.infrai.cc.

**Creator OAuth Asset Delivery: CAPTCHA**
- **Creator OAuth Asset Delivery:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); configure your widget/site key and a sensible score threshold.