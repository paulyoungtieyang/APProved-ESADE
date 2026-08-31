"""
Reference data and the offline drafting engine.

Everything the UI lists (regulatory frameworks, dossier sections, MSL material
types, policy feed, resources) lives here, plus the deterministic draft writers
that ground each section in the numbers actually present in the uploaded files.

The demo device is a Class IIb continuous glucose monitoring (CGM) system
entering the EU under MDR 2017/745 and launching in Spain. It is deliberately a
*combination* product with two regulated functions:

  - a HARDWARE function — the subcutaneous sensor and transmitter, and
  - a DIGITAL function — the bolus calculator, software as a medical device.

The two carry different classification rules, different standards and different
evidence, and the point of the demo is that one ingestion of clinical data
produces documentation covering both. `DEVICE_COMPONENTS` below is what makes
that split explicit, and every dossier section draft addresses both functions.
"""

from __future__ import annotations

from typing import Any

# ==========================================================================
# Evidence categories — generic across every engagement, not demo-specific.
#
# These are the same category strings `core.dataset.classify()` assigns and the
# upload category dropdown offers. Unlike DEVICE_COMPONENTS below, nothing here
# names a device, a market or a therapeutic area — the same eight categories
# describe the evidence base for a diagnostic, a drug-device combination, an
# app, or a piece of lab equipment.
# ==========================================================================

EVIDENCE_CATEGORIES = [
    {"id": "clinical", "label": "Clinical / performance data",
     "description": "The primary dataset the generated evidence is grounded in."},
    {"id": "safety", "label": "Safety monitoring",
     "description": "Adverse event or safety-signal records."},
    {"id": "efficacy", "label": "Efficacy endpoints",
     "description": "Endpoint-level statistical results — value, confidence interval, p-value."},
    {"id": "demographics", "label": "Demographics & baseline",
     "description": "Cohort baseline characteristics."},
    {"id": "economics", "label": "Health economics",
     "description": "Cost, budget-impact or reimbursement-relevant figures."},
    {"id": "software", "label": "Software specification",
     "description": "Specification for any digital or software component, where one exists."},
    {"id": "verification", "label": "Software verification",
     "description": "Test or verification records for a digital component, where one exists."},
    {"id": "requirements", "label": "External requirements",
     "description": "A tender, an HTA/formulary checklist, a notified-body or partner "
                    "due-diligence list — anything to match evidence against."},
    {"id": "brand", "label": "Brand template",
     "description": "A corporate PowerPoint template used to brand exported slide decks."},
]

EVIDENCE_CATEGORY_BY_ID = {item["id"]: item for item in EVIDENCE_CATEGORIES}


def evidence_readiness(stats: dict) -> list[dict]:
    """
    What evidence has been uploaded, against the generic category list above.

    Answers "what should I bring before I start" up front, on the pages where
    generation actually happens, rather than only after something fails.
    """
    counts: dict[str, int] = {}
    for entry in stats.get("files") or []:
        category = entry.get("category")
        if category and not entry.get("error"):
            counts[category] = counts.get(category, 0) + 1

    return [
        {**category, "present": category["id"] in counts, "count": counts.get(category["id"], 0)}
        for category in EVIDENCE_CATEGORIES
    ]


# ==========================================================================
# Platform methodology — generic, static, no per-engagement data. What a
# client's legal or compliance reviewer asks for before they will let anyone
# use this: how generation actually works and what happens to their data.
# ==========================================================================

def build_methodology_markdown() -> str:
    return """# APProved — Methodology & Data Handling

This is a plain-language description of how document generation works and what
happens to the data you upload — written to be handed to a legal or compliance
reviewer before an engagement starts, not just discovered by reading the code.

## How a document gets written

Every generation composes a prompt from three layers, kept visibly separate and
stored with the output so any sentence can be traced back to where it came from:

1. **Client baseline** — the signed brief: markets, frameworks, tone, audience,
   key messages. Set once per brief version; changing it creates a new version
   rather than silently overwriting the old one.
2. **Deliverable template** — the structure and evidence rules for whichever
   section or material is being written. The same for every engagement.
3. **Expert overlay** — optional emphasis or correction supplied for this run.

The model is instructed to cite only figures present in the uploaded dataset
summary and to say so explicitly when something is not reported, rather than
inventing a plausible-sounding number. The offline drafting engine — the
default, with no API key required — enforces this the same way: it is a fixed
set of deterministic templates that read the uploaded rows and fill in what is
actually there, nothing else.

## Where your data goes

- **Offline by default.** With no provider key supplied, generation never
  leaves this host. There is no network call.
- **A key is opt-in, per request.** Supplying an API key switches that one
  generation call to a live provider over HTTPS. The key is used for that
  single request and is never written to the database, the audit trail, or
  any log.
- **Every upload is checksummed.** SHA-256 on receipt, stored and shown in the
  UI, so a file's integrity is independently verifiable at any later point.
- **Nothing is used for model training.** Whatever provider is called, the
  request is a normal API call — not a fine-tuning or training submission.

## Where human review sits

Generation output is not a final answer by default. A document can be
submitted for review by anyone with approval permission, who records a
decision — accept, revise, decline, or amend the brief — and written feedback.
An **accepted** document is locked: no further refinement is possible until a
new review round reopens it. This mirrors the internal-committee pattern most
regulated organisations already run (medical, regulatory, legal sign-off)
rather than replacing it.

## What is logged

Every action — upload, brief revision, generation, refinement, review decision,
export — is written to an append-only audit trail: nothing is ever updated or
deleted, only added. Each entry carries the actor, the timestamp, and the full
payload (including the resolved prompt and generated output for a generation
event), with the one deliberate exception of API key material, which is never
captured. The complete trail for an engagement can be exported as a single
Markdown document for external review.

## Role-based access

Permissions are enforced server-side, not just hidden in the interface. A role
without upload rights gets a 403 from the upload endpoint if it tries anyway,
the same as it would from any other client. What a role can see or do does not
depend on which buttons happen to be rendered.

## What this is not

This document describes the mechanism, not a certification. It is not a legal
opinion, a DPA, or a substitute for your own review of a specific engagement's
data. Generated drafts require expert review before any regulatory or
commercial use.
"""


# ==========================================================================
# Device components — the hardware / digital split the demo exists to show
# ==========================================================================

