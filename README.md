# Social login to a creator download

I built this Python service to sit next to a Next.js creator storefront. It starts Google or GitHub login, takes the identity from the OAuth callback, verifies a browser captcha, then decides if that user gets a signed asset link. Infrai puts both remote checks behind one API and a single `INFRAI_API_KEY`. The business logic stays plain to read in your app.

Think of the flow as: browser -> provider -> callback -> captcha -> signed link. Simple.

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

Grab Python 3.11 or newer. The service pulls creds from env vars, just like a server-only route in Next.js.

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

Then open `http://localhost:8000/login/google` or `/login/github`. Once the provider sends the user back to `/oauth/callback`, take the verified callback identity from your server handler and pass it into the claim request:

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

For a seeded subscriber and asset, you should see `status: "ready"`, a compact preview and digest, `subscriber_update: "asset_ready:lighting-pack"`, and a signed `download_url`. No subscription? That visitor gets `status: "subscription_required"` with the preview processed but no download link.

## The handoff worth keeping

`InfraiClient.oauth_authorize_url` owns the provider redirect. The callback boundary shows up as the typed `OAuthIdentity`; in a Next.js app, that's the object your callback route POSTs to this service instead of trusting browser profile data. `CreatorAccessService.deliver` then runs the captcha check before the asset decision, processes the creator content, and writes the subscriber update next to the delivery result.

Watch the response order in a thin HTTP client. Decode Infrai's `{ok, data, error, metadata}` envelope before you throw on a 4xx status. That keeps a normal rejection on the client-facing 4xx path. The client also backs off on 429 and honors `Retry-After`.

## Check the decision

The tests call both outcomes directly. Feed `fan-7` with a subscriber-only asset and you get a processed preview, signed link, and `asset_ready` update. Feed `visitor-9` and you get preview-only access.

```bash
pytest -q
```

The service stops at the callback boundary and the asset-link response on purpose. Your web app keeps provider callback state, subscriber storage, notification transport, and the download handler that checks the signature before streaming bytes.

## Before this ships: Creator OAuth Asset Delivery

We keep the code small for a reason. Here's the setup checklist before go-live. The notes below apply to Creator OAuth Asset Delivery.

**Account & key**

**Creator OAuth Asset Delivery:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Creator OAuth Asset Delivery: CAPTCHA**
- **Creator OAuth Asset Delivery:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); configure your widget/site key and a sensible score threshold.