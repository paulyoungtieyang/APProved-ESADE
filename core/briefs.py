"""
Brief versioning — immutable with change tracking.
"""

from sqlalchemy.orm import Session
from core.models import BriefVersion, Engagement
from core.audit import log_event


def create_brief_v1(
    session: Session,
    engagement_id: int,
    deliverable_types: list[str],
    therapeutic_area: str,
    target_markets: list[str],
    regulatory_frameworks: list[str],
    languages: list[str],
    output_formats: list[str],
    tone: str,
    target_audience: str = None,
    focus_area: str = None,
    key_messages: str = None,
    dossier_sections: list[str] = None,
    regional_tender_spec: str = None,
    additional_requirements: str = None,
) -> BriefVersion:
    """Create the first brief version for an engagement."""

    brief = BriefVersion(
        engagement_id=engagement_id,
        version=1,
        created_by="client",
        deliverable_types=deliverable_types,
        therapeutic_area=therapeutic_area,
        target_markets=target_markets,
        regulatory_frameworks=regulatory_frameworks,
        languages=languages,
        output_formats=output_formats,
        tone=tone,
        target_audience=target_audience,
        focus_area=focus_area,
        key_messages=key_messages,
        dossier_sections=dossier_sections,
        regional_tender_spec=regional_tender_spec,
        additional_requirements=additional_requirements,
    )
    session.add(brief)
    session.commit()

    # Log to audit trail
    log_event(
        session,
        engagement_id=engagement_id,
        event_type="brief.submitted",
        actor_type="client",
        actor_identity="client",
        payload={
            "version": 1,
            "therapeutic_area": therapeutic_area,
            "markets": target_markets,
        },
        brief_version_id=brief.id,
    )

    return brief


def amend_brief(
    session: Session,
    engagement_id: int,
    previous_brief: BriefVersion,
    change_reason: str = None,
    **new_fields
) -> BriefVersion:
    """
    Create a new brief version by amending the previous one.

    Only changed fields are passed in new_fields. Unchanged fields
    carry over from previous_brief.
    """

    # Start with all fields from previous version
    brief_data = {
        "deliverable_types": previous_brief.deliverable_types,
        "therapeutic_area": previous_brief.therapeutic_area,
        "target_markets": previous_brief.target_markets,
        "regulatory_frameworks": previous_brief.regulatory_frameworks,
        "languages": previous_brief.languages,
        "output_formats": previous_brief.output_formats,
        "tone": previous_brief.tone,
        "target_audience": previous_brief.target_audience,
        "focus_area": previous_brief.focus_area,
        "key_messages": previous_brief.key_messages,
        "dossier_sections": previous_brief.dossier_sections,
        "regional_tender_spec": previous_brief.regional_tender_spec,
        "additional_requirements": previous_brief.additional_requirements,
    }

    # Calculate diffs and apply changes
    field_diffs = {}
    for key, new_value in new_fields.items():
        if key in brief_data:
            old_value = brief_data[key]
            if old_value != new_value:
                field_diffs[key] = {"old": old_value, "new": new_value}
                brief_data[key] = new_value

    # Create new version
    next_version = previous_brief.version + 1
    new_brief = BriefVersion(
        engagement_id=engagement_id,
        version=next_version,
        created_by="client",
        previous_version_id=previous_brief.id,
        change_reason=change_reason,
        field_diffs=field_diffs if field_diffs else None,
        **brief_data
    )
    session.add(new_brief)
    session.commit()

    # Log to audit trail
    log_event(
        session,
        engagement_id=engagement_id,
        event_type="brief.revised",
        actor_type="client",
        actor_identity="client",
        payload={
            "version": next_version,
            "previous_version": previous_brief.version,
            "change_reason": change_reason,
            "diffs": field_diffs,
        },
        brief_version_id=new_brief.id,
    )

    return new_brief


def get_latest_brief(session: Session, engagement_id: int) -> BriefVersion:
    """Get the most recent brief version for an engagement."""
    return (
        session.query(BriefVersion)
        .filter_by(engagement_id=engagement_id)
        .order_by(BriefVersion.version.desc())
        .first()
    )


def brief_as_dict(brief: BriefVersion) -> dict:
    """Serialize a brief to a dictionary."""
    return {
        "version": brief.version,
        "created_at": brief.created_at.isoformat(),
        "deliverable_types": brief.deliverable_types,
        "therapeutic_area": brief.therapeutic_area,
        "target_markets": brief.target_markets,
        "regulatory_frameworks": brief.regulatory_frameworks,
        "languages": brief.languages,
        "output_formats": brief.output_formats,
        "tone": brief.tone,
        "target_audience": brief.target_audience,
        "focus_area": brief.focus_area,
        "key_messages": brief.key_messages,
        "dossier_sections": brief.dossier_sections,
        "regional_tender_spec": brief.regional_tender_spec,
        "additional_requirements": brief.additional_requirements,
    }
