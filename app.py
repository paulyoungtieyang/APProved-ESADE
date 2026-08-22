#!/usr/bin/env python3
"""
APProved — Python prototype with launchable HTML interface.

Run: python app.py
Then navigate to http://localhost:5000 in your browser.

Features:
- Two-view architecture (Client + User)
- Demo mode with sample CGM pivotal study data
- MDR/Spain regulatory focus
- Interactive prompt refinement
- Offline-capable with optional API key for LLM improvements
"""

import os
import sys
import webbrowser
import csv
from threading import Timer
from io import StringIO

from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from sqlalchemy.orm import Session, sessionmaker
from datetime import datetime

from core.models import init_db, Engagement, BriefVersion, UploadedFile, GenerationRun, AuditEvent
from core.audit import log_event
from core.briefs import create_brief_v1, get_latest_brief, brief_as_dict, amend_brief
from core.gates import consent_gate, data_quality_gate

# Configuration
os.makedirs("storage", exist_ok=True)
os.makedirs("storage/uploads", exist_ok=True)
os.makedirs("sample_data", exist_ok=True)

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


def load_sample_data():
    """Load sample CGM pivotal study data from CSV files."""
    sample_data = {}

    try:
        # Load pivotal study data
        with open("sample_data/cgm_pivotal_study.csv", "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            sample_data["pivotal_study"] = {
                "filename": "cgm_pivotal_study.csv",
                "rows": len(rows),
                "summary": f"Continuous Glucose Monitoring Pivotal Study - {len(rows)} patients",
                "metrics": {
                    "mean_age": 44.7,
                    "mean_mard": 9.4,
                    "mean_duration": 13.9,
                    "diabetes_type_1_pct": 65,
                }
            }

        # Load safety data
        with open("sample_data/safety_adverse_events.csv", "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            sample_data["safety"] = {
                "filename": "safety_adverse_events.csv",
                "rows": len(rows),
                "summary": f"Adverse Events Analysis - {len(rows)} documented events"
            }

        # Load efficacy data
        with open("sample_data/efficacy_analysis.csv", "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            sample_data["efficacy"] = {
                "filename": "efficacy_analysis.csv",
                "rows": len(rows),
                "summary": f"Efficacy Analysis - {len(rows)} primary endpoints"
            }
    except FileNotFoundError:
        pass

    return sample_data


SAMPLE_DATA = load_sample_data()


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

    # Convert to dicts before closing session
    engagements_data = [
        {
            "id": e.id,
            "client_name": e.client_name,
            "created_at": e.created_at,
            "consent_given": e.consent_given,
        }
        for e in engagements
    ]

    db.close()
    return render_template("user/index.html", engagements=engagements_data)


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

    # Convert to dict before closing session to avoid detached instance errors
    engagement_data = {
        "id": engagement.id,
        "client_name": engagement.client_name,
        "created_at": engagement.created_at,
        "consent_given": engagement.consent_given,
    }

    # Convert uploaded files to dicts
    files_data = [
        {
            "id": f.id,
            "filename": f.filename,
            "category": f.category,
            "created_at": f.created_at,
        }
        for f in uploaded_files
    ]

    db.close()
    return render_template(
        "user/context.html",
        engagement=engagement_data,
        brief=brief_data,
        uploaded_files=files_data,
    )


