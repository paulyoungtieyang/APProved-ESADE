# APProved — Prototype Functionality Analysis

Analysis of the updated APProved prototype walkthrough, cross-referenced against the
design-thinking process deck and the Deliverable 2 user-testing findings.

**Sources**

| Source | Notes |
|---|---|
| `Updated APProved Prototype.mp4` | 2:14 screen recording, 2136×1454, **no audio track** — all findings below are read off the screens |
| `Team 3 - Fashion Icons - InClass Deliverable.pdf` | 33 pages, design thinking process (Empathize → Define → Ideate → Test) |
| `Team 3 - Fashion Icons - Deliverable 2 - User Testing.pdf` | 11 pages, 4 user interviews + prototype backlog + value proposition |

---

## 1. Positioning

**APProved — Medical Writing Platform.** In-product tagline: *"Unlocking compliance as
growth."*

Agentic AI that converts Phase III clinical data into regulatory submissions, Global Value
Dossiers, and field-ready medical scientific communication, with human expert review in
the loop.

---

## 2. The ten functional modules

### 2.1 Dashboard — control tower

- **Regulatory Track toggle: Global ↔ Local Affiliate.** Reframes the whole workspace
  ("Focus on global regulatory submissions and compliance"). Lets affiliates skip
  HQ-owned filings entirely.
- **Setup Checklist:** Identify Device Classification → Upload Phase 3 Clinical Data →
  Select Regulatory Frameworks → Configure Brand Guidelines → Set Up Team Permissions.
- **KPI tiles:** Documents Generated (24, +12% MoM) · Active Submissions (3, 2 pending
  review) · **Time Saved (156 hrs this quarter)**.
- **Quick Actions:** Upload Phase 3 Data · Select Regulations · Generate Global Dossier ·
  MSL Materials.
- **Recent Activity** feed with dated entries and status badges.

### 2.2 Upload Phase 3 Data — ingestion

- CSV / XLSX / PDF / DOCX, max 100 MB per file, drag-drop or browse.
- **Accepted data types:** clinical trial efficacy data (CSR, statistical analysis);
  safety and adverse event reports; patient demographics and baseline characteristics;
  pharmacokinetic/pharmacodynamic data; quality of life assessments.
- **Data Privacy & Security Guarantee panel sits above the dropzone:**
  - All uploaded data kept in a **closed-loop environment**
  - Data **never used for model training**
  - End-to-end encryption, SOC 2 Type II compliant infrastructure
  - Full HIPAA and GDPR compliance with audit trail

### 2.3 Regulations — framework selection

Multi-select by region. Each framework card exposes its **Key Requirements**, so the
generator knows the target document structure.

| Region | Authority | Key requirements shown |
|---|---|---|
| North America | **FDA (US)** | CTD format; Module 2 CTD Summaries; Module 3 Quality (CMC); Module 4 Nonclinical Study Reports; Module 5 Clinical Study Reports |
| North America | **Health Canada** | eCTD format; Product Monograph; Risk Management Plan; clinical and non-clinical summaries |
| Europe | **EMA (EU)** | Marketing authorization framework |
| Asia-Pacific | PMDA (Japan), NMPA (China), TGA (Australia) | Surfaced in Resources and Policy News |

### 2.4 Policy News — regulatory intelligence

Live feed of regulatory developments and policy changes, filterable by authority:
**All · FDA · EMA · NMPA · Health Canada · TGA · ICH**.

Each item carries a source attribution, publication date, topic tags, and a "Read More"
deep link. Observed examples: *EMA Publishes New Requirements for Environmental Risk
Assessments* (Apr 15 2026); *New EU Regulation on AI in Medical Devices Affects
Drug-Device Combinations* (Apr 5 2026).

This addresses the "dealing with changing policies" job-to-be-done from the persona work.

### 2.5 Global Value Dossier generator — core engine #1

- **Dossier Configuration:** Therapeutic Area (Oncology) · Target Markets (Global — All
  Regions) · Language (English) · Output Format (PDF).
- **Regional Tender Specifications (optional):** upload past tender documents or enter a
  tender ID — *"AI will map content to localized public purchasing criteria."*
