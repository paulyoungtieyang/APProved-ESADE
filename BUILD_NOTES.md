# Build Notes

What is actually built, what is stubbed, and what would come next. Written so the gap
between the demo and a production system is explicit rather than implied.

---

## Built and working

### Interface
- Full port of the Figma dashboard: sticky header, sidebar, twelve pages, responsive down to
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
- Append-only audit trail — every upload, brief revision, generation, refinement and export.
  **Verified**: no API key material reaches the log.
- Immutable versioned briefs with field-level diffs (`core/briefs.py`).
- RBAC across four roles. **Verified server-side**: MSL and Compliance Officer receive a 403
  from the generation endpoint, not merely a hidden button.

### Device-specific
- Bolus calculator implementing carb dose + correction dose + CGM trend adjustment − insulin
  on board, with hypoglycaemia / ketone / falling-trend warnings. **Verified** against hand
  calculation.

---

## Stubbed or simplified

| Area | Current state | What production needs |
|---|---|---|
| **Export format** | Markdown download | Real PDF and DOCX with the client's template, headers and pagination |
| **Policy news** | Static curated list | Live feed from EUR-Lex, MDCG and AEMPS |
| **Resources** | Static list, no files | Document store with the actual guidance PDFs |
| **Brand guidelines** | Upload controls present, unused | Apply `.potx` themes and brand rules to generated decks |
| **Literature search** | Database selected but not queried | PubMed / Embase integration feeding the evidence base |
| **Translation** | Languages selected, output stays English | Per-language generation with terminology control |
| **Judge scoring** | Schema exists (`judge_score`, `judge_rubric`), unused | Automated rubric pass before human review |
| **Review rounds** | `ReviewRound` model exists, no UI | Client and expert review with accept / revise / decline |
| **Auth** | Role switcher in the header | Real accounts, SSO, per-user audit identity |
| **Multi-tenancy** | One engagement per browser session | Organisations, projects, member permissions |
| **Storage** | Local SQLite + filesystem | Postgres, object storage, encryption at rest |

---

## Known constraints

- **Session-scoped engagement.** One demo engagement per browser session, auto-seeded on
  first load. `Engagement` supports many; there is no picker UI yet.
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

The bolus calculator demonstrates a documented algorithm. It is not validated, not certified,
and must not inform real dosing. The generated dossier text is a drafting aid requiring
expert review before any regulatory use.

---

## Verification performed

Each of these was executed against the running app, not assumed:

- All twelve routes return 200; unknown paths return 404.
- Ten dossier sections generate, persist and appear in the library.
- XLSX upload parses to 20 rows × 13 columns; `.exe` is rejected.
- Bolus calculation matches hand arithmetic (75 g, 210 mg/dL, rising, 1.5 U IOB → 7.7 U).
- Refinement advances a section from round 1 to round 2 with a revision note.
- Submission wizard carries state across all five steps and writes to the brief.
- Role cycling blocks generation for MSL and Compliance Officer with a 403.
- Audit trail records twelve events for the seeded demo with no key material.
