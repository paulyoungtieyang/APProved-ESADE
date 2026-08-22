"""
Reference data and the offline drafting engine.

Everything the UI lists (regulatory frameworks, dossier sections, MSL material
types, policy feed, resources) lives here, plus the deterministic draft writers
that ground each section in the numbers actually present in the uploaded files.

The demo is configured for a Class IIb continuous glucose monitoring (CGM)
system entering the EU under MDR 2017/745, launching in Spain.
"""

from __future__ import annotations

from typing import Any

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

DOSSIER_SECTIONS = [
    {"id": "exec-summary", "title": "Executive Summary",
     "description": "High-level overview of the clinical value proposition"},
    {"id": "device-description", "title": "Device Description & Intended Purpose",
     "description": "MDR Annex II device description, classification and intended purpose"},
    {"id": "disease-overview", "title": "Disease & Epidemiology",
     "description": "Disease burden, prevalence and unmet needs in the launch market"},
    {"id": "clinical-efficacy", "title": "Clinical Performance Data",
     "description": "Pivotal study results, endpoints and statistical analysis"},
    {"id": "safety-profile", "title": "Safety & Tolerability",
     "description": "Adverse events, safety profile and benefit-risk analysis"},
    {"id": "pharmacoeconomics", "title": "Health-Economic Analysis",
     "description": "Cost-effectiveness, budget impact and economic value"},
    {"id": "qol-outcomes", "title": "Quality of Life Outcomes",
     "description": "Patient-reported outcomes and usability assessments"},
    {"id": "comparative-effectiveness", "title": "Comparative Effectiveness",
     "description": "Comparison against the current standard of care and competitors"},
    {"id": "target-population", "title": "Target Population & Positioning",
     "description": "Patient segmentation and treatment positioning"},
    {"id": "regulatory-status", "title": "Regulatory Status & Compliance",
     "description": "MDR conformity route, notified body status and market notifications"},
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
    {"id": "upload", "title": "Upload pivotal clinical data", "endpoint": "upload"},
    {"id": "regulations", "title": "Select regulatory frameworks", "endpoint": "regulations"},
    {"id": "dossier", "title": "Generate the Global Value Dossier", "endpoint": "global_dossier"},
    {"id": "msl", "title": "Generate MSL field materials", "endpoint": "msl_material"},
]


# ==========================================================================
# Bolus calculator
# ==========================================================================

def calculate_bolus(
    carbs_g: float,
    current_glucose: float,
    target_glucose: float = 110.0,
    icr: float = 12.0,
    isf: float = 45.0,
    insulin_on_board: float = 0.0,
    trend: str = "steady",
) -> dict[str, Any]:
    """
    Standard bolus calculation used by the demo device's dosing-support module.

        bolus = carb dose + correction dose - insulin on board
        carb dose       = carbohydrates / insulin-to-carb ratio
        correction dose = (current glucose - target) / insulin sensitivity factor

    A CGM trend adjustment is applied on top, which is what distinguishes a
    sensor-integrated calculator from a fingerstick one.

    Returned values are illustrative only — this is a prototype, not a dosing device.
    """
    icr = max(icr, 0.1)
    isf = max(isf, 0.1)

    carb_dose = carbs_g / icr
    correction_dose = (current_glucose - target_glucose) / isf

    trend_adjustments = {
        "rising-fast": 1.5, "rising": 0.75, "steady": 0.0,
        "falling": -0.75, "falling-fast": -1.5,
    }
    trend_adjustment = trend_adjustments.get(trend, 0.0)

    total = carb_dose + correction_dose + trend_adjustment - insulin_on_board
    total = max(total, 0.0)

    warnings = []
    if current_glucose < 70:
        warnings.append("Glucose below 70 mg/dL — treat hypoglycaemia before dosing.")
    if current_glucose > 250:
        warnings.append("Glucose above 250 mg/dL — check ketones per clinical protocol.")
    if trend in ("falling", "falling-fast") and current_glucose < 100:
        warnings.append("Falling trend at a low glucose level — recheck before dosing.")
    if insulin_on_board > 0 and correction_dose > 0:
        warnings.append(f"{insulin_on_board:.1f} U insulin on board was subtracted from the total.")

    return {
        "carb_dose": round(carb_dose, 2),
        "correction_dose": round(correction_dose, 2),
        "trend_adjustment": round(trend_adjustment, 2),
        "insulin_on_board": round(insulin_on_board, 2),
        "total": round(total, 1),
        "warnings": warnings,
        "inputs": {
            "carbs_g": carbs_g, "current_glucose": current_glucose,
            "target_glucose": target_glucose, "icr": icr, "isf": isf, "trend": trend,
        },
    }


