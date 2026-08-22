"""
SQLAlchemy models for APProved.

Entities: engagement, brief_version, uploaded_file, generation_run,
review_round, audit_event.

The audit_event table is append-only — no updates, no deletes.
"""

from datetime import datetime
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    Float,
    ForeignKey,
    JSON,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Engagement(Base):
    """A client engagement — one project."""

    __tablename__ = "engagement"

    id = Column(Integer, primary_key=True)
    client_name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    consent_given = Column(Boolean, default=False)
    consent_timestamp = Column(DateTime, nullable=True)

    brief_versions = relationship("BriefVersion", back_populates="engagement", cascade="all, delete-orphan")
    uploaded_files = relationship("UploadedFile", back_populates="engagement", cascade="all, delete-orphan")
    generation_runs = relationship("GenerationRun", back_populates="engagement", cascade="all, delete-orphan")
    review_rounds = relationship("ReviewRound", back_populates="engagement", cascade="all, delete-orphan")
    audit_events = relationship("AuditEvent", back_populates="engagement", cascade="all, delete-orphan")


class BriefVersion(Base):
    """An immutable specification brief — versioned."""

    __tablename__ = "brief_version"

    id = Column(Integer, primary_key=True)
    engagement_id = Column(Integer, ForeignKey("engagement.id"), nullable=False)
    version = Column(Integer, nullable=False)  # v1, v2, ...
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(255), default="client", nullable=False)  # "client" or username

    # Specification fields
    deliverable_types = Column(JSON, nullable=False)  # ["gvd", "slide_deck", "summary"]
    therapeutic_area = Column(String(255), nullable=False)
    target_markets = Column(JSON, nullable=False)  # ["EU", "US", "JP"]
    regulatory_frameworks = Column(JSON, nullable=False)  # ["EMA", "FDA"]
    languages = Column(JSON, nullable=False)  # ["English", "French"]
    output_formats = Column(JSON, nullable=False)  # ["PDF", "DOCX"]
    tone = Column(String(50), nullable=False)  # Scientific, Balanced, Accessible
    target_audience = Column(String(255), nullable=True)  # Payers, HCPs, etc.
    focus_area = Column(String(255), nullable=True)
    key_messages = Column(Text, nullable=True)
    dossier_sections = Column(JSON, nullable=True)  # for GVD
    regional_tender_spec = Column(Text, nullable=True)
    additional_requirements = Column(Text, nullable=True)

    # Change tracking
    previous_version_id = Column(Integer, ForeignKey("brief_version.id"), nullable=True)
    change_reason = Column(Text, nullable=True)  # why client changed brief
    field_diffs = Column(JSON, nullable=True)  # {"tone": {"old": "Scientific", "new": "Balanced"}}

    engagement = relationship("Engagement", back_populates="brief_versions")
    generation_runs = relationship("GenerationRun", back_populates="brief_version")


class UploadedFile(Base):
    """A file uploaded by the client."""

    __tablename__ = "uploaded_file"

    id = Column(Integer, primary_key=True)
    engagement_id = Column(Integer, ForeignKey("engagement.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)  # relative to storage/uploads/
    file_size = Column(Integer, nullable=False)  # bytes
    sha256_checksum = Column(String(64), nullable=False)  # hex digest
    category = Column(String(100), nullable=False)  # efficacy, safety, demographics, etc.
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    uploaded_by = Column(String(255), default="client", nullable=False)

    engagement = relationship("Engagement", back_populates="uploaded_files")


class GenerationRun(Base):
    """One generation invocation by the user."""

    __tablename__ = "generation_run"

    id = Column(Integer, primary_key=True)
    engagement_id = Column(Integer, ForeignKey("engagement.id"), nullable=False)
    brief_version_id = Column(Integer, ForeignKey("brief_version.id"), nullable=False)
    round_number = Column(Integer, nullable=False)  # which refinement round
    deliverable_type = Column(String(50), nullable=False)  # gvd, slide_deck, summary, etc.

    # Prompt composition
    resolved_prompt = Column(Text, nullable=False)  # exact text sent to model
    prompt_provenance = Column(
        JSON, nullable=False
    )  # {"line 1-3": "client", "line 4-8": "template", "line 9-15": "user"}

    # Model and provider
    provider = Column(String(50), nullable=False)  # anthropic, openai, google
    model = Column(String(100), nullable=False)  # claude-opus-5, gpt-4o, etc.
    max_tokens = Column(Integer, nullable=True)
    temperature = Column(Float, nullable=True)

    # Output
    generated_output = Column(Text, nullable=True)  # markdown or text
    output_hash = Column(String(64), nullable=True)  # SHA256 of output
    status = Column(String(50), default="pending", nullable=False)  # pending, completed, failed
    error_message = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Judge scoring (before human review)
    judge_score = Column(Float, nullable=True)  # 0-1
    judge_rubric = Column(JSON, nullable=True)  # {"evidence_cited": True, "comparator_named": False, ...}
    flagged_for_redraft = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(255), nullable=False)  # user who triggered generation

    engagement = relationship("Engagement", back_populates="generation_runs")
    brief_version = relationship("BriefVersion", back_populates="generation_runs")
    review_rounds = relationship("ReviewRound", back_populates="generation_run")


class ReviewRound(Base):
    """Human review of a generated draft."""

    __tablename__ = "review_round"

    id = Column(Integer, primary_key=True)
    engagement_id = Column(Integer, ForeignKey("engagement.id"), nullable=False)
    generation_run_id = Column(Integer, ForeignKey("generation_run.id"), nullable=False)
    round_type = Column(String(50), nullable=False)  # internal_expert or client
    reviewed_by = Column(String(255), nullable=False)  # username or "client"

    feedback_text = Column(Text, nullable=True)
    decision = Column(String(50), nullable=False)  # accept, revise, decline, amend_brief
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    engagement = relationship("Engagement", back_populates="review_rounds")
    generation_run = relationship("GenerationRun", back_populates="review_rounds")


class AuditEvent(Base):
    """Append-only audit trail event."""

    __tablename__ = "audit_event"
    __table_args__ = (Index("ix_engagement_timestamp", "engagement_id", "created_at"),)

    id = Column(Integer, primary_key=True)
    engagement_id = Column(Integer, ForeignKey("engagement.id"), nullable=False)
    event_type = Column(String(100), nullable=False)
    # consent.granted, consent.declined, data.uploaded, brief.submitted, brief.revised,
    # prompt.composed, generation.requested, generation.completed, expert_review.submitted, etc.

    actor_type = Column(String(50), nullable=False)  # client, user, system
    actor_identity = Column(String(255), nullable=False)  # username or "system"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Entity references
    brief_version_id = Column(Integer, nullable=True)
    uploaded_file_id = Column(Integer, nullable=True)
    generation_run_id = Column(Integer, nullable=True)
    review_round_id = Column(Integer, nullable=True)

    # Payload — event-specific data, JSON for flexibility
    payload = Column(JSON, nullable=True)
    # For consent.granted: {"timestamp": "...", "ip": "..."}
    # For data.uploaded: {"filename": "...", "checksum": "...", "category": "..."}
    # For generation.requested: {"resolved_prompt": "...", "provider": "...", "model": "..."}
    # API keys are NEVER stored here

    engagement = relationship("Engagement", back_populates="audit_events")


def init_db(db_url: str):
    """Create all tables."""
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    return engine
