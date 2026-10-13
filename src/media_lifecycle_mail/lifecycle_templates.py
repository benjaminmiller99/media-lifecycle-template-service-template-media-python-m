"""The domain decision: turn a media pipeline event into a lifecycle mail."""

from dataclasses import dataclass
from enum import Enum


class MediaEvent(str, Enum):
    ASSET_INGESTED = "asset_ingested"
    PROCESSING_COMPLETE = "processing_complete"
    CREATOR_READY = "creator_ready"


@dataclass(frozen=True)
class TemplateDefinition:
    slug: str
    subject: str
    html: str


@dataclass(frozen=True)
class LifecycleMail:
    template_slug: str
    recipient: str
    template_vars: dict[str, str]


TEMPLATES: dict[MediaEvent, TemplateDefinition] = {
    MediaEvent.ASSET_INGESTED: TemplateDefinition(
        slug="asset-ingested",
        subject="{{title}} is safely in the processing queue",
        html=(
            "<h1>Upload received</h1><p>Hi {{creator_name}}, we received "
            "<strong>{{title}}</strong>. Its asset reference is {{asset_id}}.</p>"
        ),
    ),
    MediaEvent.PROCESSING_COMPLETE: TemplateDefinition(
        slug="processing-complete",
        subject="Processing finished for {{title}}",
        html=(
            "<h1>Your media is processed</h1><p>Hi {{creator_name}}, "
            "<strong>{{title}}</strong> has finished processing.</p>"
        ),
    ),
    MediaEvent.CREATOR_READY: TemplateDefinition(
        slug="creator-ready",
        subject="{{title}} is ready for delivery",
        html=(
            "<h1>Ready to review</h1><p>Hi {{creator_name}}, "
            "<strong>{{title}}</strong> is ready at "
            "<a href=\"{{delivery_link}}\">your delivery page</a>.</p>"
        ),
    ),
}


def choose_lifecycle_mail(
    *,
    event: MediaEvent,
    asset_id: str,
    creator_email: str,
    creator_name: str,
    title: str,
    delivery_link: str | None,
) -> LifecycleMail:
    """Select the mail and expose the state transition through its variables."""
    if event is MediaEvent.CREATOR_READY and not delivery_link:
        raise ValueError("delivery_link is required when media is ready")

    template_vars = {
        "asset_id": asset_id,
        "creator_name": creator_name,
        "title": title,
    }
    if delivery_link:
        template_vars["delivery_link"] = delivery_link

    return LifecycleMail(
        template_slug=TEMPLATES[event].slug,
        recipient=creator_email,
        template_vars=template_vars,
    )

