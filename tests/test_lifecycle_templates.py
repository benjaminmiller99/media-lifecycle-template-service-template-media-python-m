import pytest

from media_lifecycle_mail.lifecycle_templates import MediaEvent, choose_lifecycle_mail


def test_creator_ready_selects_delivery_template_and_link() -> None:
    mail = choose_lifecycle_mail(
        event=MediaEvent.CREATOR_READY,
        asset_id="asset_2048",
        creator_email="maya@example.com",
        creator_name="Maya",
        title="Night Market",
        delivery_link="https://stream.example/media/asset_2048",
    )

    assert mail.template_slug == "creator-ready"
    assert mail.recipient == "maya@example.com"
    assert mail.template_vars == {
        "asset_id": "asset_2048",
        "creator_name": "Maya",
        "title": "Night Market",
        "delivery_link": "https://stream.example/media/asset_2048",
    }


def test_creator_ready_requires_a_delivery_link() -> None:
    with pytest.raises(ValueError, match="delivery_link is required"):
        choose_lifecycle_mail(
            event=MediaEvent.CREATOR_READY,
            asset_id="asset_2048",
            creator_email="maya@example.com",
            creator_name="Maya",
            title="Night Market",
            delivery_link=None,
        )

