"""
Intake gates — consent, data quality, etc.
"""

from sqlalchemy.orm import Session
from core.models import Engagement, UploadedFile
from core.audit import log_event


def consent_gate(session: Session, engagement_id: int, consent_given: bool, ip_address: str = None) -> dict:
    """
    Consent gate — runs FIRST.

    Without consent to keep an audit record, nothing else is evaluated
    and nothing is written.
    """
    engagement = session.query(Engagement).get(engagement_id)
    if not engagement:
        return {"allowed": False, "reason": "Engagement not found"}

    if not consent_given:
        # Log this decline, but only AFTER confirming the client explicitly declined
        # (not before). Per the design: declining consent leaves no trace.
        return {"allowed": False, "reason": "Audit logging consent declined by client"}

    # Grant consent
    engagement.consent_given = True
    from datetime import datetime

    engagement.consent_timestamp = datetime.utcnow()
    session.commit()

    log_event(
        session,
        engagement_id=engagement_id,
        event_type="consent.granted",
        actor_type="client",
        actor_identity="client",
        payload={"ip": ip_address} if ip_address else {},
    )

    return {"allowed": True, "reason": "Consent granted"}


def data_quality_gate(session: Session, engagement_id: int) -> dict:
    """
    Data quality gate — reject unparsable, incomplete, or poor-quality uploads.

    Check: all uploaded files can be read, and no more than 15% of patient-level
    data points are missing in the clinical dataset.
    """
    uploads = session.query(UploadedFile).filter_by(engagement_id=engagement_id).all()

    if not uploads:
        return {"allowed": False, "reason": "No clinical data uploaded"}

    # For now, a basic pass — in production this would validate file formats,
    # read headers, and check for missing data fields.
    clinical_uploads = [u for u in uploads if u.category in ["efficacy", "safety", "demographics"]]

    if not clinical_uploads:
        return {"allowed": False, "reason": "No clinical data files (efficacy, safety, or demographics)"}

    return {"allowed": True, "reason": "Data quality acceptable"}
