#!/usr/bin/env python3
"""
APProved — medical writing platform prototype.

    python3 app.py      →  http://localhost:5001

A Flask port of the APProved Figma prototype: a landing page that routes into one
of two completely separate workspaces —

  - the TOOL:  a blank engagement, for real use, with nothing pre-loaded, or
  - the DEMO:  a pre-loaded continuous glucose monitoring (CGM) engagement,
               EU MDR / Spain launch track, for exploring what the tool produces.

The two are never mixed: each keeps its own engagement (and therefore its own
uploads, brief and generated documents) behind its own session key, so entering
one never shows data from the other.

Runs entirely offline. Supplying an API key on the generation pages switches the
same prompts over to a live Anthropic / OpenAI / Google model.
"""

from __future__ import annotations

import io
import json
import os
import shutil
from datetime import datetime
from threading import Timer
from werkzeug.utils import secure_filename

from flask import (
    Flask, flash, jsonify, redirect, render_template, request, send_file, session, url_for
)
from sqlalchemy.orm import sessionmaker

from core import audit, content, dataset, deck, llm
from core.audit import log_event, get_engagement_trail
from core.briefs import brief_as_dict, create_brief_v1, get_latest_brief
from core.gates import consent_gate
from core.models import (
    AuditEvent, BriefVersion, Engagement, GenerationRun, UploadedFile, init_db
)

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
UPLOAD_DIR = os.path.join(STORAGE_DIR, "uploads")
SAMPLE_DIR = os.path.join(BASE_DIR, "sample_data")

os.makedirs(UPLOAD_DIR, exist_ok=True)

engine = init_db(f"sqlite:///{os.path.join(STORAGE_DIR, 'approved.db')}")
SessionLocal = sessionmaker(bind=engine)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB per the upload page copy

DEMO_CLIENT_NAME = "ContinuousGlucose Monitoring Ltd."

# Source material the client hands over. The two bolus-calculator files are the
# device's own software documentation — the digital function is something the
# client documents and APProved writes up, never a feature of this platform.
SAMPLE_FILES = [
    ("cgm_pivotal_study.csv", "clinical"),
    ("safety_adverse_events.csv", "safety"),
    ("efficacy_analysis.csv", "efficacy"),
    ("bolus_calculator_spec.csv", "software"),
    ("bolus_calculator_verification.csv", "verification"),
]

# The demo ships a stand-in corporate deck template so the "generate a branded
# slide deck" path is exercised end to end without the user having to find one.
SAMPLE_BRAND_TEMPLATE = os.path.join("brand", "acme_medical_corporate_template.pptx")

# Routes reachable before a workspace has been chosen. Everything else redirects
# to the landing page until the visitor picks "the tool" or "the demo" — see
# require_workspace() below.
PUBLIC_ENDPOINTS = {"landing", "enter_tool", "enter_demo", "static"}

# Every item here is APProved functionality. Client device features — the demo
# device's bolus calculator, for instance — are never pages in this app; they are
# things the client documents, and they arrive as uploaded source material.
NAV_ITEMS = [
    {"section": "Workspace"},
    {"name": "Dashboard", "endpoint": "dashboard", "icon": "file-text"},
    {"name": "Upload Clinical Data", "endpoint": "upload", "icon": "upload"},
    {"name": "Regulations", "endpoint": "regulations", "icon": "scale"},
    {"name": "Policy News", "endpoint": "policy_news", "icon": "newspaper"},
    {"section": "Generate"},
    {"name": "Global Value Dossier", "endpoint": "global_dossier", "icon": "file-stack"},
    {"name": "MSL Materials", "endpoint": "msl_material", "icon": "message-square"},
    {"section": "Deliver"},
    {"name": "Document Library", "endpoint": "documents", "icon": "folder-open"},
    {"name": "Resources", "endpoint": "resources", "icon": "book-open"},
    {"name": "Submit", "endpoint": "submission", "icon": "send"},
    {"section": "Governance"},
    {"name": "Audit Trail", "endpoint": "audit_trail", "icon": "history"},
    {"name": "Settings", "endpoint": "settings", "icon": "settings"},
]


# --------------------------------------------------------------------------
# Session / engagement helpers
# --------------------------------------------------------------------------


def get_db():
    return SessionLocal()


def current_role() -> str:
    return session.get("role", "admin")


def can(permission: str) -> bool:
    """Permission check against the role matrix stored in the session."""
    roles = session.get("roles") or content.DEFAULT_ROLES
    role_id = current_role()
    for role in roles:
        if role["id"] == role_id:
            return bool(role["permissions"].get(permission))
    return False


def seed_demo_engagement(db) -> int:
    """Create the CGM / MDR / Spain demo engagement with its sample dataset."""
    engagement = Engagement(
        client_name=DEMO_CLIENT_NAME,
        consent_given=True,
        consent_timestamp=datetime.utcnow(),
    )
    db.add(engagement)
    db.commit()
    engagement_id = engagement.id

    log_event(db, engagement_id, "consent.granted", "client", "demo",
              {"scope": "audit logging and AI generation"})

    for filename, category in SAMPLE_FILES + [(SAMPLE_BRAND_TEMPLATE, "brand")]:
        source = os.path.join(SAMPLE_DIR, filename)
        if not os.path.exists(source):
            continue
        basename = os.path.basename(filename)
        stored_name = f"{engagement_id}_{basename}"
        destination = os.path.join(UPLOAD_DIR, stored_name)
        shutil.copyfile(source, destination)

        record = UploadedFile(
            engagement_id=engagement_id,
            filename=basename,
            file_path=stored_name,
            file_size=os.path.getsize(destination),
            sha256_checksum=dataset.checksum(destination),
            category=category,
            uploaded_by="demo",
        )
        db.add(record)
        db.commit()
        log_event(db, engagement_id,
                  "brand_template.uploaded" if category == "brand" else "data.uploaded",
                  "client", "demo",
                  {"filename": basename, "category": category,
                   "checksum": record.sha256_checksum},
                  uploaded_file_id=record.id)

    create_brief_v1(
        db,
        engagement_id=engagement_id,
        deliverable_types=["gvd", "slide_deck", "summary"],
        therapeutic_area="Diabetes — Continuous Glucose Monitoring (Class IIb device)",
        target_markets=["Spain", "European Union"],
        regulatory_frameworks=["MDR", "AEMPS"],
        languages=["Spanish (Castellano)", "English"],
        output_formats=["PDF", "DOCX"],
        tone="Scientific",
        target_audience="Endocrinologists, regional payers and notified body reviewers",
        focus_area="Clinical performance, safety and market access",
        key_messages=(
            "MARD below 10% meets the primary accuracy endpoint. Superior nocturnal "
            "hypoglycaemia detection. Integrated bolus calculator removes the need for a "
            "separate dosing app. CE marking under MDR 2017/745 with Spanish market entry "
            "through AEMPS."
        ),
        dossier_sections=[section["id"] for section in content.DOSSIER_SECTIONS],
        regional_tender_spec=(
            "Spanish CCAA tender criteria weight time-in-range improvement and nocturnal "
            "hypoglycaemia reduction. Target launch Q2 2026."
        ),
        additional_requirements=(
            "Focus on Spain market entry under MDR. Document the bolus calculator as an "
            "IEC 62304 software component. Label all comparative statements as indirect."
        ),
    )
    # create_brief_v1 writes its own brief.submitted event — no second one here.
    return engagement_id


