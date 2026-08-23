"""
Append-only audit trail — never update, never delete.
"""

from datetime import datetime
from sqlalchemy.orm import Session
from core.models import AuditEvent


def log_event(
    session: Session,
    engagement_id: int,
    event_type: str,
    actor_type: str,  # "client", "user", "system"
    actor_identity: str,  # username or "system" or "client"
    payload: dict = None,
    brief_version_id: int = None,
    uploaded_file_id: int = None,
    generation_run_id: int = None,
    review_round_id: int = None,
) -> AuditEvent:
    """
    Log an event to the audit trail.

    Never overwrites or deletes existing events — only appends.
    API keys must NEVER appear in payload.
    """
    event = AuditEvent(
        engagement_id=engagement_id,
        event_type=event_type,
        actor_type=actor_type,
        actor_identity=actor_identity,
        payload=payload or {},
        brief_version_id=brief_version_id,
        uploaded_file_id=uploaded_file_id,
        generation_run_id=generation_run_id,
        review_round_id=review_round_id,
        created_at=datetime.utcnow(),
    )
    session.add(event)
    session.commit()
    return event


def get_engagement_trail(session: Session, engagement_id: int) -> list[AuditEvent]:
    """Retrieve the full audit trail for an engagement, in order."""
    return session.query(AuditEvent).filter_by(engagement_id=engagement_id).order_by(AuditEvent.created_at).all()


def export_audit_trail_json(session: Session, engagement_id: int) -> list[dict]:
    """Export audit trail as structured JSON."""
    events = get_engagement_trail(session, engagement_id)
    return [
        {
            "timestamp": event.created_at.isoformat(),
            "event_type": event.event_type,
            "actor_type": event.actor_type,
            "actor_identity": event.actor_identity,
            "payload": event.payload,
            "entity_refs": {
                "brief_version_id": event.brief_version_id,
                "uploaded_file_id": event.uploaded_file_id,
                "generation_run_id": event.generation_run_id,
                "review_round_id": event.review_round_id,
            },
        }
        for event in events
    ]


def export_audit_trail_md(session: Session, engagement_id: int) -> str:
    """Export audit trail as a Markdown document for regulatory submission."""
    from datetime import datetime as dt
    events = get_engagement_trail(session, engagement_id)

    lines = [
        "# Audit Trail — Complete Event History\n",
        f"**Exported:** {dt.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n",
        "**Status:** Append-only record. All timestamps are UTC.\n",
    ]

    for event in events:
        lines.append(f"\n## {event.event_type.upper()}")
        lines.append(f"- **Time:** {event.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"- **Actor:** {event.actor_identity} ({event.actor_type})")

        if event.payload:
            payload = event.payload
            if event.event_type.startswith('generation'):
                if payload.get('section'):
                    lines.append(f"- **Section:** {payload['section']}")
                if payload.get('round'):
                    lines.append(f"- **Round:** {payload['round']}")
                if payload.get('provider'):
                    lines.append(f"- **Provider:** {payload['provider']}")
                if payload.get('model'):
                    lines.append(f"- **Model:** {payload['model']}")

                if event.event_type == 'generation.refined' and payload.get('instruction'):
                    lines.append("\n### Expert Refinement Instruction")
                    lines.append(payload['instruction'])

                if payload.get('resolved_prompt'):
                    lines.append("\n### Prompt Sent to LLM")
                    prompt = payload['resolved_prompt']
                    lines.append(f"```\n{prompt[:2000]}")
                    if len(prompt) > 2000:
                        lines.append(f"\n... ({len(prompt) - 2000} more characters)\n```")
                    else:
                        lines.append("```")

                if payload.get('generated_output'):
                    lines.append("\n### Output Generated")
                    output = payload['generated_output']
                    lines.append(f"```\n{output[:1500]}")
                    if len(output) > 1500:
                        lines.append(f"\n... ({len(output) - 1500} more characters)\n```")
                    else:
                        lines.append("```")

            elif event.event_type == 'brief.revised':
                if payload.get('diffs'):
                    lines.append("\n### Changes Made to Brief")
                    for field, changes in payload['diffs'].items():
                        lines.append(f"\n**{field}:**")
                        lines.append(f"- Before: `{changes.get('old')}`")
                        lines.append(f"- After: `{changes.get('new')}`")
                if payload.get('reason'):
                    lines.append(f"\n**Reason:** {payload['reason']}")

            elif event.event_type == 'review.submitted':
                if payload.get('feedback_text'):
                    lines.append(f"\n**Feedback:**\n\n{payload['feedback_text']}")
                if payload.get('decision'):
                    lines.append(f"\n**Decision:** {payload['decision'].upper()}")

            elif event.event_type == 'data.uploaded':
                if payload.get('filename'):
                    lines.append(f"- **File:** {payload['filename']}")
                if payload.get('checksum'):
                    lines.append(f"- **SHA256:** {payload['checksum'][:16]}...")
                if payload.get('category'):
                    lines.append(f"- **Category:** {payload['category']}")

    return "\n".join(lines)


def export_audit_trail_txt(session: Session, engagement_id: int) -> str:
    """Export audit trail as plain-language transcript."""
    events = get_engagement_trail(session, engagement_id)
    lines = ["APProved Audit Trail\n" "=" * 50 + "\n"]

    for event in events:
        timestamp = event.created_at.strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"[{timestamp}] {event.actor_type.upper()}: {event.actor_identity}")
        lines.append(f"  Event: {event.event_type}")

        if event.payload:
            for key, value in event.payload.items():
                # Never print API keys
                if "key" in key.lower() or "token" in key.lower():
                    lines.append(f"    {key}: ****")
                else:
                    lines.append(f"    {key}: {value}")

        lines.append("")

    return "\n".join(lines)