- **Dossier Sections** — modular, individually selectable and expandable. *"AI will
  generate content for each section based on your uploaded data."* Sections visible in the
  walkthrough:
  - **Executive Summary** — high-level overview of clinical value proposition
  - **Disease & Epidemiology** — disease burden, prevalence, and unmet medical needs
  - (further sections exist below the fold but were not scrolled into view)

### 2.6 MSL Materials — core engine #2 (medical scientific communication)

Four material types, each with an estimated generation time:

| Material type | Description | Est. time |
|---|---|---|
| **Scientific Slide Deck** | Comprehensive presentation with clinical data and key messages | 5–7 min |
| **Medical Summary Document** | Concise summary of efficacy, safety, and clinical value | 3–5 min |
| **Scientific FAQ** | Frequently asked questions with evidence-based responses | 4–6 min |
| **Email Response Templates** | Pre-written responses to common medical inquiries | 2–3 min |

**Content Configuration:** Target Audience · Focus Area · **Tone (Scientific / Balanced /
Accessible)** · free-text **Key Messages** ("specific key messages or talking points to
emphasize").

**Brand Guidelines:** upload a Corporate Presentation Template (`.potx`) and a Brand
Guidelines Document (PDF) — *"Uploaded brand assets ensure generated materials are
immediately field-ready."*

Action: **Generate Material with AI** (disabled until configuration is complete).

### 2.7 Document Library — output management

*"Access all AI-generated documents organized by market, regulation, and language."*

- **Filters:** Market/Regulation (All Markets · FDA United States · EMA European Union ·
  PMDA Japan · NMPA China) × Document Type × Language.
- **Per-document card:** title, document-type badge, market badge, language, status
  (Final), date, file size, **Download** and **Preview** actions.
- **Multilingual parallel outputs** — the same oncology dossier appears as:
  - *Global Value Dossier – Oncology Trial XYZ-301* (English, 4.1 MB)
  - *Dossier de Valeur Mondial – Oncologie Essai XYZ-301* (French, 4.3 MB)
  - *Globales Wertdossier – Onkologie-Studie XYZ-301* (German, 4.2 MB)

  One dataset, many localized assets — the clearest demonstration of the platform's
  leverage.

### 2.8 Resources — trust and commercial layer

- **Regulatory Bodies directory:** U.S. FDA · EMA · PMDA (Japan) · NMPA (China) · TGA
  (Australia) — each with Official Website and Guidance Documents links.
- **Regulation Documents Library** (version-dated, downloadable): ICH E6(R3) Good Clinical
  Practice (Mar 2024) · ICH M4 Common Technical Document (Feb 2024) · FDA Guidance –
  Clinical Trial Endpoints (Jan 2026) · EMA Guideline – Clinical Evaluation (Dec 2025) ·
  eCTD Submission Standards v4.0 (Nov 2025) · FDA Real-World Evidence Framework (Apr 2026).
- **Compliance certifications:** HIPAA Compliant · GDPR Compliant, plus a **Data
  Protection Commitment** — AES-256 encryption at rest and in transit, strict access
  controls, audit logs, and data never used to train models without explicit consent.
- **Contracts & Legal Documents:** Master Service Agreement (MSA) · Non-Disclosure
  Agreement (NDA) · Data Processing Agreement (DPA) · Service Level Agreement (SLA) ·
  Invoice Template (XLSX) · Statement of Work (SOW, DOCX).

### 2.9 Submit — guided submission workflow

Five-step stepper: *"Complete each step to generate and submit your regulatory documents."*

1. **Upload Data** — Phase 3 clinical data
2. **Select Markets** — GVD target markets
3. **Select Languages** — scientific content languages
4. **AI Instructions** — generation parameters
5. **Review & Submit** — final review

The review gate is the human-in-the-loop spine of the product.

### 2.10 Settings — Role-Based Access Control

**Compliance Framework Notice:** field teams (MSLs) are restricted from modifying approved
medical or scientific text blocks to maintain regulatory compliance and integrity.

| Role | Upload Clinical Data | Edit Documents | Approve Documents | View All Documents | Export Documents | Manage Brand Guidelines | Modify Medical/Scientific Text Blocks |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Administrator | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Medical Writer | ✓ | ✓ | — | ✓ | ✓ | ✓ | ✓ |
| Medical Science Liaison | — | — | — | ✓ | ✓ | — | — |
| Compliance Officer | — | — | ✓ | ✓ | — | — | — |

**Key Restrictions for Compliance**

- **MSL Text Modification Lock** — Medical Science Liaisons cannot modify approved medical
  or scientific text blocks, preventing unauthorized changes to regulatory-approved content.
- **Approval Workflow** — all document changes require approval from Compliance Officers
  before becoming final.

---

## 3. Product architecture in one line

**One secure ingestion → many outputs (dossiers, decks, summaries, FAQs, emails) × many
regulatory frameworks × many languages × your brand book — gated by role-based approval.**

Three cross-cutting design themes:

1. **Trust is a first-class feature, not a footnote.** Privacy guarantees on the upload
   screen, certifications in Resources, RBAC and approval workflow in Settings.
2. **Human-in-the-loop by design.** Compliance Officer approval gate, Review & Submit step,
   MSL text lock.
3. **Localization on two axes.** Regulatory (framework requirements) and commercial
   (tender specifications + brand book).

---

## 4. Traceability — every user-testing backlog item shipped

Backlog from Deliverable 2 (p. 9) mapped to where it landed in the prototype:

| Backlog item | Implemented as |
|---|---|
| Data Privacy Disclaimers | Upload page guarantee panel + Resources compliance cards |
| Affiliate vs. Global Track Switch | Dashboard Regulatory Track toggle |
| Onboarding Checklist | Dashboard Setup Checklist (incl. Identify Device Classification) |
| Regional Tender Matching | GVD → Regional Tender Specifications upload |
| Brand Book Integration | MSL Materials → Brand Guidelines (`.potx` + PDF) |
| Role-Based Permissions | Settings → RBAC matrix + MSL Text Modification Lock |

---

## 5. Open gaps

Six items worth addressing, roughly in priority order.

1. **Stale product name in the build.** Resources → MSA reads *"Standard service agreement
   for **BioWrite AI** platform usage."* Leftover from an earlier product name; should read
   APProved.

2. **Human expert review has no UI of its own.** This was the single strongest trust answer
   in user testing — Laia: *"combining the like AI power, but having experts that would be
   reviewing everything and working with us would be something that we would really
   value."* Estefanía: *"It should definitely go through a human review."* Currently it is
   only implied through the Compliance Officer role and the Review & Submit step. There is
   no assigned reviewer, review status, SLA, or milestone tracking. Given it is both the
   primary trust answer and the primary differentiator against generic AI tools, it
   warrants a dedicated surface.

3. **No AI transparency or evidence traceability layer.** Alfonso: *"Companies will want to
   understand how the AI works before trusting it."* Oleg: *"If documents are missing, will
   the system generate something randomly?"* Nothing links generated text back to the
   source CSR data, and there is no citation or confidence surface.

4. **Automated Clinical Gap Defense is missing.** Tender *upload* exists, but the
   auto-generated clinical justification for when a product feature does not match tender
   requirements — rated a top opportunity in the consolidated takeaways — does not appear
   anywhere in the flow.

5. **No generated output is ever shown.** The walkthrough covers configuration screens and
   a finished Document Library, but never the agentic generation process running, nor a
   single excerpt of actual generated content. For a product whose entire claim rests on
   output quality, a real dossier excerpt would be the most persuasive screen — and it is
   the one screen that does not exist. This also directly answers the "fear of generic
   outputs" risk raised by Laia.

6. **No MDR/SaMD-specific track.** Device classification appears in the Setup Checklist and
   SaMD roadmaps were a stated opportunity, but there is no EU MDR dossier generator
   sitting alongside the GVD generator, despite MDR being part of the stated product scope.

---

## 6. Suggested next steps

- Fix the BioWrite AI string.
- Design an **Expert Review** surface: reviewer assignment, review status per document,
  turnaround SLA, and milestone tracking.
- Add **source citations** to generated sections, traceable back to uploaded files.
- Build the **Gap Defense** output on top of the existing tender upload.
- Record one screen of **real generated dossier content** for the next demo.