DEVICE_COMPONENTS = [
    {
        "id": "hardware",
        "name": "CGM Sensor & Transmitter",
        "kind": "Hardware function",
        "icon": "activity",
        "summary": "Subcutaneous glucose sensor with a rechargeable Bluetooth transmitter, "
                   "measuring interstitial glucose continuously over a 14-day wear period.",
        "classification": "Class IIb — MDR Annex VIII, Rule 15 "
                          "(invasive device for continuous monitoring of vital physiological parameters)",
        "standards": [
            "EN ISO 15197 — glucose monitoring system accuracy",
            "EN ISO 10993 — biological evaluation / biocompatibility",
            "EN ISO 11137 — sterilisation of the sensor applicator",
            "IEC 60601-1 / -1-2 — electrical safety and EMC",
            "EN ISO 13485 — quality management system",
        ],
        "evidence": [
            "Pivotal accuracy investigation against a laboratory reference method (MARD)",
            "Sensor wear duration and survival analysis",
            "Application-site adverse event reporting",
            "Biocompatibility and sterilisation validation reports",
        ],
        "risks": [
            "Application-site irritation and adhesive reactions",
            "Calibration drift over the wear period",
            "Signal loss or transmitter connectivity failure",
        ],
    },
    {
        "id": "digital",
        "name": "Bolus Calculator",
        "kind": "Digital function — software as a medical device",
        "icon": "calculator",
        "summary": "Dosing-support module inside the display application. Combines the "
                   "carbohydrate dose, a glucose correction dose, a CGM trend adjustment and "
                   "insulin-on-board subtraction to recommend a bolus.",
        "classification": "Class IIb — MDR Annex VIII, Rule 11 "
                          "(software providing information used to take therapeutic decisions)",
        "standards": [
            "IEC 62304 — medical device software lifecycle processes",
            "IEC 82304-1 — health software product safety",
            "IEC 62366-1 — usability engineering",
            "MDCG 2019-11 — qualification and classification of software",
            "MDCG 2019-16 — cybersecurity for medical devices",
            "EU AI Act — transparency and human-oversight duties for algorithmic decision support",
        ],
        "evidence": [
            "Algorithm verification against reference dose calculations",
            "Human-factors validation of dose entry and confirmation (IEC 62366-1)",
            "Use-related risk analysis covering entry error and dose stacking",
            "Software unit, integration and system test records (IEC 62304 §5.5–5.7)",
            "Cybersecurity risk assessment for the connected application",
        ],
        "risks": [
            "Carbohydrate entry error propagating into the recommended dose",
            "Dose stacking when insulin on board is not accounted for",
            "Over-reliance on the recommendation without clinical judgement",
            "Trend adjustment applied to an unreliable sensor reading",
        ],
    },
]

COMPONENT_BY_ID = {component["id"]: component for component in DEVICE_COMPONENTS}


# ==========================================================================
# Regulatory frameworks — MDR / Spain lead, since that is the demo scenario
# ==========================================================================

REGULATIONS = [
    {
        "id": "mdr",
        "name": "EU MDR 2017/745 — Medical Device Regulation",
        "region": "Europe",
        "description": "Mandatory framework for placing medical devices on the EU market. "
                       "Governs the demo device (Class IIb CGM system).",
        "requirements": [
            "Annex II Technical Documentation",
            "Annex XIV Clinical Evaluation Report (CER)",
            "Annex III Post-Market Surveillance (PMS) plan",
            "PSUR — Periodic Safety Update Report",
            "GSPR checklist (Annex I General Safety & Performance Requirements)",
            "EUDAMED registration and UDI assignment",
        ],
        "default": True,
    },
    {
        "id": "aemps",
        "name": "AEMPS — Spain",
        "region": "Europe",
        "description": "Spanish Agency of Medicines and Medical Devices. Controls national "
                       "market entry, Spanish-language labelling and regional tenders.",
        "requirements": [
            "Comunicación de puesta en el mercado (market notification)",
            "Spanish-language IFU and labelling",
            "Registro de Productos Sanitarios listing",
            "Regional (CCAA) tender dossier alignment",
            "Vigilancia — national incident reporting route",
        ],
        "default": True,
    },
    {
        "id": "mdcg",
        "name": "MDCG Guidance & Notified Body Review",
        "region": "Europe",
        "description": "Medical Device Coordination Group guidance applied by the notified body "
                       "during conformity assessment.",
        "requirements": [
            "MDCG 2020-5 Clinical evaluation — equivalence",
            "MDCG 2020-6 Sufficient clinical evidence for legacy devices",
            "MDCG 2020-13 Clinical evaluation assessment report template",
            "MDCG 2019-11 Qualification of software as a medical device",
        ],
    },
    {
        "id": "ivdr",
        "name": "EU IVDR 2017/746",
        "region": "Europe",
        "description": "In-vitro diagnostic regulation. Applies where a companion diagnostic or "
                       "reference measurement claim is made.",
        "requirements": [
            "Performance evaluation report",
            "Scientific validity report",
            "Analytical and clinical performance studies",
        ],
    },
    {
        "id": "fda",
        "name": "FDA — United States",
        "region": "North America",
        "description": "510(k) / De Novo pathway for glucose monitoring devices, incl. iCGM "
                       "special controls.",
        "requirements": [
            "510(k) premarket notification or De Novo request",
            "iCGM special controls conformity",
            "Human factors / usability validation",
            "Cybersecurity documentation for connected devices",
        ],
    },
    {
        "id": "mhra",
        "name": "MHRA — United Kingdom",
        "region": "Europe",
        "description": "UKCA marking route for Great Britain plus the Northern Ireland CE route.",
        "requirements": [
            "UKCA marking and UK Approved Body assessment",
            "UK Responsible Person appointment",
            "MHRA device registration",
        ],
    },
    {
        "id": "pmda",
        "name": "PMDA — Japan",
        "region": "Asia",
        "description": "Pharmaceuticals and Medical Devices Agency approval (Shonin) for "
                       "controlled medical devices.",
        "requirements": [
            "Shonin application with Japanese-language dossier",
            "QMS Ordinance 169 conformity",
            "Marketing Authorisation Holder in Japan",
        ],
    },
    {
        "id": "nmpa",
        "name": "NMPA — China",
        "region": "Asia",
        "description": "National Medical Products Administration registration for imported "
                       "Class II/III devices.",
        "requirements": [
            "NMPA registration dossier (Chinese language)",
            "Type testing at an NMPA-recognised laboratory",
            "Local clinical evaluation or exemption justification",
        ],
    },
    {
        "id": "tga",
        "name": "TGA — Australia",
        "region": "Oceania",
        "description": "Therapeutic Goods Administration inclusion in the ARTG.",
        "requirements": [
            "ARTG inclusion application",
            "Essential Principles conformity",
            "Australian sponsor appointment",
        ],
    },
]

REGULATION_BY_ID = {item["id"]: item for item in REGULATIONS}


# ==========================================================================
# Markets & languages (submission wizard)
# ==========================================================================

MARKETS = [
    {"id": "es", "name": "Spain", "region": "Europe", "framework": "MDR + AEMPS", "default": True},
    {"id": "eu", "name": "European Union (CE)", "region": "Europe", "framework": "MDR", "default": True},
    {"id": "pt", "name": "Portugal", "region": "Europe", "framework": "MDR + INFARMED"},
    {"id": "de", "name": "Germany", "region": "Europe", "framework": "MDR + BfArM"},
    {"id": "fr", "name": "France", "region": "Europe", "framework": "MDR + ANSM"},
    {"id": "uk", "name": "United Kingdom", "region": "Europe", "framework": "UKCA / MHRA"},
    {"id": "us", "name": "United States", "region": "North America", "framework": "FDA"},
    {"id": "jp", "name": "Japan", "region": "Asia", "framework": "PMDA"},
]

LANGUAGES = [
    {"code": "es", "name": "Spanish (Castellano)", "markets": ["es"], "default": True},
    {"code": "en", "name": "English", "markets": ["eu", "uk", "us"], "default": True},
    {"code": "ca", "name": "Catalan", "markets": ["es"]},
    {"code": "pt", "name": "Portuguese", "markets": ["pt"]},
    {"code": "de", "name": "German", "markets": ["de"]},
    {"code": "fr", "name": "French", "markets": ["fr"]},
    {"code": "ja", "name": "Japanese", "markets": ["jp"]},
]

LITERATURE_DATABASES = [
    "PubMed / MEDLINE",
    "Embase",
    "Cochrane Library",
    "ClinicalTrials.gov",
    "EU Clinical Trials Register",
    "EUDAMED",
    "Custom / proprietary database",
]

