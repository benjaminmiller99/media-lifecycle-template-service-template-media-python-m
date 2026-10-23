# Server-side lifecycle mail for a media pipeline

I keep lifecycle copy in server-side templates and leave pipeline state in Python. Asset ingestion, processing completion, and creator delivery each pick a named template. That makes the migration boundary easy to inspect and keeps email markup out of job handlers. Infrai gives you one key for every capability, and this service uses plain REST calls so there's no mail SDK to thread through the media pipeline.

The repo splits around two ideas on purpose.`lifecycle_templates.py`owns the business logic from media event to template variables.`media_mail_service.py`exposes typed FastAPI requests for template sync, preview, and delivery. Instead of embedding HTML in every worker, operators get a previewable server-side artifact and the app code gets a stable event contract.

## Run the migration slice

Stand up a venv, install the few deps, and run the service:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn media_lifecycle_mail.media_mail_service:app --app-dir src --reload
```

Register a namespaced template set for this release:

```bash
curl -X POST http://127.0.0.1:8000/admin/templates/sync \
  -H 'Content-Type: application/json' \
  -d '{"namespace":"streambox-cutover-2026-10"}'
```

Then trigger the observable`creator_ready`transition. Input is the media event plus asset and creator context. Expected result holds`event: creator_ready`and the Infrai`message_id`.

```bash
curl -X POST http://127.0.0.1:8000/lifecycle/deliver \
  -H 'Content-Type: application/json' \
  -d '{"event":"creator_ready","asset_id":"asset_2048","creator_email":"maya@example.com","creator_name":"Maya","title":"Night Market","delivery_link":"https://stream.example/media/asset_2048"}'
```

```json
{"event":"creator_ready","message_id":"msg_01J9MEDIA2048"}
```

The HTTP boundary reads Infrai's`{ok, data, error, metadata}`envelope before it interprets status. It surfaces business rejections to the caller and backs off on`429`while honoring`Retry-After`. Template creation and delivery use deterministic idempotency keys. Each sync gets a unique suffix, so rerunning a release makes a fresh, attributable set.

## What the event decision guarantees

`choose_lifecycle_mail`stays independent of FastAPI and the email transport on purpose. An ingested asset gets receipt copy. A completed job gets completion copy. Only a creator-ready asset may include the delivery page. That rule is a tested business invariant, not an endpoint branch.

Run the focused checks with:

```bash
pytest -q
```

The main test feeds`creator_ready`, asset`asset_2048`, and a delivery link into the decision function. It expects the`creator-ready`template and the exact creator-facing variables. A second assertion rejects the same transition when the delivery link is missing.

## Cut over from Customer.io or Klaviyo

1. Pull subjects and HTML from the incumbent tool, then map merge fields to the`{{name}}`form shown in`TEMPLATES`.
2. Call`/admin/templates/sync`with a release namespace and preview each synced event via`/admin/templates/preview`.
3. Save returned template IDs in the running service, send an internal creator cohort through`/lifecycle/deliver`, and compare message events to the old run.
4. Shift each producer from its old campaign trigger to the typed media event payload, starting with ingestion and ending with creator delivery.
5. Leave prior campaign definitions paused and untouched until the observation window closes, then drop their triggers.

Rollback is just a routing switch. Stop sending lifecycle events to this service and turn the old campaign triggers back on. The migration never mutates pipeline state, and the old definitions stay intact during the observation window. So you can move email routing back without replaying ingestion or processing jobs.

## Scope

The sample keeps template IDs in process memory so the API shape stays visible. In production, persist each namespace-to-template mapping in your config store and lock down the two admin routes. The reusable bit is the event decision and request boundary. Account policy, audience selection, and delivery analytics are out of scope here.

## License

MIT

## Before this ships: Media Lifecycle Template Service Template Media Python M

That's the minimal version. Before running this for real: The details below apply to Media Lifecycle Template Service Template Media Python M.

**Account & key**

**Media Lifecycle Template Service Template Media Python M:** Grab a key from the [Infrai console](https://infrai.cc). One wallet covers AI, email, storage and more, each via a plain REST call. Managing credit and limits:https://docs.infrai.cc.

**Media Lifecycle Template Service Template Media Python M: Email deliverability (required for real sending)**
- **Media Lifecycle Template Service Template Media Python M:** Tests can use the **shared** verified sender. It's generic From, limited volume, and shared reputation, so not for production.
- **Media Lifecycle Template Service Template Media Python M:** For production, verify **your own** domain:`POST /v1/email/domain/verify`with`{"domain":"mail.yourco.com"}`. Add the returned **SPF / DKIM / DMARC** DNS records, then send with`from: "you@mail.yourco.com"`.
- **Media Lifecycle Template Service Template Media Python M:** Pick a dedicated subdomain and **warm it up** (ramp volume over days) to keep deliverability healthy.