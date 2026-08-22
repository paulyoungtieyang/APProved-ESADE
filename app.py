#!/usr/bin/env python3
"""
APProved — Python prototype with launchable HTML interface.

Run: python app.py
Then navigate to http://localhost:5000 in your browser.
"""

import os
import sys
import webbrowser
from threading import Timer

from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from sqlalchemy.orm import Session, sessionmaker
from datetime import datetime

from core.models import init_db, Engagement, BriefVersion, UploadedFile
from core.audit import log_event
from core.briefs import create_brief_v1, get_latest_brief, brief_as_dict
from core.gates import consent_gate, data_quality_gate

# Configuration
os.makedirs("storage", exist_ok=True)
os.makedirs("storage/uploads", exist_ok=True)

DATABASE_URL = "sqlite:///storage/approved.db"
engine = init_db(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

# Flask app
app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-change-in-production")
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100MB


def get_db():
    """Get a database session."""
    return SessionLocal()


# ============================================================================
# Client Routes
# ============================================================================


@app.route("/", methods=["GET"])
def index():
    """Landing page — choose Client or User view."""
    return render_template("index.html")


@app.route("/client", methods=["GET"])
def client_index():
    """Client view — list engagements."""
    db = get_db()
    engagements = db.query(Engagement).order_by(Engagement.created_at.desc()).all()
    db.close()
    return render_template("client/index.html", engagements=engagements)


@app.route("/client/new", methods=["GET", "POST"])
def client_new_engagement():
    """Client creates a new engagement."""
    if request.method == "POST":
        client_name = request.form.get("client_name", "").strip()
        if not client_name:
            return render_template("client/new_engagement.html", error="Client name is required")

        db = get_db()
        engagement = Engagement(client_name=client_name)
        db.add(engagement)
        db.commit()
        engagement_id = engagement.id
        db.close()

        log_event(
            db,
            engagement_id=engagement_id,
            event_type="engagement.created",
            actor_type="client",
            actor_identity="client",
            payload={"client_name": client_name},
        )

        return redirect(url_for("client_consent", engagement_id=engagement_id))

    return render_template("client/new_engagement.html")


@app.route("/client/<int:engagement_id>/consent", methods=["GET", "POST"])
def client_consent(engagement_id):
    """Client gives consent for audit logging."""
    db = get_db()
    engagement = db.query(Engagement).get(engagement_id)
    if not engagement:
        db.close()
        return "Engagement not found", 404

    if engagement.consent_given:
        db.close()
        return redirect(url_for("client_upload", engagement_id=engagement_id))

    if request.method == "POST":
        consent_given = request.form.get("consent") == "on"
        result = consent_gate(db, engagement_id, consent_given)

        if not result["allowed"]:
            db.close()
            return render_template(
                "client/consent.html",
                engagement=engagement,
                error="You must consent to audit logging to proceed.",
            )

        db.close()
        return redirect(url_for("client_upload", engagement_id=engagement_id))

    db.close()
    return render_template("client/consent.html", engagement=engagement)


@app.route("/client/<int:engagement_id>/upload", methods=["GET", "POST"])
def client_upload(engagement_id):
    """Client uploads data files."""
    db = get_db()
    engagement = db.query(Engagement).get(engagement_id)
    if not engagement or not engagement.consent_given:
        db.close()
        return redirect(url_for("client_consent", engagement_id=engagement_id))

    uploaded_files = db.query(UploadedFile).filter_by(engagement_id=engagement_id).all()

    if request.method == "POST":
        if "file" not in request.files:
            db.close()
            return render_template(
                "client/upload.html",
                engagement=engagement,
                uploaded_files=uploaded_files,
                error="No file part",
            )

        file = request.files["file"]
        category = request.form.get("category", "").strip()

        if file.filename == "" or not category:
            db.close()
            return render_template(
                "client/upload.html",
                engagement=engagement,
                uploaded_files=uploaded_files,
                error="File and category are required",
            )

        # Save file
        import hashlib

        file_content = file.read()
        sha256_hash = hashlib.sha256(file_content).hexdigest()
        file_path = f"engagement_{engagement_id}_{sha256_hash[:8]}_{file.filename}"
        full_path = os.path.join("storage/uploads", file_path)

        with open(full_path, "wb") as f:
            f.write(file_content)

        # Record in database
        uploaded = UploadedFile(
            engagement_id=engagement_id,
            filename=file.filename,
            file_path=file_path,
            file_size=len(file_content),
            sha256_checksum=sha256_hash,
            category=category,
        )
        db.add(uploaded)
        db.commit()

        log_event(
            db,
            engagement_id=engagement_id,
            event_type="data.uploaded",
            actor_type="client",
            actor_identity="client",
            payload={
                "filename": file.filename,
                "size": len(file_content),
                "checksum": sha256_hash,
                "category": category,
            },
            uploaded_file_id=uploaded.id,
        )

        db.close()
        return redirect(url_for("client_upload", engagement_id=engagement_id))

    db.close()
    return render_template(
        "client/upload.html",
        engagement=engagement,
        uploaded_files=uploaded_files,
        categories=["efficacy", "safety", "demographics", "pharmacokinetic", "quality_of_life"],
    )


@app.route("/client/<int:engagement_id>/specification", methods=["GET", "POST"])
def client_specification(engagement_id):
    """Client specifies deliverable requirements."""
    db = get_db()
    engagement = db.query(Engagement).get(engagement_id)
    if not engagement or not engagement.consent_given:
        db.close()
        return redirect(url_for("client_index"))

    # Check if there are uploaded files
    has_uploads = db.query(UploadedFile).filter_by(engagement_id=engagement_id).count() > 0

    latest_brief = get_latest_brief(db, engagement_id)

    if request.method == "POST":
        deliverable_types = request.form.getlist("deliverable_types")
        therapeutic_area = request.form.get("therapeutic_area", "").strip()
        target_markets = request.form.getlist("target_markets")
        regulatory_frameworks = request.form.getlist("regulatory_frameworks")
        languages = request.form.getlist("languages")
        output_formats = request.form.getlist("output_formats")
        tone = request.form.get("tone", "").strip()
        target_audience = request.form.get("target_audience", "").strip()
        focus_area = request.form.get("focus_area", "").strip()
        key_messages = request.form.get("key_messages", "").strip()
        dossier_sections = request.form.getlist("dossier_sections")
        regional_tender_spec = request.form.get("regional_tender_spec", "").strip()
        additional_requirements = request.form.get("additional_requirements", "").strip()

        if not all([deliverable_types, therapeutic_area, target_markets, tone]):
            db.close()
            return render_template(
                "client/specification.html",
                engagement=engagement,
                error="All required fields must be filled",
                has_uploads=has_uploads,
                latest_brief=latest_brief,
            )

        # Create or amend brief
        if not latest_brief:
            brief = create_brief_v1(
                db,
                engagement_id,
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
        else:
            # TODO: amend brief if needed
            pass

        db.close()
        return redirect(url_for("client_review", engagement_id=engagement_id))

    db.close()
    return render_template(
        "client/specification.html",
        engagement=engagement,
        has_uploads=has_uploads,
        latest_brief=latest_brief,
        therapeutic_areas=["Cardiometabolic", "Oncology", "Immunology", "Neurology", "Diagnostics & Monitoring"],
        markets=["Global (All Regions)", "United States", "European Union", "Japan", "China", "Australia", "Canada"],
        languages=["English", "French", "German", "Japanese", "Chinese"],
        output_formats=["PDF", "Word (DOCX)", "PowerPoint (PPTX)"],
        tones=["Scientific", "Balanced", "Accessible"],
        dossier_sections=[
            "executive-summary",
            "disease-epidemiology",
            "clinical-efficacy",
            "safety-tolerability",
            "pharmacoeconomic-analysis",
            "quality-of-life",
            "comparative-effectiveness",
            "target-population",
        ],
    )


@app.route("/client/<int:engagement_id>/review", methods=["GET"])
def client_review(engagement_id):
    """Client reviews their brief and engagement summary."""
    db = get_db()
    engagement = db.query(Engagement).get(engagement_id)
    if not engagement:
        db.close()
        return "Engagement not found", 404

    latest_brief = get_latest_brief(db, engagement_id)
    uploaded_files = db.query(UploadedFile).filter_by(engagement_id=engagement_id).all()

    brief_data = brief_as_dict(latest_brief) if latest_brief else None

    db.close()
    return render_template(
        "client/review.html",
        engagement=engagement,
        brief=brief_data,
        uploaded_files=uploaded_files,
    )


# ============================================================================
# User Routes
# ============================================================================


@app.route("/user", methods=["GET"])
def user_index():
    """User view — list available engagements."""
    db = get_db()
    # Only show engagements that have given consent and have a brief
    engagements = (
        db.query(Engagement)
        .filter(Engagement.consent_given == True)
        .order_by(Engagement.created_at.desc())
        .all()
    )
    db.close()
    return render_template("user/index.html", engagements=engagements)


@app.route("/user/<int:engagement_id>", methods=["GET"])
def user_context(engagement_id):
    """User views the client's brief and context."""
    db = get_db()
    engagement = db.query(Engagement).get(engagement_id)
    if not engagement or not engagement.consent_given:
        db.close()
        return "Engagement not found", 404

    latest_brief = get_latest_brief(db, engagement_id)
    uploaded_files = db.query(UploadedFile).filter_by(engagement_id=engagement_id).all()

    brief_data = brief_as_dict(latest_brief) if latest_brief else None

    db.close()
    return render_template(
        "user/context.html",
        engagement=engagement,
        brief=brief_data,
        uploaded_files=uploaded_files,
    )


@app.route("/user/<int:engagement_id>/prompt", methods=["GET", "POST"])
def user_prompt(engagement_id):
    """User composes a prompt for generation."""
    db = get_db()
    engagement = db.query(Engagement).get(engagement_id)
    if not engagement:
        db.close()
        return "Engagement not found", 404

    latest_brief = get_latest_brief(db, engagement_id)
    if not latest_brief:
        db.close()
        return "No brief found for this engagement", 404

    brief_data = brief_as_dict(latest_brief)

    if request.method == "POST":
        deliverable_type = request.form.get("deliverable_type", "").strip()
        provider = request.form.get("provider", "anthropic").strip()
        model = request.form.get("model", "claude-opus-5").strip()
        user_overlay = request.form.get("user_overlay", "").strip()

        # For now, just log this. Generation will be wired in the next phase.
        log_event(
            db,
            engagement_id=engagement_id,
            event_type="prompt.composed",
            actor_type="user",
            actor_identity="expert",
            payload={
                "deliverable_type": deliverable_type,
                "provider": provider,
                "model": model,
                "has_user_overlay": bool(user_overlay),
            },
        )

        db.close()
        return jsonify(
            {
                "status": "composed",
                "message": "Prompt composed. Generation will be implemented in the next phase.",
                "deliverable_type": deliverable_type,
            }
        )

    db.close()
    return render_template(
        "user/prompt.html",
        engagement=engagement,
        brief=brief_data,
        deliverable_types=["gvd", "slide_deck", "summary", "faq", "email_templates"],
        providers=["anthropic", "openai", "google"],
        models={
            "anthropic": ["claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5-20251001"],
            "openai": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
            "google": ["gemini-pro", "gemini-1.5-pro"],
        },
    )


# ============================================================================
# Error Handlers
# ============================================================================


@app.errorhandler(404)
def not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(error):
    return render_template("500.html", error=str(error)), 500


# ============================================================================
# Launch
# ============================================================================


def open_browser():
    """Open the browser after a short delay."""
    webbrowser.open("http://localhost:5000")


if __name__ == "__main__":
    # Open browser after 1 second
    timer = Timer(1.0, open_browser)
    timer.daemon = True
    timer.start()

    print("\n" + "=" * 60)
    print("APProved — Python Prototype")
    print("=" * 60)
    print("Server running at http://localhost:5000")
    print("Press Ctrl+C to stop\n")

    app.run(debug=True, use_reloader=False)