def seed_blank_engagement(db, client_name: str) -> int:
    """
    Create an empty engagement for the real tool — no sample files, no pre-filled
    brief content. This is what "Open the Tool" from the landing page starts from,
    kept deliberately separate from the CGM demo engagement.
    """
    engagement = Engagement(
        client_name=client_name or "New Engagement",
        consent_given=False,
    )
    db.add(engagement)
    db.commit()
    engagement_id = engagement.id

    consent_gate(db, engagement_id, consent_given=True)

    create_brief_v1(
        db,
        engagement_id=engagement_id,
        deliverable_types=[],
        therapeutic_area="",
        target_markets=[],
        regulatory_frameworks=[],
        languages=[],
        output_formats=[],
        tone="Scientific",
    )
    return engagement_id


def active_engagement_id(db) -> int:
    """
    The engagement bound to this browser session — scoped to the active workspace
    (tool or demo) so the two never share data. Each mode gets its own session key,
    so switching between them mid-session preserves both rather than clobbering one.
    """
    mode = session.get("workspace_mode", "tool")
    session_key = f"engagement_id_{mode}"

    engagement_id = session.get(session_key)
    if engagement_id and db.get(Engagement, engagement_id):
        return engagement_id

    if mode == "demo":
        existing = (
            db.query(Engagement)
            .filter(Engagement.client_name == DEMO_CLIENT_NAME)
            .order_by(Engagement.created_at.desc())
            .first()
        )
        engagement_id = existing.id if existing else seed_demo_engagement(db)
    else:
        engagement_id = seed_blank_engagement(db, session.get("workspace_client_name"))

    session[session_key] = engagement_id
    return engagement_id


@app.before_request
def require_workspace():
    """Force every page except the landing/entry routes through a chosen workspace."""
    if request.endpoint in PUBLIC_ENDPOINTS or request.endpoint is None:
        return None
    if not session.get("workspace_mode"):
        return redirect(url_for("landing"))
    return None


def engagement_context(db) -> tuple[int, dict, dict]:
    """(engagement_id, brief dict, dataset statistics) — the trio most pages need."""
    engagement_id = active_engagement_id(db)
    brief = get_latest_brief(db, engagement_id)
    brief_data = brief_as_dict(brief) if brief else {}
    return engagement_id, brief_data, dataset_stats(db, engagement_id)


def dataset_stats(db, engagement_id: int) -> dict:
    """Read every uploaded tabular file and derive the figures the drafts cite."""
    files = db.query(UploadedFile).filter_by(engagement_id=engagement_id).all()
    stats: dict = {"study": {}, "safety": {}, "efficacy": {},
                   "software": {}, "verification": {}, "files": []}

    for record in files:
        path = os.path.join(UPLOAD_DIR, record.file_path)
        entry = {
            "id": record.id,
            "filename": record.filename,
            "category": record.category,
            "size": record.file_size,
            "checksum": record.sha256_checksum,
            "uploaded_at": record.uploaded_at,
            "rows": 0,
            "columns": [],
            "error": None,
            "note": None,
        }

        if record.category == "brand":
            # Brand assets carry no clinical data — describe the template instead of
            # reporting "0 rows", which reads like a parse failure.
            info = deck.inspect_template(path) if os.path.exists(path) else {}
            entry["error"] = info.get("error") if os.path.exists(path) else "File missing from storage"
            entry["note"] = (
                f"{info.get('layout_count')} layouts · {info.get('aspect_ratio')}"
                if not entry["error"] else None
            )
        elif os.path.exists(path) and dataset.is_tabular(record.filename):
            table = dataset.read_table(path)
            entry["rows"] = table["row_count"]
            entry["columns"] = table["columns"]
            entry["error"] = table["error"]

            columns = set(table["columns"])
            # Order matters: the software files also carry a Parameter/Metric-ish
            # shape, so match their distinctive columns before the clinical ones.
            if "Test_ID" in columns:
                stats["verification"] = dataset.summarise_verification(table["rows"])
            elif "Requirement_ID" in columns or "Parameter" in columns:
                stats["software"] = dataset.summarise_software_spec(table["rows"])
            elif {"MARD", "Patient_ID"} & columns and "Event_Type" not in columns:
                stats["study"] = dataset.summarise_study(table["rows"])
            elif "Event_Type" in columns:
                stats["safety"] = dataset.summarise_safety(table["rows"])
            elif "Metric" in columns:
                stats["efficacy"] = dataset.summarise_efficacy(table["rows"])
        elif not os.path.exists(path):
            entry["error"] = "File missing from storage"

        stats["files"].append(entry)

    return stats


def brand_templates(db, engagement_id: int) -> list[dict]:
    """
    Uploaded PowerPoint templates available to format generated slide decks.

    Each entry carries what python-pptx could read out of the file (layouts,
    aspect ratio, theme fonts) so the picker can show the user what they
    actually uploaded rather than just a filename.
    """
    records = (
        db.query(UploadedFile)
        .filter_by(engagement_id=engagement_id, category="brand")
        .order_by(UploadedFile.uploaded_at.desc())
        .all()
    )

    templates = []
    for record in records:
        if not deck.is_template(record.filename):
            continue
        path = os.path.join(UPLOAD_DIR, record.file_path)
        info = deck.inspect_template(path) if os.path.exists(path) else {"error": "File missing"}
        templates.append({
            "id": record.id,
            "filename": record.filename,
            "size": record.file_size,
            "path": path,
            "uploaded_at": record.uploaded_at,
            **info,
        })
    return templates


