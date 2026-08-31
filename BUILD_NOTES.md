# Build Notes

What is actually built, what is stubbed, and what would come next. Written so the gap
between the demo and a production system is explicit rather than implied.

---

## Built and working

### Interface
- Full port of the Figma dashboard: sticky header, sidebar, thirteen pages, responsive down to
  mobile. Design tokens documented in [`docs/interface-spec.md`](docs/interface-spec.md).
- Server-rendered Jinja2, no build step, no runtime dependencies beyond the four packages in
  `requirements.txt`.

### Data ingestion
- Drag-and-drop and browse upload for CSV, XLSX, PDF, DOCX, TXT — unsupported types rejected
  with a message rather than a stack trace.
- CSV parsed with `csv.DictReader`; XLSX with `openpyxl` in read-only mode. **Verified**: a
  20-row × 13-column XLSX round-trips and parses identically to its CSV twin.
- SHA-256 checksum per file, stored and surfaced in the UI.
- Statistics derived from the actual rows — cohort size, mean age, mean MARD, wear duration,
  type-1 share, adverse events by type and severity, endpoint table with CIs and p-values.
  Every figure quoted in a generated draft traces to one of these.

### Generation
- Three-layer prompt composition (client baseline / deliverable template / expert overlay),
  with the resolved prompt persisted alongside the output.
- Ten dossier sections, generated one at a time through `/api/dossier/section`, each with its
  own `generation_run` row and audit event. Progress in the UI reflects committed state.
- Four MSL material types with audience / focus / tone / key-message configuration.
- Refinement loop: each pass increments a round counter; history is not overwritten.
- Offline engine is deterministic and grounded — it will say "not reported in the uploaded
  dataset" rather than inventing an endpoint.
- Live providers (Anthropic, OpenAI, Google) over stdlib `urllib`. Keys come from the UI or
  the environment, are used for exactly one call, and are never persisted or logged. A failed
  live call falls back to the offline draft.

### Governance
- Append-only audit trail — every upload, brief revision, generation, refinement, review
  decision and export. **Verified**: no API key material reaches the log.
- Immutable versioned briefs with field-level diffs (`core/briefs.py`).
- RBAC across four roles. **Verified server-side**: MSL and Compliance Officer receive a 403
  from the generation endpoint, not merely a hidden button.
