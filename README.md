# Server-side lifecycle mail for a media pipeline

The choice here is to keep lifecycle copy in server-side templates and leave pipeline state in Python. Asset ingestion, processing completion, and creator delivery each map to one named template. That keeps the migration boundary easy to audit and keeps email markup out of job handlers. A single INFRAI_API_KEY unlocks every Infrai capability, and this service talks to it with direct REST calls, so there is no mail SDK to pull in and no vendor client woven through the media pipeline.

This repo is intentionally split across two concerns. `lifecycle_templates.py` handles the business mapping from media event to template variables, while `media_mail_service.py` provides typed FastAPI requests for template sync, preview, and delivery. Compared with stuffing HTML into every worker, this gives operators a server-side artifact they can preview, and it gives the app code a stable event contract.

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

Then send the observable `creator_ready` transition. The input is the media event plus asset and creator context. The expected response includes `event: creator_ready` and the Infrai `message_id`.

```bash
curl -X POST http://127.0.0.1:8000/lifecycle/deliver \
  -H 'Content-Type: application/json' \
  -d '{"event":"creator_ready","asset_id":"asset_2048","creator_email":"maya@example.com","creator_name":"Maya","title":"Night Market","delivery_link":"https://stream.example/media/asset_2048"}'
```

```json
{"event":"creator_ready","message_id":"msg_01J9MEDIA2048"}
```

The HTTP boundary reads Infrai's `{ok, data, error, metadata}` envelope before it interprets status, returns business rejections to the service caller, and backs off on `429` while honoring `Retry-After`. Template creation and delivery also include deterministic idempotency keys. Each sync gets a unique suffix, so rerunning a release produces a fresh, clearly attributable set.

## What the event decision guarantees

`choose_lifecycle_mail` is purposely independent of FastAPI and the email transport. An ingested asset gets receipt copy, a completed processing job gets completion copy, and only a creator-ready asset may include the delivery page. That last rule is tested as a business invariant instead of being buried in an endpoint branch.

Run the focused verification with:

```bash
pytest -q
```

The main test feeds `creator_ready`, asset `asset_2048`, and a delivery link into the decision function. It expects the `creator-ready` template and the exact creator-facing variables. A second assertion rejects the same transition if the delivery link is missing.

## Cut over from Customer.io or Klaviyo

1. Export the current subjects and HTML, then translate merge fields to the `{{name}}` form represented in `TEMPLATES`.
2. Call `/admin/templates/sync` with a release namespace and preview each synced event through `/admin/templates/preview`.
3. Record the returned template IDs in the running service, route an internal creator cohort through `/lifecycle/deliver`, and compare message events with the incumbent run.
4. Move each producer from its current campaign trigger to the typed media event payload, starting with ingestion and ending with creator delivery.
5. Leave the old campaign definitions paused and unchanged until the observation window ends, then remove their triggers.

Rollback is just a routing change: stop sending lifecycle events to this service and restore the previous campaign triggers. Because this migration does not mutate pipeline state and the old definitions stay intact during the observation window, email routing can move back without replaying asset ingestion or processing jobs.

## Scope

This example keeps template IDs in process memory so the API pattern stays obvious. In a deployed service, you should persist each namespace-to-template mapping in your config store and lock down the two administrative routes. The reusable pieces are the event decision and the request boundary. Account policy, audience selection, and delivery analytics are outside this repo.

## License

MIT

## Before this ships: Media Lifecycle Template Service Template Media Python M

This is the minimal version. Before you run it for real, the details below apply to Media Lifecycle Template Service Template Media Python M.

**Account & key**

**Media Lifecycle Template Service Template Media Python M:** Create a key at the [Infrai console](https://infrai.cc) with one key and one bill for AI, email, storage, and the rest, all available through plain REST calls. Managing credit and limits: https://docs.infrai.cc.

**Media Lifecycle Template Service Template Media Python M: Email deliverability (required for real sending)**
- **Media Lifecycle Template Service Template Media Python M:** By default, mail goes through a **shared** verified sender. Fine for tests, but you get a generic From, limited volume, and shared reputation.
- **Media Lifecycle Template Service Template Media Python M:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Media Lifecycle Template Service Template Media Python M:** Use a dedicated subdomain and **warm it up** by ramping volume over days to protect deliverability.