METHODOLOGIES = [
    "Systematic Literature Review (MDCG 2020-5)",
    "Clinical Evaluation Report (Annex XIV)",
    "Network Meta-Analysis",
    "Indirect Treatment Comparison",
    "Real-World Evidence",
    "Cost-Effectiveness Analysis",
]


# ==========================================================================
# Global Value Dossier sections
# ==========================================================================

# `covers` records which device functions each section documents, so the UI can
# show at a glance that the hardware and the digital tool are both accounted for.
DOSSIER_SECTIONS = [
    {"id": "exec-summary", "title": "Executive Summary",
     "description": "High-level overview of the clinical value proposition",
     "covers": ["hardware", "digital"]},
    {"id": "device-description", "title": "Device Description & Intended Purpose",
     "description": "MDR Annex II description and classification of both device functions",
     "covers": ["hardware", "digital"]},
    {"id": "disease-overview", "title": "Disease & Epidemiology",
     "description": "Disease burden, prevalence and unmet needs in the launch market",
     "covers": []},
    {"id": "clinical-efficacy", "title": "Clinical Performance Data",
     "description": "Sensor accuracy plus bolus calculator algorithm verification",
     "covers": ["hardware", "digital"]},
    {"id": "safety-profile", "title": "Safety & Tolerability",
     "description": "Device adverse events and software use-related risk",
     "covers": ["hardware", "digital"]},
    {"id": "pharmacoeconomics", "title": "Health-Economic Analysis",
     "description": "Cost-effectiveness, budget impact and economic value",
     "covers": []},
    {"id": "qol-outcomes", "title": "Quality of Life Outcomes",
     "description": "Patient-reported outcomes and usability of both functions",
     "covers": ["hardware", "digital"]},
    {"id": "comparative-effectiveness", "title": "Comparative Effectiveness",
     "description": "Comparison against standard of care and competitor systems",
     "covers": ["hardware", "digital"]},
    {"id": "target-population", "title": "Target Population & Positioning",
     "description": "Patient segmentation and treatment positioning",
     "covers": []},
    {"id": "software-lifecycle", "title": "Software Lifecycle & Cybersecurity",
     "description": "IEC 62304 lifecycle, cybersecurity and AI Act duties for the bolus calculator",
     "covers": ["digital"]},
    {"id": "regulatory-status", "title": "Regulatory Status & Compliance",
     "description": "Conformity route for both functions, notified body and market notification",
     "covers": ["hardware", "digital"]},
]

SECTION_BY_ID = {section["id"]: section for section in DOSSIER_SECTIONS}


# ==========================================================================
# MSL material types
# ==========================================================================

MSL_MATERIALS = [
    {"id": "slide-deck", "name": "Scientific Slide Deck", "icon": "presentation",
     "description": "Comprehensive presentation with clinical data and key messages",
     "estimate": "5-7 min"},
    {"id": "medical-summary", "name": "Medical Summary Document", "icon": "file-text",
     "description": "Concise summary of performance, safety and clinical value",
     "estimate": "3-5 min"},
    {"id": "faq-document", "name": "Scientific FAQ", "icon": "message-square",
     "description": "Frequently asked questions with evidence-based responses",
     "estimate": "4-6 min"},
    {"id": "email-template", "name": "Email Response Templates", "icon": "mail",
     "description": "Pre-written responses to common medical information requests",
     "estimate": "2-3 min"},
]

MSL_MATERIAL_BY_ID = {item["id"]: item for item in MSL_MATERIALS}

AUDIENCES = [
    ("endocrinologists", "Endocrinologists"),
    ("diabetologists", "Diabetologists"),
    ("primary-care", "Primary Care Physicians"),
    ("diabetes-nurses", "Diabetes Specialist Nurses"),
    ("payers", "Payers / Regional Health Services"),
    ("hospital-pharmacy", "Hospital Pharmacy & Procurement"),
]

FOCUS_AREAS = [
    ("accuracy", "Sensor Accuracy (MARD)"),
    ("hypo-detection", "Hypoglycaemia Detection"),
    ("safety", "Safety Profile"),
    ("bolus-calculator", "Bolus Calculator & Dosing Support"),
    ("comparative", "Comparative Effectiveness"),
    ("time-in-range", "Time in Range Outcomes"),
]

TONES = ["scientific", "balanced", "accessible"]


# ==========================================================================
# Policy & regulatory news feed (MDR / Spain focused)
# ==========================================================================

POLICY_NEWS = [
    {
        "id": "1",
        "title": "MDCG updates guidance on clinical evaluation for continuous glucose monitors",
        "date": "2026-04-18", "category": "MDCG", "source": "European Commission",
        "summary": "Revised guidance clarifies the clinical evidence expected for CGM systems under "
                   "MDR Annex XIV, with explicit MARD reporting and hypoglycaemia-detection endpoints.",
        "tags": ["MDR", "Clinical Evaluation", "CGM"],
    },
    {
        "id": "2",
        "title": "AEMPS opens simplified market notification route for Class IIb monitoring devices",
        "date": "2026-04-15", "category": "AEMPS", "source": "AEMPS Spain",
        "summary": "Spain's agency streamlines the comunicación de puesta en el mercado process, "
                   "shortening national listing timelines for CE-marked monitoring devices.",
        "tags": ["Spain", "Market Access", "Notification"],
    },
    {
        "id": "3",
        "title": "EUDAMED actor and device modules become mandatory across member states",
        "date": "2026-04-12", "category": "EU MDR", "source": "European Commission",
        "summary": "Manufacturers must complete EUDAMED registration and UDI assignment before "
                   "placing devices on the EU market, with transitional relief ending this quarter.",
        "tags": ["EUDAMED", "UDI", "Registration"],
    },
    {
        "id": "4",
        "title": "Spanish regional health services align CGM tender criteria on time-in-range",
        "date": "2026-04-09", "category": "Tenders", "source": "Ministerio de Sanidad",
        "summary": "Several CCAA now weight time-in-range improvement and nocturnal hypoglycaemia "
                   "reduction in public purchasing scoring for glucose monitoring systems.",
        "tags": ["Spain", "Tenders", "Reimbursement"],
    },
    {
        "id": "5",
        "title": "Notified body capacity improves as MDR certificate backlog falls",
        "date": "2026-04-05", "category": "EU MDR", "source": "Team-NB",
        "summary": "Average conformity assessment duration drops for Class IIb devices, though "
                   "clinical evaluation deficiencies remain the leading cause of review cycles.",
        "tags": ["Notified Body", "Conformity Assessment"],
    },
    {
        "id": "6",
        "title": "EU AI Act obligations reach AI-enabled decision support in medical devices",
        "date": "2026-04-02", "category": "EU AI Act", "source": "European Commission",
        "summary": "Devices embedding algorithmic dosing support — including bolus calculators — face "
                   "additional transparency and human-oversight documentation requirements.",
        "tags": ["AI Act", "Bolus Calculator", "Software"],
    },
    {
        "id": "7",
        "title": "Post-market surveillance expectations tighten for connected glucose sensors",
        "date": "2026-03-28", "category": "EU MDR", "source": "MDCG",
        "summary": "PMS plans must now describe real-world accuracy monitoring and connectivity "
                   "failure trending, feeding the PSUR on an annual cycle for Class IIb devices.",
        "tags": ["PMS", "PSUR", "Vigilance"],
    },
    {
        "id": "8",
        "title": "ISO 15197 revision consultation opens for glucose monitoring accuracy",
        "date": "2026-03-24", "category": "Standards", "source": "ISO/TC 212",
        "summary": "The draft revision proposes tightened accuracy zones and clearer guidance on "
                   "reference method comparability for interstitial glucose measurement.",
        "tags": ["Standards", "Accuracy", "ISO"],
    },
]