- Review & approval workflow (`core/models.ReviewRound`, `_submit_review` in `app.py`) —
  generic across every deliverable type. A reviewer records accept / revise / decline /
  amend-brief with feedback; **accept** sets `GenerationRun.approved_at` and locks the run.
  **Verified server-side on two independent write paths**: `/generation/<id>/refine` and
  `/api/dossier/section` (which deletes and replaces the section's row on regeneration) both
  reject a locked run — the second was a real gap found in testing: the regenerate-all-sections
  flow didn't originally check the lock at all, and deleting an approved run whose
  `ReviewRound` rows have a NOT NULL foreign key crashed with an IntegrityError before the fix.
  A `revise` / `decline` / `amend_brief` decision on a locked run reopens it.
- Trust & Data Handling page (`/trust`, `core.content.build_methodology_markdown`) — plain-
  language methodology and data-handling document, reachable without choosing a workspace so
  it can be read before an engagement starts. Downloads as Markdown.

### Requirements fit
- `core/requirements.py` — matches uploaded evidence against any external requirement list
  (a tender, an HTA/formulary checklist, a notified-body or partner due-diligence list).
  Deliberately generic: no device, market or therapeutic area is named anywhere in the module.
- Requirements arrive pasted (one per line) or as an uploaded file with a `Requirement`
  column; each gets a **Met / Partial / Not addressed** verdict from keyword overlap against
  the uploaded evidence categories, a free-text "characteristics" field, and the brief, with
  argumentation text for anything short of a clean match.
- Same three-layer prompt shape and offline/live provider path as every other deliverable —
  a live key writes richer argumentation prose over the same match data rather than a
  different pipeline.
- **Verified**: a demo-data run initially returned 9/9 "Met", which turned out to be real bugs
  in the keyword-signal lists (a generic word — "requirement" — sat in the "software" category
  signal set, so almost every input line matched it; "performance" and "effectiveness" caused
  cross-category false positives via "cost-effectiveness"). Fixed by removing generic words
  from `CATEGORY_SIGNALS`, biased toward under-claiming: a false "Partial" is a better failure
  than a false "Met" for a screening tool. Re-verified: 7 Met / 2 Partial against the demo's
  actual uploaded categories, with no verdict left unexplained by its basis text.

### Brand templates → branded PowerPoint
- Upload a corporate `.pptx` / `.potx` on the MSL Materials page (or via `/upload` with the
  brand category). The file is validated with python-pptx on receipt — an unreadable one is
  rejected and deleted rather than stored to fail later at export.
- The picker shows what was actually read out of each template: layout count, aspect ratio
  and theme fonts.
- Generating a Scientific Slide Deck against a template produces a real `.pptx` that
  inherits that template's theme, fonts, colours and slide layouts. Existing slides in the
  template are dropped; only masters and layouts are used.
- Which template a deck was built with is persisted on the run (`generation_run
  .brand_template_id`), so re-downloading reproduces the same branded file.
- **Verified**: two templates with different fonts and aspect ratios produce visibly
  different decks; selecting "default theme" produces an unbranded one.

---

## Stubbed or simplified

| Area | Current state | What production needs |
|---|---|---|
| **Export format** | Slide decks export as real branded `.pptx`; everything else as Markdown | PDF and DOCX with the client's document template, headers and pagination |
| **Policy news** | Static curated list | Live feed from EUR-Lex, MDCG and AEMPS |
| **Resources** | Static list, no files | Document store with the actual guidance PDFs |
| **Brand guidelines** | PowerPoint templates fully wired (upload → pick → branded export) | Brand *rules* beyond the deck theme: tone-of-voice, approved claim wording, logo placement |
| **Literature search** | Database selected but not queried | PubMed / Embase integration feeding the evidence base |
| **Translation** | Languages selected, output stays English | Per-language generation with terminology control |
| **Judge scoring** | Schema exists (`judge_score`, `judge_rubric`), unused | Automated rubric pass before human review |
| **Requirements-fit matching** | Keyword overlap — legible, but will miss a paraphrase | NLP/embedding-based matching, still surfaced with a confidence signal |
| **Column mapping** | Upload expects recognised column names; a differently-shaped CRF won't parse | A mapping step: match the client's own headers to the fields drafts cite |
| **Auth** | Role switcher in the header | Real accounts, SSO, per-user audit identity |
| **Multi-tenancy** | Two engagements per browser session (tool + demo) | Organisations, projects, member permissions |
| **Storage** | Local SQLite + filesystem | Postgres, object storage, encryption at rest |

---

## Known constraints

- **Session-scoped engagements.** A landing page (`/`) routes into one of two workspaces —
  a blank tool engagement or the pre-loaded CGM demo — each kept under its own session key
  (`engagement_id_tool` / `engagement_id_demo`) so switching between them never mixes data.
  `Engagement` supports many rows; there is still no picker UI for multiple *tool*
  engagements, only the single one active in the session (with a "start new" action that
  discards it).
- **Section key encoding.** The section id is prefixed onto `resolved_prompt` as
  `"<section-id>::<prompt>"` because `GenerationRun` has no section column. It works and is
  queryable, but a dedicated column is the right fix before this grows.
- **HTML weight.** The nav icon set is inlined twice per page (sidebar + mobile drawer),
  which dominates page size. A `<symbol>` sprite would fix it if it ever matters.
- **Markdown renderer.** `markdown_to_html` in `app.py` handles headings, lists, bold, code,
  rules and blockquotes — enough for what this app generates, not a general renderer. Swap in
  a real library if drafts start arriving with tables or nested lists.
- **Health-economic figures** in the drafts are illustrative, not modelled.

---

## Not a medical device

APProved is a writing platform. It contains no dosing logic and no device functionality of
any kind — the bolus calculator belongs to the *client's device*, and exists here only as
uploaded documentation to be written up (`sample_data/bolus_calculator_spec.csv` and
`bolus_calculator_verification.csv`). There is no calculator page, no route and no
calculation code in this repository.

The generated dossier text is a drafting aid requiring expert review before any regulatory
use, and the figures in it are illustrative.

---

## Verification performed

Each of these was executed against the running app, not assumed:

- All 31 routes resolve as expected; unknown paths return 404.
- Eleven dossier sections generate, persist and appear in the library.
- XLSX upload parses to 20 rows × 13 columns; `.exe` is rejected.
- Refinement advances a section from round 1 to round 2 with a revision note.
- Submission wizard carries state across all five steps and writes to the brief.
- Role cycling blocks generation for MSL and Compliance Officer with a 403.
- A fresh demo seed writes 19 audit events (2 review decisions, 1 approval, 1
  requirements-fit generation and 2 refined dossier sections among them) with no key material.
- Every internal link and form target on all 13 pages, in both workspaces, resolves — crawled,
  not spot-checked. No dead buttons, no empty `href`s, no orphaned readonly inputs.
- Interactive controls driven in a real browser: collapsible section rows, provider→model
  swapping with API-key reveal, the progressive 11-section generation walk, dropzone
  drag/drop states, document filters, audit accordions, the review decision form and the
  mobile drawer.
- A cold-start demo run regenerates all 11 dossier sections (the already-approved one
  correctly rejected with a 409, the rest overwritten), generates 4 MSL materials and a second
  Requirements Fit run, and downloads all 17 resulting documents: 16 Markdown files that open
  and parse — including a rendered `<table>` for the requirements-fit match table, not raw
  pipe-delimited text — and one 12-slide `.pptx` that opens in python-pptx carrying the
  template's fonts and colours.
- The seven sample data files (three clinical, two software-lifecycle, one external
  requirements checklist, one brand template) all still open and parse.
- A fresh session hitting `/dashboard` or any inner page directly redirects to `/`; `/trust`
  is deliberately the one exception, reachable with no workspace chosen at all.
- Entering the tool and the demo from two independent sessions shows zero cross-contamination:
  the tool's upload/document lists stay empty while the demo's show its 7 files, and vice
  versa; switching workspace and back re-uses each engagement rather than recreating it.
- `/bolus-calculator` returns 404 in both workspaces — the route was removed along with the
  page; the calculator exists only as uploaded source documentation
  (`sample_data/bolus_calculator_spec.csv` / `_verification.csv`), never as app functionality.
- Approval lock enforcement checked with explicit round-number deltas rather than assumed
  baselines (an earlier pass of this same test asserted the wrong starting round and reported
  three false failures): refining a locked run leaves its round and `approved_at` unchanged;
  refining an unlocked run advances it by exactly one round; a `revise` decision on a locked
  run clears `approved_at`, after which refinement succeeds again.
- Regenerating every dossier section while one is approved: the approved section is rejected
  with an HTTP 409 and stays untouched; every other section regenerates normally; the
  underlying `ReviewRound` → `GenerationRun` cascade (added after this surfaced a NOT NULL
  constraint failure on delete) does not orphan review history on the sections that do get
  replaced.