@app.route("/user/<int:engagement_id>/prompt", methods=["GET", "POST"])
def user_prompt(engagement_id):
    """User composes a prompt for generation with refinement capability."""
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

    # Convert to dict before closing session
    engagement_data = {
        "id": engagement.id,
        "client_name": engagement.client_name,
        "created_at": engagement.created_at,
        "consent_given": engagement.consent_given,
    }

    if request.method == "POST":
        deliverable_type = request.form.get("deliverable_type", "gvd").strip()
        provider = request.form.get("provider", "offline").strip()
        model = request.form.get("model", "local").strip()
        user_overlay = request.form.get("user_overlay", "").strip()
        api_key = request.form.get("api_key", "").strip()

        # Generate mock output (simulated)
        mock_output = generate_mock_gvd(brief_data, deliverable_type)

        # Create generation record
        generation_run = GenerationRun(
            engagement_id=engagement_id,
            brief_version_id=latest_brief.id,
            round_number=1,
            deliverable_type=deliverable_type,
            resolved_prompt=f"Generate {deliverable_type} for {brief_data['therapeutic_area']} in {brief_data['target_markets'][0]}. Overlay: {user_overlay[:100]}...",
            prompt_provenance={"client": 60, "template": 30, "user": 10},
            provider=provider if api_key else "offline",
            model=model,
            generated_output=mock_output,
            status="completed",
            created_by="expert"
        )
        db.add(generation_run)
        db.commit()

        log_event(
            db,
            engagement_id=engagement_id,
            event_type="generation.completed",
            actor_type="user",
            actor_identity="expert",
            payload={
                "deliverable_type": deliverable_type,
                "provider": provider,
                "model": model,
                "has_user_overlay": bool(user_overlay),
                "api_key_used": bool(api_key),
            },
            generation_run_id=generation_run.id,
        )

        db.close()
        return render_template(
            "user/generation_result.html",
            engagement=engagement_data,
            brief=brief_data,
            generation_run={
                "id": generation_run.id,
                "deliverable_type": deliverable_type,
                "output": mock_output,
                "provider": provider,
                "model": model,
            }
        )

    db.close()
    return render_template(
        "user/prompt.html",
        engagement=engagement_data,
        brief=brief_data,
        deliverable_types=["gvd", "slide_deck", "summary", "faq", "email_templates"],
        providers=["offline", "anthropic", "openai", "google"],
        models={
            "offline": ["local-simulation"],
            "anthropic": ["claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5-20251001"],
            "openai": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
            "google": ["gemini-pro", "gemini-1.5-pro"],
        },
    )


@app.route("/client/demo", methods=["GET"])
def client_demo():
    """Load demo engagement with sample CGM pivotal study data."""
    db = get_db()

    # Create demo engagement
    engagement = Engagement(client_name="Demo: ContinuousGlucose Monitoring Ltd.", consent_given=True)
    db.add(engagement)
    db.commit()
    engagement_id = engagement.id

    # Log consent
    log_event(
        db,
        engagement_id=engagement_id,
        event_type="consent.granted",
        actor_type="system",
        actor_identity="demo",
        payload={"demo_mode": True}
    )

    # Upload sample files programmatically
    for key, data in SAMPLE_DATA.items():
        uploaded = UploadedFile(
            engagement_id=engagement_id,
            filename=data["filename"],
            file_path=f"sample_data/{data['filename']}",
            file_size=12345,
            sha256_checksum="demo_" + key,
            category={"pivotal_study": "efficacy", "safety": "safety", "efficacy": "efficacy"}.get(key, "other"),
            uploaded_by="demo",
        )
        db.add(uploaded)

    db.commit()

    # Create demo brief
    brief = create_brief_v1(
        db,
        engagement_id,
        deliverable_types=["gvd"],
        therapeutic_area="Diagnostics & Monitoring",
        target_markets=["Spain", "European Union"],
        regulatory_frameworks=["MDR"],
        languages=["English", "Spanish"],
        output_formats=["PDF"],
        tone="Scientific",
        target_audience="Healthcare Providers, Regulatory Bodies",
        focus_area="Clinical Efficacy & Safety",
        key_messages="Continuous glucose monitoring with bolus calculator integration. MARD <10%. Superior hypoglycemia detection. Meets CE marking requirements under EU MDR.",
        dossier_sections=["executive-summary", "disease-epidemiology", "clinical-efficacy", "safety-tolerability"],
        regional_tender_spec="Spanish ICS contract requirements. Target launch Q2 2026.",
        additional_requirements="Focus on Spain market entry. MDR compliance documentation. Bolus calculator features. Competitive positioning vs Dexcom, Abbott Freestyle."
    )

    db.close()

    # Redirect to user view to start working
    return redirect(url_for("user_context", engagement_id=engagement_id))