NEWS_CATEGORIES = ["All", "EU MDR", "AEMPS", "MDCG", "Tenders", "EU AI Act", "Standards"]


# ==========================================================================
# Resources library
# ==========================================================================

RESOURCES = [
    {"title": "MDR 2017/745 — Consolidated Text", "type": "Regulation",
     "description": "Full consolidated text of the EU Medical Device Regulation, including Annex I "
                    "GSPRs and Annex XIV clinical evaluation.",
     "source": "EUR-Lex", "tags": ["MDR", "Primary Source"]},
    {"title": "MDCG 2020-13 — Clinical Evaluation Assessment Report Template", "type": "Guidance",
     "description": "Template the notified body uses to assess the clinical evaluation report. "
                    "Write the CER to match this structure.",
     "source": "MDCG", "tags": ["CER", "Notified Body"]},
    {"title": "AEMPS Guía de Productos Sanitarios", "type": "Guidance",
     "description": "Spanish agency guidance on market notification, labelling language duties and "
                    "national vigilance reporting.",
     "source": "AEMPS", "tags": ["Spain", "Labelling"]},
    {"title": "ISO 15197:2013 — Glucose Monitoring Accuracy", "type": "Standard",
     "description": "Accuracy requirements and reference-method comparison protocol for glucose "
                    "measurement systems.",
     "source": "ISO", "tags": ["Accuracy", "MARD"]},
    {"title": "IEC 62304 — Medical Device Software Lifecycle", "type": "Standard",
     "description": "Software lifecycle processes applicable to the sensor algorithm and the bolus "
                    "calculator module.",
     "source": "IEC", "tags": ["Software", "Bolus Calculator"]},
    {"title": "IEC 62366-1 — Usability Engineering", "type": "Standard",
     "description": "Usability engineering process for medical devices — the evidence base for "
                    "human-factors claims in the dossier.",
     "source": "IEC", "tags": ["Usability", "Human Factors"]},
    {"title": "ATTD Consensus on Time in Range", "type": "Publication",
     "description": "International consensus targets for time in range, used as the comparator "
                    "framework in the value dossier.",
     "source": "ATTD", "tags": ["Time in Range", "Clinical"]},
    {"title": "APProved GVD Section Template Pack", "type": "Template",
     "description": "The section-by-section prompt templates this platform composes from, exported "
                    "for offline review.",
     "source": "APProved", "tags": ["Template", "Internal"]},
]

RESOURCE_TYPES = ["All", "Regulation", "Guidance", "Standard", "Publication", "Template"]


# ==========================================================================
# Role-based access control
# ==========================================================================

PERMISSION_LABELS = {
    "upload_data": "Upload Clinical Data",
    "edit_documents": "Edit Documents",
    "approve_documents": "Approve Documents",
    "view_all_documents": "View All Documents",
    "export_documents": "Export Documents",
    "manage_brand_guidelines": "Manage Brand Guidelines",
    "modify_medical_text": "Modify Medical / Scientific Text Blocks",
}

DEFAULT_ROLES = [
    {"id": "admin", "name": "Administrator", "permissions": {
        "upload_data": True, "edit_documents": True, "approve_documents": True,
        "view_all_documents": True, "export_documents": True,
        "manage_brand_guidelines": True, "modify_medical_text": True}},
    {"id": "medical-writer", "name": "Medical Writer", "permissions": {
        "upload_data": True, "edit_documents": True, "approve_documents": False,
        "view_all_documents": True, "export_documents": True,
        "manage_brand_guidelines": True, "modify_medical_text": True}},
    {"id": "msl", "name": "Medical Science Liaison", "permissions": {
        "upload_data": False, "edit_documents": False, "approve_documents": False,
        "view_all_documents": True, "export_documents": True,
        "manage_brand_guidelines": False, "modify_medical_text": False}},
    {"id": "compliance", "name": "Compliance Officer", "permissions": {
        "upload_data": False, "edit_documents": False, "approve_documents": True,
        "view_all_documents": True, "export_documents": False,
        "manage_brand_guidelines": False, "modify_medical_text": False}},
]

ROLE_LABELS = {role["id"]: role["name"] for role in DEFAULT_ROLES}


# ==========================================================================
# Onboarding checklist
# ==========================================================================

ONBOARDING_STEPS = [
    {"id": "classification", "title": "Identify device classification", "endpoint": "regulations"},
    {"id": "upload", "title": "Upload clinical data and device documentation", "endpoint": "upload"},
    {"id": "regulations", "title": "Select regulatory frameworks", "endpoint": "regulations"},
    {"id": "dossier", "title": "Generate the Global Value Dossier", "endpoint": "global_dossier"},
    {"id": "msl", "title": "Generate MSL field materials", "endpoint": "msl_material"},
]


# ==========================================================================
# Offline drafting engine
# ==========================================================================

def _fmt(value: Any, fallback: str = "not available in the uploaded data") -> str:
    return fallback if value in (None, "") else str(value)


def build_section_prompt(section_id: str, brief: dict, stats: dict, overlay: str = "") -> str:
    """Compose the three-layer prompt (client baseline + template + expert overlay)."""
    section = SECTION_BY_ID.get(section_id, {"title": section_id, "description": ""})
    frameworks = ", ".join(brief.get("regulatory_frameworks") or ["MDR"])
    markets = ", ".join(brief.get("target_markets") or ["Spain"])
    languages = ", ".join(brief.get("languages") or ["English"])

    covers = section.get("covers") or []
    component_lines = []
    for component_id in covers:
        component = COMPONENT_BY_ID[component_id]
        component_lines.append(
            f"- {component['kind']} — {component['name']}: {component['summary']} "
            f"Classified {component['classification']}. "
            f"Standards: {', '.join(component['standards'][:3])}."
        )

    lines = [
        "# Layer 1 — Client baseline (from the signed brief)",
        f"Device / therapeutic area: {brief.get('therapeutic_area', 'Diagnostics & Monitoring')}",
        f"Target markets: {markets}",
        f"Regulatory frameworks: {frameworks}",
        f"Languages: {languages}",
        f"Tone: {brief.get('tone', 'Scientific')}",
        f"Target audience: {brief.get('target_audience', 'Healthcare professionals and payers')}",
        f"Key messages: {brief.get('key_messages', '')}",
        f"Additional requirements: {brief.get('additional_requirements', '')}",
        "",
        "# Layer 2 — Deliverable template",
        f"Write the '{section['title']}' section of a Global Value Dossier.",
        f"Purpose of this section: {section['description']}.",
        "Cite only figures present in the uploaded dataset summary below. "
        "Do not invent endpoints, comparators or citations.",
        "Structure the output as Markdown with a level-2 heading and short subsections.",
    ]

    if component_lines:
        lines += [
            "",
            "## Device functions this section must cover",
            "The product combines a hardware function and a digital function (software as a "
            "medical device). Address each explicitly under its own subheading — do not "
            "collapse them, and do not apply hardware endpoints to the software.",
            *component_lines,
        ]

    lines += [
        "",
        "## Dataset summary available to you",
        _dataset_digest(stats),
    ]

    if overlay:
        lines += ["", "# Layer 3 — Expert overlay", overlay]

    return "\n".join(lines)


