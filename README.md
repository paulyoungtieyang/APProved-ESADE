# APProved

**Medical Writing Platform** — *Unlocking compliance as growth*

Agentic AI that turns pivotal clinical data into regulatory submissions, Global Value
Dossiers (GVDs), and field-ready medical scientific communication — with human expert
review in the loop.

This repository holds the **Python prototype**, a Flask port of the APProved Figma design.
It ships with a working demo: a Class IIb continuous glucose monitoring (CGM) system going
through EU MDR conformity assessment, launching in Spain.

---

## Run it

```bash
pip install -r requirements.txt
```

```bash
python3 app.py
```

The app opens at **http://localhost:5001** and seeds the demo engagement on first load —
sample CGM dataset, brief, and MDR/AEMPS framework selection are already in place.

No API key. No internet. No configuration. Set `PORT` to use a different port, or
`OPEN_BROWSER=0` to stop it launching a browser tab.

---

## The problem

After a successful pivotal trial, clinical data is handed off for regulatory filing, medical
writing, and commercialisation prep. Emerging companies and local affiliates rarely have the
internal Medical Affairs and Market Access capacity to do this, so they depend on
consultancies that are expensive and slow. Valuable trial data does not become reimbursement
material fast enough — delaying launch and burning patent life.

## What the platform does

One secure ingestion of clinical data produces many outputs — dossier sections, slide decks,
summaries, FAQs, email templates — across multiple regulatory frameworks, markets and
languages, with every claim traceable back to the file and prompt that produced it.

---

## The interface

Ten pages behind a persistent sidebar, matching the Figma prototype 1:1.

| Page | Path | What it does |
|---|---|---|
| Dashboard | `/` | Setup checklist, live stats from the parsed dataset, quick actions, recent activity |
| Upload Clinical Data | `/upload` | Drag-and-drop CSV / XLSX / PDF / DOCX, SHA-256 checksums, parsed cohort + safety summary |
| Regulations | `/regulations` | Framework picker (MDR, AEMPS, MDCG, IVDR, FDA, MHRA, PMDA, NMPA, TGA) written back to the brief |
| Policy News | `/policy-news` | Filterable regulatory feed focused on MDR and Spanish market access |
| Global Value Dossier | `/global-dossier` | Section-by-section generation with live progress, three-layer prompt composition |
| MSL Materials | `/msl-material` | Slide decks, medical summaries, scientific FAQs, email templates |
| Bolus Calculator | `/bolus-calculator` | The demo device's dosing-support module, documented as an IEC 62304 component |
| Document Library | `/documents` | Everything generated, filtered by type / market / language, with download |
| Resources | `/resources` | Regulations, guidance, standards and templates the drafts cite |
| Submit | `/submission` | Five-step wizard: data → markets → languages → AI instructions → review |
| Audit Trail | `/audit` | Append-only event log with full payloads |
| Settings | `/settings` | Role-based access control matrix and provider key status |

---

## How generation works

Every draft is composed from **three prompt layers**, kept visibly separate:

| Layer | Source | Editable by |
|---|---|---|
| **1 — Client baseline** | The signed brief: markets, frameworks, tone, audience, key messages | Client only |
| **2 — Deliverable template** | Section-specific structure and evidence rules | System |
| **3 — Expert overlay** | The medical writer's emphasis and corrections | Expert |

The resolved prompt is stored with the output, so any claim can be traced back to the exact
text sent to the model. Refinements increment a round counter rather than overwriting history.

### Offline by default

Generation runs with **no API key and no network**. The offline engine is deterministic and
grounds every figure in the uploaded dataset — it reads the actual CSV/XLSX rows rather than
inventing numbers.

Supplying a key on any generation page switches the same prompt to a live model:

```bash
export ANTHROPIC_API_KEY=sk-ant-...   # or OPENAI_API_KEY / GOOGLE_API_KEY
```

Keys can also be typed into the UI per request. Either way they are used for that one call
and are **never** written to the database or the audit trail. A failed live call falls back
to the offline draft rather than dead-ending.

Live calls go over `urllib` from the standard library — there are no vendor SDKs to install
or keep in sync.

---

## The demo

| | |
|---|---|
| Device | Class IIb continuous glucose monitoring system with integrated bolus calculator |
| Regulation | EU MDR 2017/745 (Annex II, Annex XIV, Annex III) + AEMPS |
| Launch market | Spain, then wider EU |
| Languages | Spanish (Castellano), English |
| Dataset | 20 patients · 10 adverse events · 10 statistical endpoints |
| Headline figures | Mean MARD 9.6% · 94.2% hypoglycaemia detection · 13.8-day wear |

Sample files live in `sample_data/`. Reset the demo from the button at the foot of the
dashboard — it rebuilds the engagement and discards generated work.

To use your own data, drop a CSV or XLSX on `/upload`. The parser detects the category from
the header row and recomputes every statistic the drafts cite.

---

## Roles

The header badge cycles through four roles. Permissions are enforced **server-side**, not
just hidden in the UI:

| Role | Upload | Edit | Approve | Export | Modify approved text |
|---|---|---|---|---|---|
| Administrator | ✓ | ✓ | ✓ | ✓ | ✓ |
| Medical Writer | ✓ | ✓ | — | ✓ | ✓ |
| Medical Science Liaison | — | — | — | ✓ | — |
| Compliance Officer | — | — | ✓ | — | — |

The MSL text-modification lock is the compliance-critical one: field teams read and export
approved materials but cannot alter them.

---

## Project layout

```
app.py                  Flask routes and page controllers
core/
  models.py             SQLAlchemy schema (engagement, brief, upload, generation, audit)
  briefs.py             Immutable brief versioning with field-level diffs
  audit.py              Append-only event log
  dataset.py            CSV/XLSX ingestion, checksums, derived statistics
  content.py            Reference data + the deterministic offline drafting engine
  llm.py                Provider layer (offline / Anthropic / OpenAI / Google)
  gates.py              Consent and data-quality gates
templates/              Jinja2 pages; base.html is the sidebar shell, _icons.html the icon set
static/css/style.css    Design system ported from the Figma tokens
sample_data/            Demo CGM dataset
storage/                SQLite database and uploaded files (gitignored)
docs/                   Architecture and interface specifications
```

---

## Documentation

- [`docs/interface-spec.md`](docs/interface-spec.md) — Figma → Flask mapping, design tokens, component inventory
- [`docs/two-view-architecture.md`](docs/two-view-architecture.md) — prompt composition, refinement loop, audit model
- [`docs/prototype-analysis.md`](docs/prototype-analysis.md) — analysis of the earlier prototypes
- [`BUILD_NOTES.md`](BUILD_NOTES.md) — what is built, what is stubbed, what is next

---

## Status

This is a **prototype**. It demonstrates the workflow and the interface; it is not a medical
device, not validated, and the bolus calculator must not be used for real dosing decisions.
The health-economic figures in the generated drafts are illustrative.