def generate_mock_gvd(brief, deliverable_type):
    """Generate a mock Global Value Dossier output for demonstration."""
    therapeutic_area = brief.get("therapeutic_area", "Diagnostics")
    market = brief.get("target_markets", ["Global"])[0]

    if deliverable_type == "gvd":
        return f"""## Executive Summary

A novel Continuous Glucose Monitoring (CGM) system with integrated bolus calculator designed for patients with Type 1 and Type 2 diabetes. The device combines real-time glucose monitoring with predictive analytics to improve glycemic control and reduce hypoglycemic events.

**Key Clinical Benefits:**
- Mean Absolute Relative Difference (MARD): 9.4% ± 0.6%
- Hypoglycemia Detection Rate: 94.2%
- Time-in-Range Improvement: +23.4% vs. conventional monitoring
- Nocturnal Hypoglycemia Reduction: 35.2%

## Disease & Epidemiology

### Diabetes in Spain
Spain has a significant diabetes burden affecting approximately 2.5-3 million patients (6-7% of adult population). Type 2 diabetes represents 85-90% of cases, while Type 1 diabetes affects 8-10% of the diabetic population.

### Unmet Medical Needs
- Suboptimal glycemic control: Only 30% of Type 2 patients achieve HbA1c targets
- Hypoglycemic events: 1-2 severe events per patient-year in insulin users
- Treatment burden: Multiple daily injections and fingerstick testing
- Limited real-time feedback on glucose trends

## Clinical Efficacy Data

### Pivotal Study Design
- **Population:** 20 patients (60% Type 1, 40% Type 2)
- **Study Duration:** 14 days per patient
- **Primary Endpoint:** MARD ≤10%
- **Secondary Endpoints:** Hypoglycemia detection rate, safety

### Efficacy Results
- **Primary Endpoint Achieved:** MARD 9.4% [95% CI: 8.8-10.0%, p<0.001]
- **Hypoglycemia Detection:** 94.2% sensitivity, 91.7% specificity
- **Glucose Variability:** 28.5% reduction vs. conventional monitoring
- **Sensor Performance:** 13.8-day mean lifespan (target: 14 days)

## Safety & Tolerability

### Adverse Events Summary
- **Total Events:** 10 documented
- **Serious Adverse Events:** 0
- **Mild/Moderate Events:** 10 (skin irritation 2, hyperglycemia 2, calibration issues 3, hypoglycemia 2, device performance 1)
- **Resolution Rate:** 100%

### Safety Profile
- Skin irritation managed with adhesive alternatives
- Calibration drift addressed with system improvements
- No serious device-related events
- Excellent long-term safety (14-day observation)

## Pharmacoeconomic Analysis

### Spanish Healthcare Perspective
- **Annual Cost-Effectiveness:** €2,400-3,200 per patient per year
- **Cost per Quality-Adjusted Life Year (QALY):** €18,500 (vs. €30,000 conventional)
- **Budget Impact (100,000 patients):** €45-60M annual investment
- **Return on Investment:** Hypoglycemia reduction alone saves €8-12M annually

### Payer Value Proposition
- Reduces emergency department visits by 35%
- Decreases hospitalization for hypoglycemic episodes by 42%
- Improves HbA1c by 0.8-1.2% vs. conventional monitoring
- Enables early intervention in hyperglycemic crises

## Comparative Effectiveness

### vs. Dexcom G6
- Comparable MARD (9.4% vs. 9.0%)
- Superior hypoglycemia detection (94.2% vs. 92%)
- Integrated bolus calculator (Dexcom: requires separate app)
- Cost: 15% lower in Spanish market

### vs. Abbott Freestyle
- Superior real-time glucose display (14-day CGM vs. 14-day FGM)
- Integrated predictive alerts
- Better patient satisfaction (4.2/5.0 vs. 3.8/5.0)

## Regulatory Status

### EU MDR Compliance
- Device Classification: Class II (Medical Device Regulation 2017/745)
- Conformity Assessment: Annex IX (Quality Management System)
- Notified Body: Approved under EU MDR pathway
- CE Mark Expected: Q1 2026

### Spanish Market Approval
- AEMPS Registration: Pending (submitted Q3 2025)
- Spanish Reimbursement: ICS negotiation ongoing
- Launch Timeline: Q2 2026 (post-CE marking)

## Conclusion

This Continuous Glucose Monitoring system with bolus calculator represents a significant advancement in diabetes care, offering superior efficacy, safety, and user experience compared to existing solutions. The clinical evidence base, combined with economic value and regulatory compliance, positions this device for successful market entry in Spain and the EU.

**Recommended Actions:**
1. Complete CE marking documentation
2. Finalize Spanish reimbursement negotiations
3. Prepare physician training program
4. Establish patient support services"""

    elif deliverable_type == "summary":
        return f"""# Medical Summary Document: CGM System with Bolus Calculator

## Clinical Overview
Continuous Glucose Monitoring (CGM) system achieving 9.4% MARD with integrated bolus calculator for optimal insulin dosing. Designed for Type 1 and Type 2 diabetes management.

## Key Efficacy Metrics
- **MARD:** 9.4% (Primary endpoint: MARD ≤10%)
- **Hypoglycemia Detection:** 94.2% sensitivity
- **Safety Events:** 10 mild-moderate (0 serious)
- **Patient Satisfaction:** 4.2/5.0

## Clinical Value
- 23.4% improvement in Time-in-Range vs. conventional monitoring
- 35.2% reduction in nocturnal hypoglycemic events
- Cost-effective: €18,500 per QALY vs. €30,000 conventional

## Market Status
- EU MDR Class II device
- CE marking expected Q1 2026
- Spanish AEMPS registration submitted
- Launch planned Q2 2026

## Contraindications & Warnings
- Not recommended for patients with severe adhesive allergies
- Requires minimum 2 fingerstick calibrations per 14-day wear cycle
- Not approved for pediatric patients <4 years old (under clinical investigation)

## References
Based on pivotal study with 20 patients, 14-day observation period. Safety surveillance ongoing post-launch."""

    else:
        return f"Mock {deliverable_type} output for {brief.get('therapeutic_area')} in {market}. This is a simulated demonstration."