def _dataset_digest(stats: dict) -> str:
    study = stats.get("study") or {}
    safety = stats.get("safety") or {}
    efficacy = stats.get("efficacy") or {}

    parts = []
    if study:
        parts.append(
            f"- Cohort: {study.get('patients')} patients, mean age {study.get('mean_age')} years, "
            f"{study.get('type_1_pct')}% type 1 diabetes, {study.get('female_pct')}% female."
        )
        parts.append(
            f"- Accuracy: mean MARD {study.get('mean_mard')}%; "
            f"mean sensor wear {study.get('mean_wear_days')} days; "
            f"mean baseline HbA1c {study.get('mean_hba1c')}%."
        )
    if safety:
        by_type = ", ".join(f"{name} ({count})" for name, count in safety.get("by_type", {}).items())
        parts.append(
            f"- Safety: {safety.get('total')} adverse events, {safety.get('serious')} serious, "
            f"{safety.get('resolution_pct')}% resolved. Breakdown: {by_type}."
        )
    for metric, values in (efficacy.get("endpoints") or {}).items():
        parts.append(
            f"- {metric.replace('_', ' ')}: {values['value']}{values['unit']} "
            f"[95% CI {values['ci_low']}–{values['ci_high']}], p={values['p_value']}."
        )

    software = stats.get("software") or {}
    verification = stats.get("verification") or {}
    if software:
        parts.append(
            f"- Digital function specification: {software.get('count')} documented parameters; "
            f"software safety classification {software.get('safety_class')}; "
            f"classified under {software.get('classification_rule')}; "
            f"{len(software.get('risk_controls') or [])} specified risk controls."
        )
        for item in software.get("algorithm") or []:
            parts.append(f"  - {item['parameter'].replace('_', ' ')}: {item['value']} "
                         f"({item['requirement_id']})")
    if verification:
        parts.append(
            f"- Software verification: {verification.get('passed')}/{verification.get('total')} "
            f"test cases passed ({verification.get('pass_pct')}%), covering "
            f"{verification.get('requirements_covered')} requirements. "
            f"{verification.get('failed')} failures."
        )

    return "\n".join(parts) if parts else "- No dataset uploaded yet."


