# APProved

**Medical Writing Platform** — *Unlocking compliance as growth*

Agentic AI that turns Phase III clinical data into regulatory submissions, Global Value
Dossiers (GVDs), and field-ready medical scientific communication — with human expert
review in the loop.

## The problem

After successful Phase III trials, clinical data is handed off for regulatory filing,
medical writing, and commercialization prep. Emerging biopharma companies (EBPs) and local
affiliates rarely have the internal Medical Affairs and Market Access capacity to do this,
so they depend on consultancies that are expensive and slow. Valuable trial data doesn't
become reimbursement material fast enough — delaying launch and burning patent life.

## What the platform does

One secure ingestion of clinical data produces many outputs — dossiers, slide decks,
summaries, FAQs, email templates — across multiple regulatory frameworks, multiple
languages, and your own brand book, gated by role-based approval.

Localization runs on two axes:

- **Regulatory** — framework requirements per authority (FDA, EMA, PMDA, NMPA, TGA,
  Health Canada)
- **Commercial** — regional tender specifications and corporate brand guidelines

## Modules

| Module | Purpose |
|---|---|
| Dashboard | Global ↔ Local Affiliate track toggle, setup checklist, KPIs, recent activity |
| Upload Phase 3 Data | Clinical data ingestion with closed-loop privacy guarantees |
| Regulations | Multi-select regulatory frameworks with their key requirements |
| Policy News | Live regulatory intelligence feed, filterable by authority |
| Global Value Dossier | Modular GVD generation with regional tender matching |
| MSL Materials | Slide decks, medical summaries, scientific FAQs, email templates |
| Document Library | All generated outputs by market, type, and language |
| Resources | Regulatory bodies, guidance library, compliance certs, contract templates |
| Submit | Guided 5-step submission workflow ending in human review |
| Settings | Role-based access control and approval workflow |

## Implementation

The working prototypes live in
[`paulyoungtieyang/APProved`](https://github.com/paulyoungtieyang/APProved), each on its
own branch:

| Branch | What it is |
|---|---|
| `prototype-2` | Next.js app; Global Value Dossier and MSL Materials wired to live Claude generation |
| `prototype-1-ucla-version` (`v1.0`) | Python agentic EU MDR CE-mark drafting workflow — intake gates, parallel section drafting, automated compliance judge, human review loops, full audit trail |

See [`docs/prototype-analysis.md`](docs/prototype-analysis.md) for a full breakdown of the
prototype's functionality, the agentic pipeline behind generation, traceability to user
testing, and open gaps.

## Value proposition

For medical affairs teams and health startups struggling with expensive, slow consulting
agencies, APProved delivers drastic time and cost savings on asset creation because it
pairs secure AI automation with human expert review. Unlike generic AI tools or legacy
consultancies, it offers complete flexibility by instantly integrating regional tender
requirements and corporate brand books.

## Team

Team 3 — Fashion Icons · EMBA Cohort 2025–2027, ESADE

Ema Menichelli · Giulia Raimondi · Micaela Vanes · Paul Young Tie Yang