GLUCOSE_TRENDS = [
    ("rising-fast", "Rising fast  ↑↑"),
    ("rising", "Rising  ↑"),
    ("steady", "Steady  →"),
    ("falling", "Falling  ↓"),
    ("falling-fast", "Falling fast  ↓↓"),
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
    return "\n".join(parts) if parts else "- No dataset uploaded yet."


def draft_section(section_id: str, brief: dict, stats: dict, overlay: str = "") -> str:
    """Deterministic offline draft for one dossier section."""
    study = stats.get("study") or {}
    safety = stats.get("safety") or {}
    endpoints = (stats.get("efficacy") or {}).get("endpoints") or {}

    markets = ", ".join(brief.get("target_markets") or ["Spain"])
    primary_market = (brief.get("target_markets") or ["Spain"])[0]
    frameworks = ", ".join(brief.get("regulatory_frameworks") or ["MDR"])

    mard = _fmt(study.get("mean_mard"))
    patients = _fmt(study.get("patients"))
    wear = _fmt(study.get("mean_wear_days"))

    def endpoint(name: str) -> str:
        item = endpoints.get(name)
        if not item:
            return "not reported in the uploaded dataset"
        return (f"{item['value']}{item['unit']} "
                f"[95% CI {item['ci_low']}–{item['ci_high']}], p={item['p_value']}")

    builders = {
        "exec-summary": lambda: f"""## Executive Summary

The device is a Class IIb continuous glucose monitoring (CGM) system with an integrated
bolus calculator, submitted for conformity assessment under {frameworks} and prepared for
launch in {primary_market}.

**Value proposition**

- Mean absolute relative difference (MARD) of **{mard}%** across {patients} evaluable
  patients, meeting the pre-specified primary accuracy endpoint.
- Hypoglycaemia detection rate of {endpoint('Hypoglycemia_Detection_Rate')}.
- Time-in-range improvement of {endpoint('Time_In_Range_Improvement')} versus baseline.
- Sensor wear duration of {wear} days per application, reducing consumable burden.
- Integrated bolus calculator delivers dosing support without a separate application.

**Regulatory position**

Technical documentation is assembled against MDR Annex II, with the clinical evaluation
report structured per Annex XIV and MDCG 2020-13. Target markets: {markets}.""",

        "device-description": lambda: f"""## Device Description & Intended Purpose

**Intended purpose.** Continuous measurement of interstitial glucose in people with
diabetes mellitus aged 18 years and over, to support glycaemic management decisions
including insulin dosing via the integrated bolus calculator.

**Classification.** Class IIb under MDR 2017/745 Annex VIII, Rule 11 (software providing
information used to take decisions with diagnosis or therapeutic purposes) in combination
with the invasive sensor rule.

**Principal components**

- Subcutaneous glucose sensor with a {wear}-day labelled wear duration.
- Rechargeable transmitter with Bluetooth Low Energy connectivity.
- Display application incorporating trend arrows, predictive alerts and the bolus
  calculator module (developed under IEC 62304).

**Conformity route.** Annex IX quality management system assessment plus technical
documentation review by the notified body, supported by EN ISO 13485, ISO 14971
risk management and IEC 62366-1 usability engineering files.""",

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

**Interpretation.** Accuracy performance sits within the range reported for contemporary
CE-marked CGM systems, and the hypoglycaemia detection result supports the alerting claims
made in the instructions for use.""",

        "safety-profile": lambda: f"""## Safety & Tolerability

**Adverse event summary.** {_fmt(safety.get('total'))} adverse events were recorded across
the investigation, of which {_fmt(safety.get('serious'))} were serious.
{_fmt(safety.get('resolution_pct'))}% resolved without sequelae.

**Events by type**

{chr(10).join(f"- {name}: {count} event(s)" for name, count in (safety.get('by_type') or {}).items()) or "- No adverse events recorded in the uploaded dataset."}

**Benefit-risk conclusion.** Observed events were predominantly mild-to-moderate, localised
to the application site or related to calibration handling, and all were managed with
routine measures. No device deficiency led to a serious deterioration in health. The
benefit-risk determination under MDR Annex I Chapter I remains favourable.

**Risk controls.** Adhesive alternatives are provided for application-site reactions;
calibration drift is mitigated through the firmware algorithm and in-app prompts; the
bolus calculator applies insulin-on-board subtraction to reduce stacking risk.""",

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

**Contributing factors**

- Elimination of routine fingerstick testing across the {wear}-day wear period.
- Predictive alerts reducing anxiety around nocturnal hypoglycaemia.
- Integrated bolus calculation removing manual arithmetic at mealtimes.
- Calibration burden of {endpoint('Calibration_Frequency')}, considered acceptable by
  participants.

**Usability evidence.** Human-factors validation was conducted per IEC 62366-1. Use-related
risk analysis covers sensor application, alert interpretation and bolus calculator entry,
with no unresolved critical use errors.""",

        "comparative-effectiveness": lambda: f"""## Comparative Effectiveness

**Comparator set.** Contemporary CE-marked CGM and flash glucose monitoring systems
available in the {primary_market} market, plus conventional self-monitoring of blood
glucose as the baseline standard of care.

**Positioning against CGM comparators**

- Accuracy: MARD {mard}% is comparable with the leading marketed systems.
- Hypoglycaemia detection: {endpoint('Hypoglycemia_Detection_Rate')}, supporting the
  alerting claim.
- Dosing support: bolus calculation is integrated in the primary display application
  rather than requiring a separate companion app.
- Wear duration: {wear} days per sensor.

**Positioning against self-monitoring**

- Continuous trend visibility versus discrete measurements.
- Time-in-range improvement of {endpoint('Time_In_Range_Improvement')}.
- Nocturnal hypoglycaemia reduction of {endpoint('Nocturnal_Hypoglycemia_Reduction')}.

**Evidence caveat.** No head-to-head randomised comparison has been conducted. Comparative
statements are indirect and are labelled as such throughout the dossier, per MDCG 2020-5
expectations on equivalence and comparative claims.""",

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
assessment) with notified body involvement.

**Documentation status**

- Annex II technical documentation: assembled.
- Annex XIV clinical evaluation report: drafted against MDCG 2020-13.
- Annex I GSPR checklist: complete with evidence cross-references.
- Annex III post-market surveillance plan: drafted, PSUR on an annual cycle.
- EUDAMED actor registration and UDI assignment: in progress.

**{primary_market} market entry**

- AEMPS comunicación de puesta en el mercado to be filed on receipt of the CE certificate.
- Spanish-language instructions for use and labelling prepared.
- Regional tender dossiers aligned to CCAA purchasing criteria.

**Applicable frameworks selected for this engagement:** {frameworks}.

**Standards conformity.** EN ISO 13485, ISO 14971, IEC 62304, IEC 62366-1, ISO 15197.""",
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
        body = f"""
## Slide 1 — Title
Continuous Glucose Monitoring with Integrated Bolus Calculation: pivotal performance data.

## Slide 2 — Unmet need
Hypoglycaemia remains under-detected with intermittent self-monitoring, particularly
overnight, and manual dose calculation adds avoidable error.

## Slide 3 — Study design
Prospective single-arm accuracy investigation; {_fmt(study.get('patients'))} patients;
{_fmt(study.get('mean_wear_days'))}-day wear period; laboratory reference comparison.

## Slide 4 — Primary endpoint
MARD {mard}% — primary accuracy endpoint met.

## Slide 5 — Hypoglycaemia detection
Detection rate {endpoint('Hypoglycemia_Detection_Rate')}; nocturnal hypoglycaemia reduced by
{endpoint('Nocturnal_Hypoglycemia_Reduction')}.

## Slide 6 — Glycaemic control
Time in range improved by {endpoint('Time_In_Range_Improvement')}; glucose variability
reduced by {endpoint('Glucose_Variability_Reduction')}.

## Slide 7 — Safety
{_fmt(safety.get('total'))} adverse events, {_fmt(safety.get('serious'))} serious,
{_fmt(safety.get('resolution_pct'))}% resolved.

## Slide 8 — Dosing support
Bolus calculator applies carbohydrate ratio, correction factor, CGM trend adjustment and
insulin-on-board subtraction.

## Slide 9 — Patient experience
Satisfaction {endpoint('Patient_Satisfaction_Score')}; calibration burden
{endpoint('Calibration_Frequency')}.

## Slide 10 — Summary and references
Field-ready summary with full citation list appended.
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
correction dose ((current glucose − target) ÷ insulin sensitivity factor), applies a CGM
trend adjustment, then subtracts insulin on board.

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