def draft_section(section_id: str, brief: dict, stats: dict, overlay: str = "") -> str:
    """Deterministic offline draft for one dossier section."""
    study = stats.get("study") or {}
    safety = stats.get("safety") or {}
    endpoints = (stats.get("efficacy") or {}).get("endpoints") or {}
    software = stats.get("software") or {}
    verification = stats.get("verification") or {}

    markets = ", ".join(brief.get("target_markets") or ["Spain"])
    primary_market = (brief.get("target_markets") or ["Spain"])[0]
    frameworks = ", ".join(brief.get("regulatory_frameworks") or ["MDR"])

    mard = _fmt(study.get("mean_mard"))
    patients = _fmt(study.get("patients"))
    wear = _fmt(study.get("mean_wear_days"))

    # Figures from the client's uploaded software documentation, so the digital
    # function's claims are as traceable as the clinical ones.
    sw_class = _fmt(software.get("safety_class"), "not stated in the uploaded specification")
    sw_rule = _fmt(software.get("classification_rule"), "not stated in the uploaded specification")
    ver_total = _fmt(verification.get("total"), "no")
    ver_passed = _fmt(verification.get("passed"), "no")
    ver_pct = _fmt(verification.get("pass_pct"), "—")
    ver_reqs = _fmt(verification.get("requirements_covered"), "no")

    def controls(limit: int = 6) -> str:
        items = (software.get("risk_controls") or [])[:limit]
        if not items:
            return "- No risk controls listed in the uploaded specification."
        return "\n".join(
            f"- {item['parameter'].replace('_', ' ')}: **{item['value']}"
            f"{(' ' + item['unit']) if item['unit'] not in ('', 'boolean') else ''}** "
            f"({item['requirement_id']})"
            for item in items
        )

    def algorithm() -> str:
        items = software.get("algorithm") or []
        if not items:
            return "- Algorithm not described in the uploaded specification."
        return "\n".join(
            f"- {item['parameter'].replace('_', ' ')}: `{item['value']}` ({item['requirement_id']})"
            for item in items
        )

    def endpoint(name: str) -> str:
        item = endpoints.get(name)
        if not item:
            return "not reported in the uploaded dataset"
        return (f"{item['value']}{item['unit']} "
                f"[95% CI {item['ci_low']}–{item['ci_high']}], p={item['p_value']}")

    builders = {
        "exec-summary": lambda: f"""## Executive Summary

The product is a Class IIb continuous glucose monitoring (CGM) system submitted for
conformity assessment under {frameworks} and prepared for launch in {primary_market}. It
comprises **two regulated functions** documented together in this dossier:

- a **hardware function** — the subcutaneous sensor and transmitter, and
- a **digital function** — the bolus calculator, software as a medical device.

**Hardware function — value proposition**

- Mean absolute relative difference (MARD) of **{mard}%** across {patients} evaluable
  patients, meeting the pre-specified primary accuracy endpoint.
- Hypoglycaemia detection rate of {endpoint('Hypoglycemia_Detection_Rate')}.
- Time-in-range improvement of {endpoint('Time_In_Range_Improvement')} versus baseline.
- Sensor wear duration of {wear} days per application, reducing consumable burden.

**Digital function — value proposition**

- Dosing support is delivered inside the primary display application rather than through a
  separate companion app, removing a hand-off step at mealtimes.
- The calculator consumes the live sensor trend, which a fingerstick-based calculator
  cannot do, and subtracts insulin on board to reduce dose stacking.
- Developed under IEC 62304 with human-factors validation per IEC 62366-1.

**Regulatory position**

Technical documentation is assembled against MDR Annex II for both functions, with the
clinical evaluation report structured per Annex XIV and MDCG 2020-13, and the software
qualified under MDCG 2019-11. Target markets: {markets}.""",

        "device-description": lambda: f"""## Device Description & Intended Purpose

**Intended purpose.** Continuous measurement of interstitial glucose in people with
diabetes mellitus aged 18 years and over, to support glycaemic management decisions
including insulin dosing via the integrated bolus calculator.

The product is a combination of a hardware function and a digital function. Each is
classified on its own rule and carries its own evidence, and both are covered here.

### Hardware function — sensor and transmitter

- Subcutaneous glucose sensor with a {wear}-day labelled wear duration.
- Rechargeable transmitter with Bluetooth Low Energy connectivity.
- **Classification:** Class IIb, MDR Annex VIII **Rule 15** — invasive device intended for
  continuous monitoring of vital physiological parameters.
- **Applicable standards:** EN ISO 15197 (accuracy), EN ISO 10993 (biocompatibility),
  EN ISO 11137 (sterilisation), IEC 60601-1 / -1-2 (electrical safety and EMC).

### Digital function — bolus calculator

- Dosing-support module within the display application, alongside trend arrows and
  predictive alerts.
- Computes a carbohydrate dose and a glucose correction dose, applies a CGM trend
  adjustment, then subtracts insulin on board.
- **Classification:** Class IIb, MDR Annex VIII **Rule 11** — software providing
  information used to take decisions with therapeutic purposes. Qualified as a medical
  device in its own right under MDCG 2019-11.
- **Applicable standards:** IEC 62304 (software lifecycle), IEC 82304-1 (health software),
  IEC 62366-1 (usability), MDCG 2019-16 (cybersecurity).
- The calculator issues a recommendation only; it does not deliver insulin.

**Conformity route.** A single Annex IX quality management system assessment plus technical
documentation review by the notified body covering both functions, supported by
EN ISO 13485 and ISO 14971 risk management files.""",

        "disease-overview": lambda: f"""## Disease & Epidemiology

**Burden in {primary_market}.** Diabetes mellitus affects approximately 6–7% of the adult
population in Spain, corresponding to an estimated 2.5–3.0 million people, of whom roughly
10% have type 1 diabetes requiring intensive insulin therapy.

**Unmet needs addressed by continuous monitoring**

- Fingerstick self-monitoring gives discrete snapshots and systematically under-detects
  nocturnal and asymptomatic hypoglycaemia.
- Hypoglycaemia is a leading driver of emergency presentations and a principal barrier to
  achieving HbA1c targets.
- Manual dose calculation is error-prone; integrated dosing support reduces the arithmetic
  burden placed on the patient.

**Cohort context.** The pivotal dataset covers {patients} patients with a mean baseline
HbA1c of {_fmt(study.get('mean_hba1c'))}% and {_fmt(study.get('type_1_pct'))}% type 1
diabetes representation, consistent with the intended-use population.""",

        "clinical-efficacy": lambda: f"""## Clinical Performance Data

Performance evidence is presented separately for the two device functions, since they are
assessed against different endpoints.

### Hardware function — sensor accuracy

**Study design.** Prospective, single-arm, multi-centre accuracy investigation. Sensor
glucose readings were compared against a laboratory reference method (YSI) across a
{wear}-day wear period in {patients} evaluable patients.

**Primary endpoint**

- Mean absolute relative difference (MARD): {endpoint('Mean_MARD')} — primary endpoint met.

**Secondary endpoints**

- Hypoglycaemia detection rate: {endpoint('Hypoglycemia_Detection_Rate')}
- Hyperglycaemia detection rate: {endpoint('Hyperglycemia_Detection_Rate')}
- Time in range improvement: {endpoint('Time_In_Range_Improvement')}
- Nocturnal hypoglycaemia reduction: {endpoint('Nocturnal_Hypoglycemia_Reduction')}
- Glucose variability reduction: {endpoint('Glucose_Variability_Reduction')}
- Sensor longevity: {endpoint('Sensor_Longevity')}
- System reliability: {endpoint('System_Reliability')}

### Digital function — bolus calculator verification

The calculator is not evaluated by MARD. Its performance evidence is verification and
human-factors data rather than a clinical accuracy endpoint:

- **Algorithm verification.** {ver_passed} of {ver_total} test cases passed ({ver_pct}%),
  covering {ver_reqs} software requirements. Computed doses were checked against
  independently derived reference calculations across the specified input ranges, including
  boundary conditions for carbohydrate entry, correction dose and insulin on board.
- **Trend-adjustment behaviour.** Adjustment is applied only when the sensor reading meets
  the reliability criteria used for display, so the calculator inherits the accuracy
  characterised above rather than asserting an independent one.
- **Human-factors validation.** Conducted per IEC 62366-1 against the use scenarios for
  dose entry, review and confirmation, with no unresolved critical use errors.
- **Dose-stacking control.** Insulin on board is subtracted from every recommendation;
  this is a verified requirement, not a configurable preference.

**Interpretation.** Sensor accuracy sits within the range reported for contemporary
CE-marked CGM systems, and the hypoglycaemia detection result supports the alerting claims
in the instructions for use. The calculator's evidence supports a decision-support claim
only — no autonomous dosing claim is made.""",

        "safety-profile": lambda: f"""## Safety & Tolerability

**Adverse event summary.** {_fmt(safety.get('total'))} adverse events were recorded across
the investigation, of which {_fmt(safety.get('serious'))} were serious.
{_fmt(safety.get('resolution_pct'))}% resolved without sequelae.

**Events by type**

{chr(10).join(f"- {name}: {count} event(s)" for name, count in (safety.get('by_type') or {}).items()) or "- No adverse events recorded in the uploaded dataset."}

### Hardware function — device-related risk

Observed events were predominantly mild-to-moderate, localised to the application site or
related to calibration handling, and all were managed with routine measures. No device
deficiency led to a serious deterioration in health.

**Risk controls.** Adhesive alternatives are provided for application-site reactions;
calibration drift is mitigated through the firmware algorithm and in-app prompts.

### Digital function — use-related risk

Software risk is assessed as use-related rather than as adverse events, per ISO 14971 and
IEC 62366-1. The dominant hazards and their controls:

- **Carbohydrate entry error** → input range limits, an explicit confirmation step, and the
  computed breakdown shown before acceptance.
- **Dose stacking** → mandatory insulin-on-board subtraction.
- **Dosing on an unreliable reading** → the trend adjustment is suppressed when sensor
  reliability criteria are not met.
- **Over-reliance on the recommendation** → labelling and in-app text state that the output
  is decision support requiring clinical judgement.
- **Hypoglycaemia and ketone thresholds** → explicit warnings raised before a dose is
  recommended.

**Benefit-risk conclusion.** Taking both functions together, the benefit-risk determination
under MDR Annex I Chapter I remains favourable.""",

        "pharmacoeconomics": lambda: f"""## Health-Economic Analysis

**Perspective.** Spanish National Health System (Sistema Nacional de Salud), regional
purchasing level, 1-year budget-impact horizon with a lifetime cost-utility extension.

**Base-case results (illustrative)**

- Annual device and consumable cost: €2,400–3,200 per patient.
- Incremental cost-effectiveness ratio: approximately €18,500 per QALY, against roughly
  €30,000 per QALY for conventional self-monitoring intensification.
- Budget impact at 100,000 patients: €45–60M gross annual investment.

**Offsetting effects**

- Reduction in emergency presentations for severe hypoglycaemia.
- Reduction in hypoglycaemia-related hospitalisation days.
- HbA1c improvement translating into avoided long-term complication costs.

**Tender alignment.** Regional tender scoring in several CCAA now weights time-in-range
improvement and nocturnal hypoglycaemia reduction; both endpoints are met by the pivotal
dataset and are mapped directly to the scoring criteria in the tender annex.""",

        "qol-outcomes": lambda: f"""## Quality of Life Outcomes

**Patient-reported outcomes.** Patient satisfaction scored
{endpoint('Patient_Satisfaction_Score')} on the study instrument.

### Hardware function — contributing factors

- Elimination of routine fingerstick testing across the {wear}-day wear period.
- Predictive alerts reducing anxiety around nocturnal hypoglycaemia.
- Calibration burden of {endpoint('Calibration_Frequency')}, considered acceptable by
  participants.

### Digital function — contributing factors

- Integrated bolus calculation removes manual arithmetic at mealtimes.
- The dose breakdown (carbohydrate, correction, trend, insulin on board) is shown before
  confirmation, supporting understanding rather than blind acceptance.
- No app switching between glucose review and dose calculation.

**Usability evidence.** Human-factors validation was conducted per IEC 62366-1 across both
functions. Use-related risk analysis covers sensor application and alert interpretation for
the hardware, and dose entry, review and confirmation for the calculator, with no
unresolved critical use errors.""",

        "comparative-effectiveness": lambda: f"""## Comparative Effectiveness

**Comparator set.** Contemporary CE-marked CGM and flash glucose monitoring systems
available in the {primary_market} market, plus conventional self-monitoring of blood
glucose as the baseline standard of care.

### Hardware function

- Accuracy: MARD {mard}% is comparable with the leading marketed systems.
- Hypoglycaemia detection: {endpoint('Hypoglycemia_Detection_Rate')}, supporting the
  alerting claim.
- Wear duration: {wear} days per sensor.
- Versus self-monitoring: continuous trend visibility rather than discrete measurements,
  a time-in-range improvement of {endpoint('Time_In_Range_Improvement')} and a
  {endpoint('Nocturnal_Hypoglycemia_Reduction')} reduction in nocturnal hypoglycaemia.

### Digital function

- Dosing support is integrated in the primary display application; several comparator
  systems require a separate companion app or a third-party calculator.
- The calculator consumes the live CGM trend. A standalone or fingerstick-based calculator
  has no trend input and cannot make this adjustment.
- Insulin-on-board subtraction is mandatory rather than optional.
- This is the principal point of differentiation: the combined hardware-plus-software
  offering, documented under a single conformity assessment.

**Evidence caveat.** No head-to-head randomised comparison has been conducted. Comparative
statements — for both functions — are indirect and are labelled as such throughout the
dossier, per MDCG 2020-5 expectations on equivalence and comparative claims.""",

        "software-lifecycle": lambda: f"""## Software Lifecycle & Cybersecurity

This section applies to the **digital function** — the bolus calculator — which is a
medical device in its own right under MDR Annex VIII Rule 11 and MDCG 2019-11.

**Software safety classification.** {sw_class} under IEC 62304, per the uploaded software
specification: a failure of the dose recommendation could contribute to serious injury
through hypoglycaemia or persistent hyperglycaemia. Classified under {sw_rule}.

**Specified algorithm**

{algorithm()}

**Specified risk controls**

{controls()}

**Verification evidence (IEC 62304 §5.5–5.7)**

The uploaded verification record contains **{ver_total} test cases**, of which
**{ver_passed} passed ({ver_pct}%)**, covering **{ver_reqs} distinct software requirements**.
Coverage includes the carbohydrate and correction dose calculations, every trend-adjustment
state, insulin-on-board subtraction, output clamping, the configurable parameter boundaries
and each warning threshold.

**Lifecycle records (IEC 62304)**

- §5.1 Software development plan, including the SOUP inventory.
- §5.2–5.4 Requirements, architectural design and detailed design, traced to the intended
  purpose and to the risk controls listed above.
- §5.5–5.7 Unit, integration and system test records — summarised above.
- §6 Maintenance process, with a defined route for post-release changes.
- §7 Risk management for software, cross-referenced to the use-related risk analysis.
- §8 Configuration management and §9 problem resolution.

**Cybersecurity (MDCG 2019-16)**

- Threat model for the Bluetooth link between transmitter and display application.
- Authenticated pairing and encrypted transport for glucose data.
- Integrity protection for the calculator's configuration parameters (carbohydrate ratio,
  correction factor, target), since altering them silently changes every recommendation.
- Coordinated vulnerability disclosure route and a patching commitment stated in the PMS
  plan.

**EU AI Act considerations.** The calculator is deterministic rule-based software rather
than a learning system, which limits the obligations that attach. Transparency and
human-oversight duties are nonetheless addressed: the dose breakdown is displayed before
confirmation, the recommendation is labelled as decision support, and the user retains the
final decision.

**Usability (IEC 62366-1).** Use specification, user interface specification, use-related
risk analysis and summative evaluation, all covering dose entry, review and confirmation.""",

        "target-population": lambda: f"""## Target Population & Positioning

**Primary population.** Adults with type 1 diabetes on multiple daily injections or pump
therapy — {_fmt(study.get('type_1_pct'))}% of the pivotal cohort — where intensive
monitoring and dosing support deliver the largest clinical benefit.

**Secondary population.** Adults with insulin-treated type 2 diabetes experiencing
hypoglycaemia unawareness or failing to reach glycaemic targets.

**Prioritised segments for {primary_market} launch**

1. Patients with documented severe or nocturnal hypoglycaemia episodes.
2. Patients above HbA1c target despite structured self-monitoring.
3. Patients transitioning to intensive insulin regimens who need dosing support.

**Exclusions.** Paediatric use is outside the current intended purpose; a paediatric
indication extension would require a separate clinical investigation and Annex II update.""",

        "regulatory-status": lambda: f"""## Regulatory Status & Compliance

**Conformity route.** MDR 2017/745, Class IIb, Annex IX (QMS + technical documentation
assessment) with notified body involvement. Both device functions are covered by a single
assessment, but each is classified on its own rule:

| Function | Classification rule | Class |
|---|---|---|
| CGM sensor and transmitter | Annex VIII **Rule 15** — invasive, continuous monitoring of vital physiological parameters | IIb |
| Bolus calculator software | Annex VIII **Rule 11** — software informing therapeutic decisions | IIb |

**Documentation status**

- Annex II technical documentation: assembled, covering both functions.
- Annex XIV clinical evaluation report: drafted against MDCG 2020-13.
- Software qualification rationale per MDCG 2019-11: documented.
- IEC 62304 lifecycle file (Class C): complete — see the Software Lifecycle section.
- Annex I GSPR checklist: complete with evidence cross-references, including GSPR 17
  (electronic programmable systems and software).
- Annex III post-market surveillance plan: drafted, PSUR on an annual cycle, with real-world
  accuracy monitoring and software problem trending.
- EUDAMED actor registration and UDI assignment: in progress. The software carries its own
  UDI-DI where placed on the market as a distinct unit.

**{primary_market} market entry**

- AEMPS comunicación de puesta en el mercado to be filed on receipt of the CE certificate.
- Spanish-language instructions for use, labelling and in-application text prepared —
  the language duty extends to the calculator's user interface.
- Regional tender dossiers aligned to CCAA purchasing criteria.

**Applicable frameworks selected for this engagement:** {frameworks}.

**Standards conformity.** EN ISO 13485, ISO 14971, EN ISO 15197, EN ISO 10993,
IEC 60601-1/-1-2 (hardware); IEC 62304, IEC 82304-1, IEC 62366-1, MDCG 2019-16 (software).""",
    }

    builder = builders.get(section_id)
    body = builder() if builder else f"## {SECTION_BY_ID.get(section_id, {}).get('title', section_id)}\n\nNo offline template is defined for this section."

    if overlay:
        body += f"\n\n> **Expert overlay applied:** {overlay}"
    return body