def file_size_label(num_bytes: int) -> str:
    size = float(num_bytes or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def markdown_to_html(text: str) -> str:
    """
    Minimal Markdown renderer — enough for the drafts this app produces.

    Source text is hard-wrapped, so a bullet or paragraph often spans several
    lines. Continuation lines are folded into the block they belong to; rendering
    each source line independently would scatter stray <p> fragments between the
    list items.
    """
    from markupsafe import escape

    html: list[str] = []
    in_list = False
    buffer: list[str] = []
    kind: str | None = None          # "p" | "li" | "quote"

    def inline(raw: str) -> str:
        safe = str(escape(raw))
        while safe.count("**") >= 2:
            safe = safe.replace("**", "<strong>", 1).replace("**", "</strong>", 1)
        while safe.count("`") >= 2:
            safe = safe.replace("`", "<code>", 1).replace("`", "</code>", 1)
        return safe

    def flush():
        nonlocal buffer, kind
        if not buffer:
            return
        body = inline(" ".join(buffer))
        if kind == "li":
            html.append(f"<li>{body}</li>")
        elif kind == "quote":
            html.append(f'<p class="text-muted"><em>{body}</em></p>')
        else:
            html.append(f"<p>{body}</p>")
        buffer, kind = [], None

    def close_list():
        nonlocal in_list
        flush()
        if in_list:
            html.append("</ul>")
            in_list = False

    for raw in (text or "").split("\n"):
        stripped = raw.strip()

        if not stripped:
            close_list()
            continue

        if stripped.startswith("---"):
            close_list()
            html.append("<hr>")
            continue

        if stripped.startswith("#"):
            close_list()
            level = min(len(stripped) - len(stripped.lstrip("#")), 4)
            html.append(f"<h{level}>{inline(stripped.lstrip('#').strip())}</h{level}>")
            continue

        if stripped.startswith(("- ", "* ", "• ")):
            flush()
            if not in_list:
                html.append("<ul>")
                in_list = True
            buffer, kind = [stripped[2:].strip()], "li"
            continue

        if stripped.startswith("> "):
            close_list()
            buffer, kind = [stripped[2:].strip()], "quote"
            continue

        # A continuation of whatever block is open, or the start of a paragraph.
        if kind:
            buffer.append(stripped)
        else:
            close_list()
            buffer, kind = [stripped], "p"

    close_list()
    return "\n".join(html)


@app.context_processor
def inject_globals():
    return {
        "nav_items": NAV_ITEMS,
        "current_role": current_role(),
        "current_role_label": content.ROLE_LABELS.get(current_role(), "Administrator"),
        "can": can,
        "file_size_label": file_size_label,
        "workspace_mode": session.get("workspace_mode"),
        "workspace_client_name": session.get("workspace_client_name"),
    }


app.jinja_env.filters["markdown"] = markdown_to_html


# --------------------------------------------------------------------------
# Landing page — chooses between the tool and the demo, never both at once
# --------------------------------------------------------------------------


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/enter/tool", methods=["GET", "POST"])
def enter_tool():
    """Start (or resume) a blank, real engagement — no CGM sample data involved."""
    if request.method == "POST":
        session["workspace_mode"] = "tool"
        session["workspace_client_name"] = (request.form.get("client_name") or "").strip() or "New Engagement"
        session.pop("engagement_id_tool", None)  # fresh engagement, not the last blank one
        session.pop("wizard", None)
        return redirect(url_for("dashboard"))
    return render_template("enter_tool.html")


@app.route("/enter/demo", methods=["POST"])
def enter_demo():
    """Enter the pre-loaded CGM / MDR / Spain demo engagement."""
    session["workspace_mode"] = "demo"
    session["workspace_client_name"] = DEMO_CLIENT_NAME
    session.pop("wizard", None)
    return redirect(url_for("dashboard"))


@app.route("/switch-workspace", methods=["POST"])
def switch_workspace():
    """Leave the current workspace and go back to the landing page to choose again."""
    session.pop("workspace_mode", None)
    session.pop("workspace_client_name", None)
    return redirect(url_for("landing"))


# --------------------------------------------------------------------------
# Dashboard
# --------------------------------------------------------------------------


@app.route("/dashboard")
def dashboard():
    db = get_db()
    try:
        engagement_id, brief, stats = engagement_context(db)
        engagement = db.get(Engagement, engagement_id)

        runs = (
            db.query(GenerationRun)
            .filter_by(engagement_id=engagement_id)
            .order_by(GenerationRun.created_at.desc())
            .all()
        )
        events = (
            db.query(AuditEvent)
            .filter_by(engagement_id=engagement_id)
            .order_by(AuditEvent.created_at.desc())
            .limit(6)
            .all()
        )

        dossier_runs = [run for run in runs if run.deliverable_type == "gvd"]
        completed_sections = {run.resolved_prompt.split("::")[0] for run in dossier_runs}

        checklist = {
            "classification": bool(brief.get("therapeutic_area")),
            "upload": bool(stats["files"]),
            "regulations": bool(brief.get("regulatory_frameworks")),
            "dossier": len(dossier_runs) > 0,
            "msl": any(run.deliverable_type != "gvd" for run in runs),
        }

        activity = [{
            "title": event.event_type.replace(".", " · ").replace("_", " ").title(),
            "actor": event.actor_identity,
            "date": event.created_at,
            "status": "Completed",
        } for event in events]

        return render_template(
            "dashboard.html",
            engagement=engagement.client_name,
            brief=brief,
            stats=stats,
            documents_generated=len(runs),
            sections_done=len(completed_sections),
            total_sections=len(content.DOSSIER_SECTIONS),
            checklist=checklist,
            onboarding_steps=content.ONBOARDING_STEPS,
            activity=activity,
            regulatory_track=session.get("regulatory_track", "global"),
        )
    finally:
        db.close()


@app.route("/regulatory-track", methods=["POST"])
def regulatory_track():
    session["regulatory_track"] = request.form.get("track", "global")
    return redirect(url_for("dashboard"))


@app.route("/switch-role", methods=["POST"])
def switch_role():
    order = [role["id"] for role in content.DEFAULT_ROLES]
    index = order.index(current_role()) if current_role() in order else 0
    session["role"] = order[(index + 1) % len(order)]
    return redirect(request.form.get("next") or url_for("dashboard"))


@app.route("/demo/reset", methods=["POST"])
def reset_demo():
    """Rebuild the demo engagement from the sample data, discarding generated work."""
    if session.get("workspace_mode") != "demo":
        return redirect(url_for("dashboard"))
    db = get_db()
    try:
        engagement_id = session.get("engagement_id_demo")
        if engagement_id:
            engagement = db.get(Engagement, engagement_id)
            if engagement:
                db.delete(engagement)
                db.commit()
        session.pop("engagement_id_demo", None)
        session.pop("wizard", None)
        session["engagement_id_demo"] = seed_demo_engagement(db)
        flash("Demo reset — sample CGM dataset and brief reloaded.", "success")
        return redirect(url_for("dashboard"))
    finally:
        db.close()


@app.route("/tool/new", methods=["POST"])
def new_tool_engagement():
    """Discard the current blank engagement and start a fresh one for the tool."""
    if session.get("workspace_mode") != "tool":
        return redirect(url_for("dashboard"))
    db = get_db()
    try:
        engagement_id = session.get("engagement_id_tool")
        if engagement_id:
            engagement = db.get(Engagement, engagement_id)
            if engagement:
                db.delete(engagement)
                db.commit()
        session.pop("engagement_id_tool", None)
        session.pop("wizard", None)
        return redirect(url_for("enter_tool"))
    finally:
        db.close()


# --------------------------------------------------------------------------
# Upload
# --------------------------------------------------------------------------


@app.route("/upload", methods=["GET", "POST"])
def upload():
    db = get_db()
    try:
        engagement_id, brief, stats = engagement_context(db)

        if request.method == "POST":
            if not can("upload_data"):
                flash(f"{content.ROLE_LABELS[current_role()]} cannot upload clinical data.", "error")
                return redirect(url_for("upload"))

            uploads = request.files.getlist("files")
            accepted, rejected = 0, []

            for upload_file in uploads:
                if not upload_file or not upload_file.filename:
                    continue
                original = upload_file.filename
                if not dataset.is_allowed(original):
                    rejected.append(f"{original} (unsupported type)")
                    continue

                safe_name = secure_filename(original)
                stored_name = f"{engagement_id}_{int(datetime.utcnow().timestamp())}_{safe_name}"
                destination = os.path.join(UPLOAD_DIR, stored_name)
                upload_file.save(destination)

                table = dataset.read_table(destination) if dataset.is_tabular(original) else {"columns": []}
                record = UploadedFile(
                    engagement_id=engagement_id,
                    filename=original,
                    file_path=stored_name,
                    file_size=os.path.getsize(destination),
                    sha256_checksum=dataset.checksum(destination),
                    category=request.form.get("category")
                             or dataset.classify(original, table.get("columns", [])),
                    uploaded_by=current_role(),
                )
                db.add(record)
                db.commit()
                log_event(db, engagement_id, "data.uploaded", "client", current_role(),
                          {"filename": original, "category": record.category,
                           "checksum": record.sha256_checksum, "bytes": record.file_size},
                          uploaded_file_id=record.id)
                accepted += 1

            if accepted:
                flash(f"{accepted} file(s) uploaded and checksummed.", "success")
            for note in rejected:
                flash(f"Rejected {note}", "error")
            return redirect(url_for("upload"))

        return render_template("upload.html", brief=brief, stats=stats)
    finally:
        db.close()


@app.route("/upload/<int:file_id>/delete", methods=["POST"])
def delete_upload(file_id):
    db = get_db()
    try:
        engagement_id = active_engagement_id(db)
        record = db.get(UploadedFile, file_id)
        if record and record.engagement_id == engagement_id:
            if not can("upload_data"):
                flash("Your role cannot remove uploaded data.", "error")
                return redirect(url_for("upload"))
            path = os.path.join(UPLOAD_DIR, record.file_path)
            if os.path.exists(path):
                os.remove(path)
            log_event(db, engagement_id, "data.removed", "client", current_role(),
                      {"filename": record.filename})
            db.delete(record)
            db.commit()
            flash(f"Removed {record.filename}.", "success")
        return redirect(url_for("upload"))
    finally:
        db.close()


# --------------------------------------------------------------------------
# Regulations / policy news / resources
# --------------------------------------------------------------------------


@app.route("/regulations", methods=["GET", "POST"])
def regulations():
    db = get_db()
    try:
        engagement_id, brief, _ = engagement_context(db)

        if request.method == "POST":
            selected = request.form.getlist("regulations")
            latest = get_latest_brief(db, engagement_id)
            if latest:
                latest.regulatory_frameworks = [
                    content.REGULATION_BY_ID[key]["id"].upper()
                    for key in selected if key in content.REGULATION_BY_ID
                ] or ["MDR"]
                db.commit()
                log_event(db, engagement_id, "brief.revised", "user", current_role(),
                          {"field": "regulatory_frameworks", "new": latest.regulatory_frameworks},
                          brief_version_id=latest.id)
            flash(f"{len(selected)} regulatory framework(s) saved to the brief.", "success")
            return redirect(url_for("regulations"))

        selected_ids = {value.lower() for value in (brief.get("regulatory_frameworks") or [])}
        grouped: dict[str, list] = {}
        for regulation in content.REGULATIONS:
            grouped.setdefault(regulation["region"], []).append(regulation)

        return render_template(
            "regulations.html",
            grouped=grouped,
            selected_ids=selected_ids,
            selected_count=len(selected_ids),
        )
    finally:
        db.close()


@app.route("/policy-news")
def policy_news():
    category = request.args.get("category", "All")
    items = content.POLICY_NEWS
    if category != "All":
        items = [item for item in items if item["category"] == category]
    return render_template(
        "policy_news.html",
        items=items,
        categories=content.NEWS_CATEGORIES,
        selected_category=category,
    )


@app.route("/resources")
def resources():
    resource_type = request.args.get("type", "All")
    items = content.RESOURCES
    if resource_type != "All":
        items = [item for item in items if item["type"] == resource_type]
    return render_template(
        "resources.html",
        items=items,
        types=content.RESOURCE_TYPES,
        selected_type=resource_type,
    )


# --------------------------------------------------------------------------
# Global Value Dossier
# --------------------------------------------------------------------------


@app.route("/global-dossier")
def global_dossier():
    db = get_db()
    try:
        engagement_id, brief, stats = engagement_context(db)

        runs = (
            db.query(GenerationRun)
            .filter_by(engagement_id=engagement_id, deliverable_type="gvd")
            .order_by(GenerationRun.created_at.asc())
            .all()
        )
        generated = {run.resolved_prompt.split("::")[0]: {
            "id": run.id, "provider": run.provider, "model": run.model,
            "offline": run.provider == "offline",
        } for run in runs}

        return render_template(
            "global_dossier.html",
            brief=brief,
            stats=stats,
            sections=content.DOSSIER_SECTIONS,
            generated=generated,
            providers=llm.PROVIDERS,
            markets=content.MARKETS,
            languages=content.LANGUAGES,
            completed_count=len(generated),
        )
    finally:
        db.close()


@app.route("/api/dossier/section", methods=["POST"])
def api_generate_section():
    """Generate one dossier section — drives the progressive UI on the dossier page."""
    payload = request.get_json(silent=True) or {}
    section_id = payload.get("section_id", "")
    if section_id not in content.SECTION_BY_ID:
        return jsonify({"error": "Unknown section"}), 400

    if not can("edit_documents"):
        return jsonify({"error": f"{content.ROLE_LABELS[current_role()]} cannot generate documents."}), 403

    db = get_db()
    try:
        engagement_id, brief, stats = engagement_context(db)
        latest_brief = get_latest_brief(db, engagement_id)

        overlay = (payload.get("overlay") or "").strip()
        provider = payload.get("provider", "offline")
        model = payload.get("model") or llm.PROVIDERS.get(provider, {}).get("models", ["offline"])[0]
        api_key = payload.get("api_key") or ""

        prompt = content.build_section_prompt(section_id, brief, stats, overlay)
        offline_draft = content.draft_section(section_id, brief, stats, overlay)
        result = llm.generate(prompt, offline_draft, provider, model, api_key)

        existing = (
            db.query(GenerationRun)
            .filter_by(engagement_id=engagement_id, deliverable_type="gvd")
            .filter(GenerationRun.resolved_prompt.like(f"{section_id}::%"))
            .first()
        )
        round_number = (existing.round_number + 1) if existing else 1

        run = GenerationRun(
            engagement_id=engagement_id,
            brief_version_id=latest_brief.id,
            round_number=round_number,
            deliverable_type="gvd",
            resolved_prompt=f"{section_id}::{prompt}",
            prompt_provenance={"client": "layer-1", "template": "layer-2",
                               "expert": "layer-3" if overlay else None},
            provider=result.provider,
            model=result.model,
            generated_output=result.text,
            status="completed",
            completed_at=datetime.utcnow(),
            created_by=current_role(),
        )
        if existing:
            db.delete(existing)
        db.add(run)
        db.commit()

        log_event(db, engagement_id, "generation.completed", "user", current_role(),
                  {"section": section_id, "deliverable": "gvd", "provider": result.provider,
                   "model": result.model, "offline": result.offline,
                   "expert_overlay": overlay or None,
                   "resolved_prompt": prompt,
                   "prompt_provenance": {"client": "layer-1", "template": "layer-2",
                                        "expert": "layer-3" if overlay else None},
                   "generated_output": result.text,
                   "round": round_number},
                  generation_run_id=run.id)

        return jsonify({
            "section_id": section_id,
            "run_id": run.id,
            "provider": result.provider,
            "model": result.model,
            "offline": result.offline,
            "note": result.note,
            "html": markdown_to_html(result.text),
        })
    finally:
        db.close()


@app.route("/global-dossier/section/<section_id>")
def dossier_section(section_id):
    """Full read/refine view for one generated section."""
    db = get_db()
    try:
        engagement_id, brief, _ = engagement_context(db)
        run = (
            db.query(GenerationRun)
            .filter_by(engagement_id=engagement_id, deliverable_type="gvd")
            .filter(GenerationRun.resolved_prompt.like(f"{section_id}::%"))
            .first()
        )
        if not run:
            flash("That section has not been generated yet.", "error")
            return redirect(url_for("global_dossier"))

        return render_template(
            "generation_result.html",
            title=content.SECTION_BY_ID[section_id]["title"],
            subtitle="Global Value Dossier section",
            run={"id": run.id, "provider": run.provider, "model": run.model,
                 "round": run.round_number, "created_at": run.created_at,
                 "output": run.generated_output,
                 "prompt": run.resolved_prompt.split("::", 1)[-1]},
            back_url=url_for("global_dossier"),
            brief=brief,
        )
    finally:
        db.close()


@app.route("/generation/<int:run_id>/refine", methods=["POST"])
def refine_generation(run_id):
    db = get_db()
    try:
        engagement_id = active_engagement_id(db)
        run = db.get(GenerationRun, run_id)
        if not run or run.engagement_id != engagement_id:
            flash("Generation not found.", "error")
            return redirect(url_for("documents"))

        if not can("edit_documents"):
            flash(f"{content.ROLE_LABELS[current_role()]} cannot edit documents.", "error")
            return redirect(request.referrer or url_for("documents"))

        instruction = (request.form.get("instruction") or "").strip()
        if not instruction:
            flash("Describe what to change before refining.", "error")
            return redirect(request.referrer or url_for("documents"))

        provider = request.form.get("provider", "offline")
        model = request.form.get("model") or llm.PROVIDERS.get(provider, {}).get("models", ["offline"])[0]
        api_key = request.form.get("api_key", "")

        prompt = (
            f"{run.resolved_prompt.split('::', 1)[-1]}\n\n"
            "# Layer 3 — Expert revision instruction\n"
            f"{instruction}\n\n"
            "Rewrite the section applying this instruction. Keep every factual claim traceable "
            "to the dataset summary above.\n\n"
            "# Current draft\n"
            f"{run.generated_output}"
        )
        result = llm.generate(prompt, content.refine(run.generated_output, instruction),
                              provider, model, api_key)

        run.generated_output = result.text
        run.provider = result.provider
        run.model = result.model
        run.round_number += 1
        run.completed_at = datetime.utcnow()
        db.commit()

        log_event(db, engagement_id, "generation.refined", "user", current_role(),
                  {"instruction": instruction, "provider": result.provider,
                   "offline": result.offline, "round": run.round_number,
                   "resolved_prompt": prompt,
                   "generated_output": result.text},
                  generation_run_id=run.id)

        flash(result.note or f"Refined — now at round {run.round_number}.",
              "error" if result.note else "success")
        return redirect(request.referrer or url_for("documents"))
    finally:
        db.close()


# --------------------------------------------------------------------------
# MSL materials
# --------------------------------------------------------------------------


@app.route("/brand-template/upload", methods=["POST"])
def upload_brand_template():
    """Accept a corporate .pptx/.potx used to format generated slide decks."""
    db = get_db()
    try:
        engagement_id = active_engagement_id(db)

        if not can("manage_brand_guidelines"):
            flash(f"{content.ROLE_LABELS[current_role()]} cannot manage brand guidelines.", "error")
            return redirect(url_for("msl_material"))

        upload_file = request.files.get("template")
        if not upload_file or not upload_file.filename:
            flash("Choose a .pptx or .potx file to upload.", "error")
            return redirect(url_for("msl_material"))

        original = upload_file.filename
        if not deck.is_template(original):
            flash(f"{original} is not a PowerPoint template — expected .pptx or .potx.", "error")
            return redirect(url_for("msl_material"))

        safe_name = secure_filename(original)
        stored_name = f"{engagement_id}_{int(datetime.utcnow().timestamp())}_{safe_name}"
        destination = os.path.join(UPLOAD_DIR, stored_name)
        upload_file.save(destination)

        # Reject anything python-pptx cannot open, rather than storing a file that
        # will only fail later at export time.
        info = deck.inspect_template(destination)
        if info.get("error"):
            os.remove(destination)
            flash(f"{original} could not be read as a PowerPoint template — {info['error']}", "error")
            return redirect(url_for("msl_material"))

        record = UploadedFile(
            engagement_id=engagement_id,
            filename=original,
            file_path=stored_name,
            file_size=os.path.getsize(destination),
            sha256_checksum=dataset.checksum(destination),
            category="brand",
            uploaded_by=current_role(),
        )
        db.add(record)
        db.commit()

        log_event(db, engagement_id, "brand_template.uploaded", "client", current_role(),
                  {"filename": original, "checksum": record.sha256_checksum,
                   "layouts": info.get("layout_count"), "aspect_ratio": info.get("aspect_ratio"),
                   "fonts": f"{info.get('major_font')}/{info.get('minor_font')}"},
                  uploaded_file_id=record.id)

        flash(f"{original} uploaded — {info['layout_count']} layouts, {info['aspect_ratio']}. "
              "Slide decks will now use this template.", "success")
        return redirect(url_for("msl_material"))
    finally:
        db.close()


@app.route("/msl-material", methods=["GET", "POST"])
def msl_material():
    db = get_db()
    try:
        engagement_id, brief, stats = engagement_context(db)
        generated_run = None

        if request.method == "POST":
            if not can("edit_documents"):
                flash(f"{content.ROLE_LABELS[current_role()]} cannot generate materials.", "error")
                return redirect(url_for("msl_material"))

            material_id = request.form.get("material_type", "")
            if material_id not in content.MSL_MATERIAL_BY_ID:
                flash("Choose a material type first.", "error")
                return redirect(url_for("msl_material"))

            config = {
                "audience": request.form.get("audience", ""),
                "focus_area": request.form.get("focus_area", ""),
                "tone": request.form.get("tone", "scientific"),
                "key_messages": request.form.get("key_messages", ""),
                "brand_template_id": request.form.get("brand_template_id", ""),
            }
            provider = request.form.get("provider", "offline")
            model = request.form.get("model") or llm.PROVIDERS.get(provider, {}).get("models", ["offline"])[0]
            api_key = request.form.get("api_key", "")

            offline_draft = content.draft_msl_material(material_id, brief, stats, config)
            prompt = (
                f"Produce a {content.MSL_MATERIAL_BY_ID[material_id]['name']} for "
                f"{dict(content.AUDIENCES).get(config['audience'], 'healthcare professionals')}, "
                f"focused on {dict(content.FOCUS_AREAS).get(config['focus_area'], 'clinical performance')}, "
                f"in a {config['tone']} tone.\n\n"
                f"{content.build_section_prompt('clinical-efficacy', brief, stats, config['key_messages'])}"
            )
            result = llm.generate(prompt, offline_draft, provider, model, api_key)

            template_id = None
            if config["brand_template_id"].isdigit():
                candidate = db.get(UploadedFile, int(config["brand_template_id"]))
                if candidate and candidate.engagement_id == engagement_id:
                    template_id = candidate.id

            latest_brief = get_latest_brief(db, engagement_id)
            run = GenerationRun(
                engagement_id=engagement_id,
                brief_version_id=latest_brief.id,
                round_number=1,
                deliverable_type=material_id,
                resolved_prompt=f"{material_id}::{prompt}",
                prompt_provenance={"client": "layer-1", "template": "layer-2",
                                   "expert": "layer-3" if config["key_messages"] else None},
                provider=result.provider,
                model=result.model,
                brand_template_id=template_id,
                generated_output=result.text,
                status="completed",
                completed_at=datetime.utcnow(),
                created_by=current_role(),
            )
            db.add(run)
            db.commit()

            log_event(db, engagement_id, "generation.completed", "user", current_role(),
                      {"deliverable": material_id, "provider": result.provider,
                       "model": result.model, "offline": result.offline, **config},
                      generation_run_id=run.id)

            if result.note:
                flash(result.note, "error")

            generated_run = {
                "id": run.id, "provider": run.provider, "model": run.model,
                "output": run.generated_output, "material": content.MSL_MATERIAL_BY_ID[material_id],
                "config": config,
                "is_deck": material_id == "slide-deck",
                "brand_template": (db.get(UploadedFile, template_id).filename
                                   if template_id else None),
            }

        return render_template(
            "msl_material.html",
            brief=brief,
            stats=stats,
            materials=content.MSL_MATERIALS,
            audiences=content.AUDIENCES,
            focus_areas=content.FOCUS_AREAS,
            tones=content.TONES,
            providers=llm.PROVIDERS,
            templates=brand_templates(db, engagement_id),
            generated=generated_run,
        )
    finally:
        db.close()


# --------------------------------------------------------------------------
# Document library
# --------------------------------------------------------------------------


@app.route("/documents")
def documents():
    db = get_db()
    try:
        engagement_id, brief, _ = engagement_context(db)
        runs = (
            db.query(GenerationRun)
            .filter_by(engagement_id=engagement_id)
            .order_by(GenerationRun.created_at.desc())
            .all()
        )

        type_filter = request.args.get("type", "All Types")
        market_filter = request.args.get("market", "All Markets")
        language_filter = request.args.get("language", "All Languages")

        markets = brief.get("target_markets") or ["Spain"]
        languages = brief.get("languages") or ["English"]

        items = []
        for run in runs:
            key = run.resolved_prompt.split("::")[0]
            if run.deliverable_type == "gvd":
                doc_type = "Global Value Dossier"
                title = f"GVD — {content.SECTION_BY_ID.get(key, {}).get('title', key)}"
            else:
                doc_type = "MSL Material"
                title = content.MSL_MATERIAL_BY_ID.get(run.deliverable_type, {}).get(
                    "name", run.deliverable_type)
            items.append({
                "id": run.id,
                "title": title,
                "type": doc_type,
                "market": markets[0],
                "language": languages[0],
                "date": run.created_at,
                "size": file_size_label(len((run.generated_output or "").encode("utf-8"))),
                "status": "Final" if run.round_number > 1 else "Draft",
                "provider": run.provider,
                "model": run.model,
                "round": run.round_number,
                "format": "PPTX" if run.deliverable_type == "slide-deck" else "MD",
            })

        doc_types = ["All Types"] + sorted({item["type"] for item in items})
        market_options = ["All Markets"] + markets
        language_options = ["All Languages"] + languages

        filtered = [
            item for item in items
            if (type_filter in ("All Types", item["type"]))
            and (market_filter in ("All Markets", item["market"]))
            and (language_filter in ("All Languages", item["language"]))
        ]

        return render_template(
            "documents.html",
            items=filtered,
            total=len(items),
            doc_types=doc_types,
            markets=market_options,
            languages=language_options,
            selected={"type": type_filter, "market": market_filter, "language": language_filter},
        )
    finally:
        db.close()


@app.route("/documents/<int:run_id>")
def document_detail(run_id):
    db = get_db()
    try:
        engagement_id, brief, _ = engagement_context(db)
        run = db.get(GenerationRun, run_id)
        if not run or run.engagement_id != engagement_id:
            flash("Document not found.", "error")
            return redirect(url_for("documents"))

        key = run.resolved_prompt.split("::")[0]
        title = (content.SECTION_BY_ID.get(key, {}).get("title")
                 or content.MSL_MATERIAL_BY_ID.get(run.deliverable_type, {}).get("name")
                 or run.deliverable_type)

        return render_template(
            "generation_result.html",
            title=title,
            subtitle="Global Value Dossier section" if run.deliverable_type == "gvd" else "MSL material",
            run={"id": run.id, "provider": run.provider, "model": run.model,
                 "round": run.round_number, "created_at": run.created_at,
                 "output": run.generated_output,
                 "prompt": run.resolved_prompt.split("::", 1)[-1]},
            back_url=url_for("documents"),
            brief=brief,
        )
    finally:
        db.close()


@app.route("/documents/<int:run_id>/download")
def download_document(run_id):
    db = get_db()
    try:
        engagement_id = active_engagement_id(db)
        run = db.get(GenerationRun, run_id)
        if not run or run.engagement_id != engagement_id:
            flash("Document not found.", "error")
            return redirect(url_for("documents"))
        if not can("export_documents"):
            flash(f"{content.ROLE_LABELS[current_role()]} cannot export documents.", "error")
            return redirect(url_for("documents"))

        key = run.resolved_prompt.split("::")[0]
        stem = f"approved_{run.deliverable_type}_{key}_r{run.round_number}"

        # A slide deck is exported as a real .pptx, rendered into the client's own
        # brand template when one was chosen. Everything else exports as Markdown.
        if run.deliverable_type == "slide-deck":
            template_path = None
            template_name = None
            if run.brand_template_id:
                record = db.get(UploadedFile, run.brand_template_id)
                if record and record.engagement_id == engagement_id:
                    candidate = os.path.join(UPLOAD_DIR, record.file_path)
                    if os.path.exists(candidate):
                        template_path = candidate
                        template_name = record.filename

            payload, note = deck.build_deck(
                run.generated_output or "",
                template_path,
                title=content.MSL_MATERIAL_BY_ID["slide-deck"]["name"],
                subtitle=f"{brief_subtitle(db, engagement_id)}",
            )
            if payload:
                filename = f"{stem}.pptx"
                path = os.path.join(STORAGE_DIR, secure_filename(filename))
                with open(path, "wb") as handle:
                    handle.write(payload)
                log_event(db, engagement_id, "document.exported", "user", current_role(),
                          {"filename": filename, "format": "pptx",
                           "brand_template": template_name, "note": note or None},
                          generation_run_id=run.id)
                return send_file(path, as_attachment=True, download_name=filename)
            flash(note or "Could not build the PowerPoint file; exported as Markdown instead.",
                  "error")

        filename = f"{stem}.md"
        path = os.path.join(STORAGE_DIR, secure_filename(filename))
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(run.generated_output or "")

        log_event(db, engagement_id, "document.exported", "user", current_role(),
                  {"filename": filename, "format": "md"}, generation_run_id=run.id)
        return send_file(path, as_attachment=True, download_name=filename)
    finally:
        db.close()


def brief_subtitle(db, engagement_id: int) -> str:
    """Short line for a deck's title slide — device area and markets from the brief."""
    brief = get_latest_brief(db, engagement_id)
    if not brief:
        return ""
    markets = ", ".join(brief.target_markets or [])
    return " · ".join(part for part in (brief.therapeutic_area, markets) if part)


# --------------------------------------------------------------------------
# Submission wizard
# --------------------------------------------------------------------------

WIZARD_STEPS = [
    {"number": 1, "name": "Upload Data", "description": "Pivotal clinical data"},
    {"number": 2, "name": "Select Markets", "description": "GVD target markets"},
    {"number": 3, "name": "Select Languages", "description": "Content languages"},
    {"number": 4, "name": "AI Instructions", "description": "Generation parameters"},
    {"number": 5, "name": "Review & Submit", "description": "Final review"},
]


@app.route("/submission", methods=["GET", "POST"])
def submission():
    db = get_db()
    try:
        engagement_id, brief, stats = engagement_context(db)
        wizard = session.get("wizard") or {
            "step": 1, "markets": [market["id"] for market in content.MARKETS if market.get("default")],
            "languages": [lang["code"] for lang in content.LANGUAGES if lang.get("default")],
            "database": "", "methodology": "", "special_requirements": "",
        }

        if request.method == "POST":
            action = request.form.get("action", "next")
            step = int(request.form.get("step", 1))

            if step == 2:
                wizard["markets"] = request.form.getlist("markets")
            elif step == 3:
                wizard["languages"] = request.form.getlist("languages")
            elif step == 4:
                wizard["database"] = request.form.get("database", "")
                wizard["methodology"] = request.form.get("methodology", "")
                wizard["special_requirements"] = request.form.get("special_requirements", "")

            if action == "submit":
                latest = get_latest_brief(db, engagement_id)
                if latest:
                    latest.target_markets = [
                        market["name"] for market in content.MARKETS
                        if market["id"] in wizard["markets"]
                    ] or latest.target_markets
                    latest.languages = [
                        lang["name"] for lang in content.LANGUAGES
                        if lang["code"] in wizard["languages"]
                    ] or latest.languages
                    if wizard["special_requirements"]:
                        latest.additional_requirements = wizard["special_requirements"]
                    db.commit()

                log_event(db, engagement_id, "submission.queued", "user", current_role(),
                          {"markets": wizard["markets"], "languages": wizard["languages"],
                           "database": wizard["database"], "methodology": wizard["methodology"]})
                session["wizard"] = {**wizard, "step": 5}
                flash("Submission queued. Generate the dossier sections to produce the documents.",
                      "success")
                return redirect(url_for("global_dossier"))

            wizard["step"] = max(1, min(len(WIZARD_STEPS),
                                        step + (1 if action == "next" else -1)))
            session["wizard"] = wizard
            return redirect(url_for("submission"))

        session["wizard"] = wizard
        return render_template(
            "submission.html",
            steps=WIZARD_STEPS,
            wizard=wizard,
            stats=stats,
            brief=brief,
            markets=content.MARKETS,
            languages=content.LANGUAGES,
            databases=content.LITERATURE_DATABASES,
            methodologies=content.METHODOLOGIES,
        )
    finally:
        db.close()


# --------------------------------------------------------------------------
# Settings & audit
# --------------------------------------------------------------------------


@app.route("/settings", methods=["GET", "POST"])
def settings():
    roles = session.get("roles") or [
        {**role, "permissions": dict(role["permissions"])} for role in content.DEFAULT_ROLES
    ]

    if request.method == "POST":
        role_id = request.form.get("role_id")
        permission = request.form.get("permission")
        for role in roles:
            if role["id"] == role_id and role_id != "admin" and permission in role["permissions"]:
                role["permissions"][permission] = not role["permissions"][permission]
        session["roles"] = roles
        return redirect(url_for("settings"))

    session["roles"] = roles
    return render_template(
        "settings.html",
        roles=roles,
        permission_labels=content.PERMISSION_LABELS,
        providers=llm.PROVIDERS,
        env_keys={name: bool(os.getenv(env)) for name, env in llm.ENV_KEYS.items()},
    )


@app.route("/audit")
def audit_trail():
    db = get_db()
    try:
        engagement_id, brief, _ = engagement_context(db)
        events = get_engagement_trail(db, engagement_id)
        rows = [{
            "id": event.id,
            "type": event.event_type,
            "actor": f"{event.actor_identity} ({event.actor_type})",
            "created_at": event.created_at,
            "payload": json.dumps(event.payload or {}, indent=2, default=str),
        } for event in reversed(events)]
        return render_template("audit.html", events=rows, brief=brief)
    finally:
        db.close()


@app.route("/audit/download")
def download_audit_trail():
    """Download the complete audit trail as a Markdown document."""
    db = get_db()
    try:
        engagement_id = active_engagement_id(db)
        md = audit.export_audit_trail_md(db, engagement_id)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"approved_audit-trail_{timestamp}.md"
        return send_file(
            io.BytesIO(md.encode('utf-8')),
            mimetype='text/markdown',
            as_attachment=True,
            download_name=filename,
        )
    finally:
        db.close()


# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------


@app.errorhandler(404)
def not_found(error):
    return render_template("error.html", code=404,
                           message="That page does not exist."), 404


@app.errorhandler(500)
def server_error(error):
    return render_template("error.html", code=500,
                           message="Something went wrong on the server."), 500


@app.errorhandler(413)
def too_large(error):
    flash("That file exceeds the 100 MB per-file limit.", "error")
    return redirect(url_for("upload")), 302


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def open_browser(port: int):
    import webbrowser
    webbrowser.open(f"http://localhost:{port}")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))

    if os.getenv("OPEN_BROWSER", "1") == "1":
        timer = Timer(1.2, open_browser, args=(port,))
        timer.daemon = True
        timer.start()

    live = [name for name, env in llm.ENV_KEYS.items() if os.getenv(env)]

    print("\n" + "=" * 64)
    print("  APProved — Medical Writing Platform (prototype)")
    print("=" * 64)
    print(f"  URL      : http://localhost:{port}")
    print(f"  Landing  : choose the Tool (blank) or the Demo (CGM · MDR · Spain)")
    print(f"  LLM mode : {'live keys detected for ' + ', '.join(live) if live else 'offline (no API key needed)'}")
    print("  Stop     : Ctrl+C")
    print("=" * 64 + "\n")

    app.run(host="127.0.0.1", port=port, debug=True, use_reloader=False)
