"""FastAPI entry point for synchronizing and delivering media lifecycle mail."""

from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl

from .infrai_client import InfraiError, infrai
from .lifecycle_templates import MediaEvent, TEMPLATES, choose_lifecycle_mail


class TemplateSyncRequest(BaseModel):
    namespace: str


class TemplatePreviewRequest(BaseModel):
    event: MediaEvent
    creator_name: str
    title: str
    asset_id: str
    delivery_link: HttpUrl | None = None


class MediaLifecycleRequest(BaseModel):
    event: MediaEvent
    asset_id: str
    creator_email: str
    creator_name: str
    title: str
    delivery_link: HttpUrl | None = None


app = FastAPI(title="Media lifecycle mail service")
template_ids: dict[str, str] = {}


@app.exception_handler(InfraiError)
async def handle_infrai_error(_request: Request, exc: InfraiError) -> JSONResponse:
    status = exc.status_code if 400 <= exc.status_code < 500 else 502
    return JSONResponse(status_code=status, content={"error": exc.detail})


@app.post("/admin/templates/sync")
def sync_templates(request: TemplateSyncRequest) -> dict[str, dict[str, str]]:
    """Create one namespaced template set for the migration or release run."""
    run_id = uuid4().hex[:10]
    created: dict[str, str] = {}
    for event, definition in TEMPLATES.items():
        name = f"{request.namespace}-{definition.slug}-{run_id}"
        data = infrai.email.template.create(
            name=name,
            subject=definition.subject,
            html=definition.html,
        )
        created[event.value] = data["template_id"]
    template_ids.update(created)
    return {"template_ids": created}


@app.post("/admin/templates/preview")
def preview_template(request: TemplatePreviewRequest) -> dict[str, object]:
    template_id = template_ids.get(request.event.value)
    if not template_id:
        raise HTTPException(status_code=409, detail="sync templates before previewing")
    return infrai.email.template.preview(template_id)


@app.post("/lifecycle/deliver")
def deliver_lifecycle_mail(request: MediaLifecycleRequest) -> dict[str, str]:
    template_id = template_ids.get(request.event.value)
    if not template_id:
        raise HTTPException(status_code=409, detail="sync templates before delivery")
    try:
        mail = choose_lifecycle_mail(
            event=request.event,
            asset_id=request.asset_id,
            creator_email=str(request.creator_email),
            creator_name=request.creator_name,
            title=request.title,
            delivery_link=str(request.delivery_link) if request.delivery_link else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    data = infrai.email.send(
        {
            "to": mail.recipient,
            "template_id": template_id,
            "template_vars": mail.template_vars,
        },
        f"lifecycle:{request.asset_id}:{request.event.value}",
    )
    return {"event": request.event.value, "message_id": data["message_id"]}