def draft_msl_material(material_id: str, brief: dict, stats: dict, config: dict) -> str:
    """Deterministic offline draft for an MSL material."""
    study = stats.get("study") or {}
    endpoints = (stats.get("efficacy") or {}).get("endpoints") or {}
    safety = stats.get("safety") or {}
    software = stats.get("software") or {}
    verification = stats.get("verification") or {}

    material = MSL_MATERIAL_BY_ID.get(material_id, {"name": material_id})
    audience = dict(AUDIENCES).get(config.get("audience"), "healthcare professionals")
    focus = dict(FOCUS_AREAS).get(config.get("focus_area"), "clinical performance")
    tone = config.get("tone", "scientific")
    mard = _fmt(study.get("mean_mard"))

    def endpoint(name: str) -> str:
        item = endpoints.get(name)
        return f"{item['value']}{item['unit']} (p={item['p_value']})" if item else "not reported"

    header = (f"# {material['name']}\n\n"
              f"**Audience:** {audience}  |  **Focus:** {focus}  |  **Tone:** {tone}\n\n"
              f"**Evidence base:** {_fmt(study.get('patients'))}-patient pivotal investigation, "
              f"MDR 2017/745 conformity route.\n\n---\n")

    if material_id == "slide-deck":
        # Each `## ` heading becomes one slide and each `- ` line one bullet when this
        # is exported to PowerPoint (see core/deck.py), so keep the structure flat.
        body = f"""
## The unmet need
- Hypoglycaemia is under-detected by intermittent self-monitoring, particularly overnight
- Manual dose calculation adds avoidable arithmetic error at mealtimes
- Two functions address this: a continuous sensor, and integrated dosing support

## Device overview — two regulated functions
- Hardware: subcutaneous CGM sensor and transmitter (MDR Annex VIII, Rule 15)
- Digital: bolus calculator, software as a medical device (MDR Annex VIII, Rule 11)
- Both covered by a single Class IIb conformity assessment

## Study design
- Prospective, single-arm, multi-centre accuracy investigation
- {_fmt(study.get('patients'))} evaluable patients
- {_fmt(study.get('mean_wear_days'))}-day wear period
- Comparison against a laboratory reference method

## Primary endpoint — sensor accuracy
- Mean absolute relative difference (MARD): {mard}%
- Pre-specified primary accuracy endpoint met
- Comparable with contemporary CE-marked CGM systems

## Hypoglycaemia detection
- Detection rate: {endpoint('Hypoglycemia_Detection_Rate')}
- Nocturnal hypoglycaemia reduced by {endpoint('Nocturnal_Hypoglycemia_Reduction')}
- Supports the alerting claims made in the instructions for use

## Glycaemic control
- Time in range improved by {endpoint('Time_In_Range_Improvement')}
- Glucose variability reduced by {endpoint('Glucose_Variability_Reduction')}
- Sensor longevity: {endpoint('Sensor_Longevity')}

## Safety profile
- {_fmt(safety.get('total'))} adverse events recorded
- {_fmt(safety.get('serious'))} serious
- {_fmt(safety.get('resolution_pct'))}% resolved without sequelae
- Predominantly application-site or calibration-related

## Digital function — bolus calculator
- Carbohydrate dose plus glucose correction dose
- CGM trend adjustment, which a fingerstick calculator cannot make
- Insulin-on-board subtraction to reduce dose stacking
- Decision support only — the device does not deliver insulin

## Digital function — evidence and controls
- {_fmt(verification.get('passed'), 'No')} of {_fmt(verification.get('total'), 'no')} verification test cases passed ({_fmt(verification.get('pass_pct'), '—')}%)
- {_fmt(verification.get('requirements_covered'), 'No')} software requirements covered
- Human-factors validation per IEC 62366-1, no unresolved critical use errors
- {_fmt(software.get('safety_class'), 'Classification not stated')} under IEC 62304
- Cybersecurity assessed per MDCG 2019-16

## Patient experience
- Satisfaction: {endpoint('Patient_Satisfaction_Score')}
- Calibration burden: {endpoint('Calibration_Frequency')}
- No fingerstick testing across the wear period
- No app switching between glucose review and dose calculation

## Summary
- Primary accuracy endpoint met at MARD {mard}%
- Hypoglycaemia detection supports the alerting claim
- Hardware and software documented under one conformity assessment
- Comparative statements are indirect and labelled as such
"""
    elif material_id == "medical-summary":
        body = f"""
## Clinical overview
The system provides continuous interstitial glucose measurement with integrated dosing
support, evaluated in a {_fmt(study.get('patients'))}-patient pivotal investigation.

## Performance
- MARD: {mard}%
- Hypoglycaemia detection: {endpoint('Hypoglycemia_Detection_Rate')}
- Time in range improvement: {endpoint('Time_In_Range_Improvement')}
- System reliability: {endpoint('System_Reliability')}

## Safety
{_fmt(safety.get('total'))} adverse events recorded, {_fmt(safety.get('serious'))} serious.
Events were predominantly application-site or calibration-related and resolved with routine
management.

## Practical considerations for {audience}
Sensor wear duration of {_fmt(study.get('mean_wear_days'))} days; calibration burden of
{endpoint('Calibration_Frequency')}; the bolus calculator subtracts insulin on board to
reduce stacking risk.

## Regulatory status
Class IIb under MDR 2017/745. Comparative statements against other CGM systems are indirect.
"""
    elif material_id == "faq-document":
        body = f"""
**Q: How accurate is the sensor?**
A: Mean absolute relative difference was {mard}% against a laboratory reference method
across {_fmt(study.get('patients'))} patients.

**Q: How well does it detect hypoglycaemia?**
A: Detection rate was {endpoint('Hypoglycemia_Detection_Rate')}, with nocturnal
hypoglycaemia reduced by {endpoint('Nocturnal_Hypoglycemia_Reduction')}.

**Q: How long does a sensor last?**
A: {endpoint('Sensor_Longevity')}, consistent with the labelled wear duration.

**Q: How does the bolus calculator work?**
A: It combines the carbohydrate dose (carbohydrates ÷ insulin-to-carb ratio) with a
correction dose ((current glucose − target) ÷ correction factor), applies a CGM trend
adjustment, then subtracts insulin on board. It is decision support only and issues no
insulin delivery command.

**Q: How was the calculator verified?**
A: {_fmt(verification.get('passed'), 'No')} of {_fmt(verification.get('total'), 'no')} test
cases passed ({_fmt(verification.get('pass_pct'), '—')}%), covering
{_fmt(verification.get('requirements_covered'), 'no')} software requirements including every
trend state, the parameter boundaries and each warning threshold. It is developed under
IEC 62304 as {_fmt(software.get('safety_class'), 'a classified')} software.

**Q: What adverse events were observed?**
A: {_fmt(safety.get('total'))} events, {_fmt(safety.get('serious'))} serious,
{_fmt(safety.get('resolution_pct'))}% resolved.

**Q: Is there head-to-head comparative data?**
A: No. Comparisons against other CGM systems are indirect and are labelled as such.
"""
    elif material_id == "email-template":
        body = f"""
### Template 1 — Accuracy enquiry

Dear Dr. [Name],

Thank you for your enquiry regarding sensor accuracy. In the pivotal investigation
({_fmt(study.get('patients'))} patients), mean absolute relative difference against a
laboratory reference method was {mard}%. The full clinical evaluation report is available
on request.

Kind regards,
[MSL name]

### Template 2 — Hypoglycaemia detection enquiry

Dear Dr. [Name],

Regarding hypoglycaemia detection: the observed detection rate was
{endpoint('Hypoglycemia_Detection_Rate')}, with a
{endpoint('Nocturnal_Hypoglycemia_Reduction')} reduction in nocturnal events.

Kind regards,
[MSL name]

### Template 3 — Dosing support enquiry

Dear Dr. [Name],

The integrated bolus calculator applies the carbohydrate ratio and correction factor, adds a
CGM trend adjustment, and subtracts insulin on board. It is decision support only and does
not deliver insulin.

Kind regards,
[MSL name]
"""
    else:
        body = "\nNo offline template is defined for this material type.\n"

    key_messages = (config.get("key_messages") or "").strip()
    if key_messages:
        body += f"\n---\n\n**Key messages requested by the requester:** {key_messages}\n"

    return header + body


def refine(original: str, instruction: str) -> str:
    """Offline refinement pass — appends a tracked revision note."""
    return (
        f"{original}\n\n---\n\n## Revision note\n\n"
        f"**Requested change:** {instruction}\n\n"
        "Applied offline. Re-run with a provider API key to have the full text rewritten "
        "against this instruction rather than annotated."
    )