@app.route("/user/<int:engagement_id>/generation/<int:generation_id>/refine", methods=["POST"])
def user_refine_generation(engagement_id, generation_id):
    """Refine generated output with user feedback and optional API improvement."""
    db = get_db()

    generation_run = db.query(GenerationRun).get(generation_id)
    if not generation_run or generation_run.engagement_id != engagement_id:
        db.close()
        return "Generation not found", 404

    refinement_prompt = request.form.get("refinement_prompt", "").strip()
    use_api = request.form.get("use_api") == "on"
    api_key = request.form.get("api_key", "").strip() if use_api else None

    # Simulate refinement
    refined_output = simulate_refinement(
        generation_run.generated_output,
        refinement_prompt,
        use_api=use_api
    )

    # Log refinement
    log_event(
        db,
        engagement_id=engagement_id,
        event_type="generation.refined",
        actor_type="user",
        actor_identity="expert",
        payload={
            "refinement_prompt": refinement_prompt[:200],
            "used_api": use_api,
        },
        generation_run_id=generation_id,
    )

    # Create a new version of the generation with refined output
    generation_run.generated_output = refined_output
    generation_run.status = "refined"
    db.commit()

    db.close()
    return redirect(url_for("user_prompt", engagement_id=engagement_id))


def simulate_refinement(original_output, refinement_prompt, use_api=False):
    """Simulate output refinement (in Phase 2, this will call actual LLM)."""
    improvement = "\n\n---\n\n## Refinement Applied\n"
    improvement += f"**User Feedback:** {refinement_prompt[:100]}...\n\n"

    if use_api:
        improvement += "**Enhancement Level:** Full API refinement (would use Claude/GPT-4/Gemini in Phase 2)\n"
    else:
        improvement += "**Enhancement Level:** Offline simulation mode\n"

    improvement += "In Phase 2, the refined output will be regenerated through the selected LLM provider based on your feedback."

    return original_output + improvement


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


def open_browser(port=5001):
    """Open the browser after a short delay."""
    webbrowser.open(f"http://localhost:{port}")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))

    # Open browser after 1 second
    timer = Timer(1.0, lambda: open_browser(port))
    timer.daemon = True
    timer.start()

    print("\n" + "=" * 60)
    print("APProved — Python Prototype")
    print("=" * 60)
    print(f"Server running at http://localhost:{port}")
    print("Press Ctrl+C to stop\n")

    app.run(host="127.0.0.1", port=port, debug=True, use_reloader=False)
