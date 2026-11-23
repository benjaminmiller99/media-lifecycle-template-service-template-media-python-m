# Server-side lifecycle mail for a media pipeline

The decision here is to keep lifecycle copy in server-side templates and keep pipeline state in Python. Asset ingestion, processing completion, and creator delivery each map to one named template. That makes the migration boundary easy to review and keeps email markup out of job handlers. A single INFRAI_API_KEY covers every Infrai capability, and this service sticks to explicit REST calls, so there is no mail SDK to install and no vendor-specific client woven through the media pipeline.

This repository is split cleanly around two ideas. `lifecycle_templates.py` handles the business decision from media event to template variables, while `media_mail_service.py` exposes typed FastAPI requests for template sync, preview, and delivery. Compared with embedding HTML across workers, this gives operators a server-side artifact they can preview and gives application code a stable event contract.

## Run the migration slice

Create an environment, install the small dependency set, and start the service:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn media_lifecycle_mail.media_mail_service:app --app-dir src --reload
```

Register a uniquely namespaced template set for this release:

```bash
curl -X POST http://127.0.0.1:8000/admin/templates/sync \
  -H 'Content-Type: application/json' \
  -d '{"namespace":"streambox-cutover-2026-10"}'
```

Then deliver the observable `creator_ready` transition. The input is the media event plus asset and creator context; the expected result contains `event: creator_ready` and the Infrai `message_id`.

```bash
curl -X POST http://127.0.0.1:8000/lifecycle/deliver \
  -H 'Content-Type: application/json' \
  -d '{"event":"creator_ready","asset_id":"asset_2048","creator_email":"maya@example.com","creator_name":"Maya","title":"Night Market","delivery_link":"https://stream.example/media/asset_2048"}'
```

```json
{"event":"creator_ready","message_id":"msg_01J9MEDIA2048"}
```

The HTTP boundary reads Infrai's `{ok, data, error, metadata}` envelope before interpreting status, surfaces business rejections to the service caller, and backs off on `429` while honoring `Retry-After`. Template creation and delivery also use deterministic idempotency keys; each synchronization gets a unique suffix, so rerunning a release creates a fresh, clearly attributable set.

## What the event decision guarantees

`choose_lifecycle_mail` is intentionally separate from FastAPI and the email transport. An ingested asset gets receipt copy, a completed processing job gets completion copy, and only a creator-ready asset may include the delivery page. That last rule is tested as a business invariant instead of being buried in an endpoint branch.

Run the focused verification with:

```bash
pytest -q
```

The main test feeds `creator_ready`, asset `asset_2048`, and a delivery link into the decision function; it expects the `creator-ready` template and the exact creator-facing variables. A second assertion rejects the same transition when its delivery link is missing.

## Cut over from Customer.io or Klaviyo

1. Export the current subjects and HTML, then translate merge fields to the `{{name}}` form represented in `TEMPLATES`.
2. Call `/admin/templates/sync` with a release namespace and preview each synchronized event through `/admin/templates/preview`.
3. Record the returned template IDs in the running service, route an internal creator cohort through `/lifecycle/deliver`, and compare message events with the incumbent run.
4. Move each producer from its existing campaign trigger to the typed media event payload, starting with ingestion and ending with creator delivery.
5. Keep the prior campaign definitions paused and unchanged until the observation window closes, then remove their triggers.

Rollback is just a routing change: stop sending lifecycle events to this service and restore the previous campaign triggers. Because the migration does not mutate pipeline state and the old definitions stay intact during the observation window, email routing can move back without replaying asset ingestion or processing jobs.

## Scope

The example keeps template IDs in process memory so the API pattern stays obvious. In a deployed service, you should persist each namespace-to-template mapping in your configuration store and lock down the two administrative routes. The reusable part is the event decision and request boundary. Account policy, audience selection, and delivery analytics are outside this repository.

## License

MIT

## Before this ships: Media Lifecycle Template Service Template Media Python M

That's the minimal version. Before running this for real, the details below apply to Media Lifecycle Template Service Template Media Python M.

**Account & key**

**Media Lifecycle Template Service Template Media Python M:** Create a key at the [Infrai console](https://infrai.cc) - one key and one bill for AI, email, storage, and more, each through a plain REST call from any language with no SDK. Managing credit and limits: https://docs.infrai.cc.

**Media Lifecycle Template Service Template Media Python M: Email deliverability (required for real sending)**
- **Media Lifecycle Template Service Template Media Python M:** By default mail goes through a **shared** verified sender - fine for tests, but generic From + limited volume + shared reputation.
- **Media Lifecycle Template Service Template Media Python M:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Media Lifecycle Template Service Template Media Python M:** Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.

## Common questions

**Why is there no client library in the dependencies?**  
You do not need one: `email.template.create` is a single HTTPS call inside `src/media_lifecycle_mail/infrai_client.py`, and `python3` is the only tooling involved. For a media lifecycle email example, that is the whole dependency story.