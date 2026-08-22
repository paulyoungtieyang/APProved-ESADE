# APProved — Prototype Functionality Analysis

Analysis of the updated APProved prototype walkthrough, cross-referenced against the
design-thinking process deck and the Deliverable 2 user-testing findings.

**Sources**

| Source | Notes |
|---|---|
| `Updated APProved Prototype.mp4` | 2:14 screen recording, 2136×1454, **no audio track** — all findings below are read off the screens |
| `Team 3 - Fashion Icons - InClass Deliverable.pdf` | 33 pages, design thinking process (Empathize → Define → Ideate → Test) |
| `Team 3 - Fashion Icons - Deliverable 2 - User Testing.pdf` | 11 pages, 4 user interviews + prototype backlog + value proposition |
| [`paulyoungtieyang/APProved`](https://github.com/paulyoungtieyang/APProved) | Source. `prototype-2` — Next.js app with GVD/MSL wired to live Claude generation. `prototype-1-ucla-version` (`v1.0`) — Python agentic EU MDR CE-mark workflow |

Where the recording and the source disagree, **the source wins** — §2.5 and §4 are read
from code, and §6 is reassessed against it.

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

The walkthrough shows the configuration surface; the working implementation lives in
[`paulyoungtieyang/APProved`](https://github.com/paulyoungtieyang/APProved) on the
`prototype-2` branch. Details below are read from that source, not inferred from the video.

**Configuration vocabularies** (`web/src/lib/mock-data/dossier-options.ts`)

| Field | Options |
|---|---|
| Therapeutic Area | Cardiometabolic · Oncology · Immunology · Neurology · Diagnostics & Monitoring |
| Target Market | Global (All Regions) · United States · European Union · Japan · China · Australia · Canada |
| Language | English · French · German · Japanese · Chinese |
| Output Format | PDF · Word (DOCX) · PowerPoint (PPTX) |
| Tender Type | Public Tender · Hospital Formulary · National HTA Submission · Private Payer |

**Regional Tender Specifications (optional)** — free-text spec or tender ID, passed
through to the model so content maps to localized public purchasing criteria.

**The eight dossier sections** — modular and individually selectable, all selected by
default:

| # | Section | Description |
|---|---|---|
| 1 | Executive Summary | High-level overview of clinical value proposition |
| 2 | Disease & Epidemiology | Disease burden, prevalence, and unmet medical needs |
| 3 | Clinical Efficacy Data | Phase 3 trial results, endpoints, and statistical analysis |
| 4 | Safety & Tolerability | Adverse events, safety profile, and risk-benefit analysis |
| 5 | Pharmacoeconomic Analysis | Cost-effectiveness, budget impact, and economic value |
| 6 | Quality of Life Outcomes | Patient-reported outcomes and quality of life assessments |
| 7 | Comparative Effectiveness | Comparison with current standard of care and competitors |
| 8 | Target Population | Patient population, inclusion criteria, and treatment eligibility |

**Generation endpoint** — `POST /api/generate-dossier`
(`web/src/app/api/generate-dossier/route.ts`, Node runtime)

- **Request:** `therapeuticArea`, `market`, `language`, `outputFormat`, `sectionIds[]`,
  optional `regionalTenderSpec`, `provider`, `apiKey`, `promptRules`.
- **Dual provider:** Claude (default) on `claude-opus-5`, `max_tokens` 8000, medium
  reasoning effort; OpenAI on `gpt-4o`, `max_tokens` 4000.
- **Expert-editable prompt rules:** a `promptRules` string is appended to the system
  prompt as *"Additional rules from the regulatory/medical affairs team — follow these
  strictly."* This lets medical affairs constrain generation without a code change.
- **System role:** *"a market access and value-communications specialist drafting an
  early-stage Global Value Dossier. Output valid markdown only."*
- **Anti-fabrication instruction:** the prompt asks for *"representative (clearly
  illustrative, not fabricated as if real) figures and claims"*, 2–4 short paragraphs per
  section, and nothing outside the requested sections.
- **Validation:** missing required fields or zero valid sections → `400`; unconfigured
  provider → `503`; upstream failure → `502`.
- **Output:** markdown, one `## ` heading per selected section, in the requested order.

**Result rendering** (`GeneratedDossierPreview.tsx`) — the UI runs an
`idle → generating → done → error` state machine, disables the button while generating,
surfaces errors inline, and renders the draft under a **"Draft generated by Claude"**
badge titled *"{Therapeutic Area} Global Value Dossier — {Market}"* with a
*"{Language} · {Output Format}"* subline.

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

## 4. The agentic pipeline — what GVD generation should adopt

The `prototype-1-ucla-version` branch (tagged `v1.0`) implements a full agentic EU MDR
CE-mark drafting workflow in Python. GVD generation is currently a **single LLM call**;
the MDR pipeline is a **gated, parallelized, reviewed workflow**. These are the pieces
worth porting across.

### 4.1 Parallel section drafting — `drafting.py`

Each section is an independent, focused LLM call, run concurrently via `ThreadPoolExecutor`.
The design note is explicit that this is *parallelization (sectioning)*, not an open-ended
orchestrator-worker agent, because the target document structure is fixed and known in
advance — so the `SECTIONS` list **is** the architecture decision.

The same reasoning applies directly to the GVD: its eight sections are equally fixed, so
one call per section would improve depth per section and cut wall-clock time, replacing
today's single 8000-token call covering all eight at once.

### 4.2 Automated compliance gate — `judge.py`

An LLM-as-Judge check that runs **before the draft reaches a human**. Deliberately built as
a *checklist scorer* rather than a free-text critic: it returns a fixed, parseable format
so the orchestrator can act on it programmatically and redraft flagged sections without a
second interpretive call. The stated rationale is that it catches mechanical gaps cheaply
so the expert's single review pass is spent on things that genuinely need judgment.

A GVD equivalent would score each section against a market-access rubric — evidence cited,
comparator named, economic claim substantiated.

### 4.3 Human-in-the-loop review — `review.py`

Two applications of the same evaluator-optimizer pattern with a **human as the evaluator**:

- `internal_expert_review()` — one QA pass, capped for safety
- `client_review_loop()` — up to `max_client_rounds` rounds, then a mandatory final
  accept/decline decision

Supports both interactive input and a scripted `auto_demo` mode for unattended end-to-end
runs. **This is the missing "expert review" surface identified in §6.2** — it already
exists in Python and has no UI counterpart in the web app.

### 4.4 Live regulatory grounding — `regulation.py`

Fetches the live regulation-updates feed and **combines** it with a local clause-level
reference rather than replacing it: the local file carries the Annex I/II/III/XIV clause
structure that drafting and review are grounded in, while the live fetch adds visibility
into recent amendments and guidance. An `--offline` flag falls back to local only.

This is the concrete wiring between **Policy News and generation** — the design note states
retrieval should refresh whenever the news feed flags a change. Today those two modules are
unconnected.

### 4.5 Audit trail — `audit_trail.py`

A structured, per-submission record: every gate decision, every round of human feedback,
every redraft, every classification discrepancy and its resolution, and the final outcome —
each timestamped and attributed to system, agent, client, or regulatory expert. Emitted in
two formats from one event list: `.audit.json` (machine-readable) and `.audit.txt` (a
plain-language transcript).

Critically, it is **consent-gated**: a run that never receives logging consent never gets a
trail written. This is the traceability layer that answers the AI-transparency objection in
§6.3.

### 4.6 Intake gates — run in order, before any drafting

| Gate | Module | Behavior |
|---|---|---|
| Audit-trail consent | `consent_gate.py` | Runs **first** — without consent nothing may be recorded, so nothing else is evaluated |
| Scope | `scope_gate.py` | Rejects out-of-scope requests before any validation or drafting effort is spent |
| Data quality | `data_quality_gate.py` | Rejects unparsable uploads, missing required intake fields, or **>15% missing patient-level data** in the pivotal dataset |
| Classification plausibility | `classification_gate.py` | Catches implausible self-declared classifications that no human happened to challenge |

Each gate declines with a stated reason rather than failing silently. The data-quality gate
in particular is the structural answer to the hallucination concern — it refuses to draft
from insufficient input instead of inventing content to fill gaps.

### 4.7 Branded export — `docx_export.py`

Uses `python-docx` with no external dependencies (no LibreOffice or Word install required).
When a brand template is supplied it opens that as the base document instead of a blank
one, so headers, footers, and styles carry over — the delivery half of the Brand Book
feature the web UI already collects assets for.

---

## 5. Traceability — every user-testing backlog item shipped

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

## 6. Open gaps

Reassessed against the `APProved` source. Two gaps previously flagged from the recording
alone turned out to be already solved in code, and the central gap is now clearer: **the
two halves of the product do not share an architecture.**

### 6.1 The headline gap — GVD generation has none of the pipeline's rigor

The MDR workflow (§4) runs gates → parallel drafting → automated judge → human review →
audit trail. The GVD path is **one LLM call**, with no intake gate, no compliance scoring,
no review loop, and no audit record. Same company, same claim, two very different levels of
assurance.

This is the single most consequential item on the list, and everything in §4 is a
ready-made answer to it — the code already exists and is proven on the MDR side.

### 6.2 Expert review exists in Python, but has no web UI

The single strongest trust answer in user testing — Laia: *"combining the like AI power,
but having experts that would be reviewing everything and working with us would be
something that we would really value."* Estefanía: *"It should definitely go through a
human review."*

`review.py` implements exactly this (§4.3). In the web app it is only *implied* through the
Compliance Officer role and the Review & Submit step: no assigned reviewer, review status,
SLA, or milestone tracking. **This is a porting job, not a design-from-scratch job.**

### 6.3 Transparency layer exists in Python, but is not surfaced

Alfonso: *"Companies will want to understand how the AI works before trusting it."* Oleg:
*"If documents are missing, will the system generate something randomly?"*

`audit_trail.py` already produces a timestamped, attributed, consent-gated record in both
machine- and human-readable form (§4.5), and the data-quality gate structurally prevents
drafting from insufficient input (§4.6). Neither is visible anywhere in the web UI, and
generated GVD sections carry no citations back to source data.

### 6.4 Automated Clinical Gap Defense is still missing

Tender *input* exists — `regionalTenderSpec` is passed to the model — but nothing
auto-generates clinical justification when a product feature does not match tender
requirements. Rated a top opportunity in the consolidated takeaways; absent from both
codebases.

### 6.5 Policy News and generation are unconnected

`regulation.py` establishes the pattern of combining live regulatory fetch with a local
clause-level reference (§4.4), and the design note states retrieval should refresh whenever
the news feed flags a change. In the web app, Policy News is a read-only feed that feeds
nothing.

### 6.6 Two disconnected codebases

The MDR pipeline is a Python CLI; the GVD and MSL generators are a Next.js app. They share
no code, no data model, and no audit surface. The `README` frames prototypes as
independently checkout-able snapshots, which is sound for coursework — but the
consolidation question is now live.

### Resolved since the previous revision

- ~~*GVD section list incomplete*~~ — all eight sections are enumerated in §2.5.
- ~~*No generated output is ever shown*~~ — the app renders drafts via
  `GeneratedDossierPreview` with a "Draft generated by Claude" badge. This was a **recording
  gap, not a product gap**: the walkthrough simply never triggers a generation. Worth
  capturing on video, since it directly answers Laia's "fear of generic outputs" risk.
- ~~*No MDR/SaMD track*~~ — `prototype-1-ucla-version` **is** a complete EU MDR CE-mark
  workflow. It is not absent, it is unintegrated (see §6.6).

### Still open from the recording

**Stale product name.** Resources → MSA reads *"Standard service agreement for **BioWrite
AI** platform usage."* Leftover from an earlier product name.

---

## 7. Suggested next steps

> **Superseded in part.** The next build is now specified in
> [`two-view-architecture.md`](two-view-architecture.md), which addresses §6.1, §6.2 and
> §6.3 structurally by splitting the product into Client and User views over a shared
> append-only audit trail. Items 4–7 below remain open and are not covered by that spec.

Ordered by leverage:

1. **Port the pipeline to GVD generation** — the highest-value work, and mostly a
   translation exercise since the Python implementations are proven:
   - Split the single call into eight parallel per-section calls (§4.1)
   - Add a market-access rubric judge before human review (§4.2)
   - Add a data-quality intake gate so the system declines rather than invents (§4.6)
2. **Build the Expert Review UI** on top of `review.py`'s two-loop model — reviewer
   assignment, per-document status, round count, accept/decline (§4.3, §6.2).
3. **Surface the audit trail** in the web app, and add per-section source citations
   traceable back to uploaded files (§4.5, §6.3).
4. **Wire Policy News into retrieval** so flagged changes refresh generation grounding
   (§4.4, §6.5).
5. **Build Gap Defense** on top of the existing `regionalTenderSpec` input (§6.4).
6. **Re-record the demo** including a live generation and the rendered draft (§6, Resolved).
7. Fix the BioWrite AI string.
