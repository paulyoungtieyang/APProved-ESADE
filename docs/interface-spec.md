# APProved — Interface Specification

How the Figma prototype maps onto the Flask application, the design tokens that carry it,
and the component inventory. Read this before changing anything visual.

**Source of truth:** the Figma export (`src/app/` — React + Tailwind + shadcn/ui).
**Implementation:** server-rendered Jinja2 with a hand-written CSS design system, no build step.

---

## 1. Why a port rather than a rewrite

The Figma prototype is a React SPA with client-side state. The Flask app needs the same
interface backed by real persistence, real file ingestion and a real audit trail. Rather
than run a Node build alongside Python, the design tokens were ported directly into
`static/css/style.css` and the layout reproduced in Jinja2.

The consequence worth knowing: **there is no Tailwind at runtime**. Utility class names from
the Figma source do not exist here. Every visual is either a semantic component class
(`.card`, `.btn--primary`, `.option-card`) or one of a small set of utilities
(`.row`, `.stack-4`, `.mb-6`, `.text-muted`).

---

## 2. Design tokens

Ported verbatim from Tailwind's defaults, which is what the Figma design uses.

| Role | Token | Value |
|---|---|---|
| Page background | `--slate-50` | `#f8fafc` |
| Card surface | white | `#ffffff` |
| Border | `--slate-200` | `#e2e8f0` |
| Body text | `--slate-900` / `--slate-600` | `#0f172a` / `#475569` |
| Muted text | `--slate-500` | `#64748b` |
| Primary | `--blue-600` → `--blue-700` on hover | `#2563eb` → `#1d4ed8` |
| Selected surface | `--blue-50` / `--blue-100` | `#eff6ff` / `#dbeafe` |
| Success | `--green-600`, `--green-50` | `#16a34a`, `#f0fdf4` |
| Warning | `--amber-600`, `--amber-50` | `#d97706`, `#fffbeb` |
| Destructive | `--red-600`, `--red-50` | `#dc2626`, `#fef2f2` |
| Accent tiles | `--purple-500`, `--orange-500` | `#a855f7`, `#f97316` |

Geometry: `--radius` `0.5rem` (cards, inputs, buttons), `--radius-full` for pills,
`--header-h` `4rem`, `--sidebar-w` `16rem`.

Type scale: 16px root. Page titles `1.5rem/600`, dashboard hero `1.875rem/600`, section
titles `1.25rem/600`, card titles `1rem/600`, body `0.875rem`, hints `0.75rem`.

### One rule that matters

```css
[hidden] { display: none !important; }
```

Component classes set `display`, which would otherwise beat the UA stylesheet's `[hidden]`
rule and leave "hidden" panels visible. All JS visibility toggling uses the `hidden`
attribute, so this rule keeps it authoritative. Removing it silently breaks the API-key
fields, the progress panel and every collapsible section.

---

## 3. Shell

`templates/base.html`. Three regions, identical to `DashboardLayout.tsx`:

- **Header** — sticky, `4rem`, white on a `slate-200` bottom border. Blue rounded logo tile,
  wordmark + tagline, role badge on the right (`md:` and up), hamburger below `lg:`.
- **Sidebar** — `16rem`, sticky under the header, visible from `lg:` up. Active item is
  `blue-50` background with `blue-700` text. Navigation is grouped under small uppercase
  section labels (Workspace / Generate / Deliver / Governance) — an addition to the Figma,
  needed because the Flask app has 12 destinations rather than 10.
- **Main** — `flex-1`, padding steps `1rem → 1.5rem → 2rem` across breakpoints.

Breakpoints follow Tailwind: `640px`, `768px`, `1024px`, `1280px`.

Navigation is data-driven from `NAV_ITEMS` in `app.py`. Adding a page means adding one dict
entry and one route — the sidebar, mobile drawer and active state all follow.

### Icons

`templates/_icons.html` is a Jinja macro wrapping ~40 inline Lucide SVGs — the same icon set
the Figma uses, at the same 2px stroke weight.

```jinja
{% import "_icons.html" as icons %}
{{ icons.icon("upload", 20) }}
```

Inline SVG avoids a font or sprite dependency and keeps `currentColor` inheritance working.
Cost: the nav icon set is duplicated between the desktop sidebar and the mobile drawer, which
is most of each page's HTML weight. Acceptable for a local prototype; the fix if it ever
matters is a `<symbol>` sprite in `base.html` plus `<use>` references.

---

## 4. Component inventory

| Component | Class | Figma equivalent |
|---|---|---|
| Card | `.card`, `.card__header`, `.card__body` | `bg-white rounded-lg border border-slate-200` |
| Hoverable card | `.card--hover` | `hover:border-blue-300 hover:shadow-md` |
| Buttons | `.btn--primary` / `--success` / `--outline` / `--ghost`, `--lg` / `--sm` / `--block` | button variants |
| Stat card | `.stat__label` / `__value` / `__delta` | dashboard stats grid |
| Quick action tile | `.action-tile` + `.bg-blue-500` etc. | `HomePage` quick actions |
| Selectable card | `.option-card` (+ `--green`) | regulation / market / language / material pickers |
| Segmented control | `.segmented` | tone selector, regulatory track switch |
| Badge / pill | `.badge--blue` / `--green` / `--amber` / `--purple` / `--slate` / `--red` | status pills |
| Alert | `.alert--blue` / `--green` / `--amber` / `--red` | privacy notice, compliance notice |
| Dropzone | `.dropzone`, `.is-active` | `DataUploadPage` drag target |
| Stepper | `.stepper`, `.is-current`, `.is-done` | `SubmissionPage` progress steps |
| Checklist | `.checklist`, `.is-done` | onboarding checklist |
| Progress bar | `.progress`, `.progress__bar`, `--thin` | dossier generation progress |
| Spinner | `.spinner` | `animate-spin` loading rings |
| Collapsible row | `.section-row`, `.is-open` | dossier section accordion |
| Permission toggle | `.perm-toggle`, `.is-on` | `SettingsPage` RBAC matrix |
| Filter chips | `.chip`, `.is-active` | news / resource category filters |
| Document card | `.doc-card` | `DocumentLibraryPage` rows |
| News card | `.news-card` | `PolicyNewsPage` articles |
| Empty state | `.empty-state` | "no documents found" |

### Two components with no Figma counterpart

- **`.prompt-preview`** — dark monospace panel showing the resolved prompt. Needed because
  the Flask app has real prompt provenance to expose; the Figma has no equivalent.
- **`.provenance`** — the three-swatch legend (client / template / expert) that labels which
  prompt layer produced which text.

---

## 5. Page mapping

| Figma page | Flask route | Divergence |
|---|---|---|
| `HomePage` | `dashboard` | Stats read live from the parsed dataset instead of fixed numbers. Checklist ticks itself from real state. |
| `DataUploadPage` | `upload` | Real multipart upload, checksums, parsing and a dataset summary panel. |
| `RegulationsPage` | `regulations` | Framework list rewritten for medical devices — MDR and AEMPS lead, since the demo is a Class IIb device rather than a drug. Selection persists to the brief. |
| `PolicyNewsPage` | `policy_news` | Feed rewritten around MDR / AEMPS / CCAA tenders. |
| `GlobalDossierPage` | `global_dossier` | Ten sections (Figma has eight — device description and regulatory status added for MDR). Progress is driven by real per-section API calls, not a timer. |
| `MSLMaterialPage` | `msl_material` | Same four material types; audiences and focus areas rewritten for diabetes care. The Figma's decorative brand-asset upload controls are replaced by a working template picker and file upload — decks export as real branded `.pptx`. |
| `DocumentLibraryPage` | `documents` | Populated from real `generation_run` rows. |
| `ResourcesPage` | `resources` | Rewritten for MDR guidance and device standards. |
| `SubmissionPage` | `submission` | Same five steps; state persists server-side in the session and writes to the brief on submit. |
| `SettingsPage` | `settings` | Same RBAC matrix, plus a provider/key status panel. Permissions are enforced server-side. |
| — | `landing` / `enter_tool` | **New.** A fork before any engagement exists: the blank tool, or the pre-loaded CGM demo. The only pages without the sidebar shell. |
| — | `audit_trail` | **New.** The append-only log the compliance story depends on. |

---

## 6. Progressive generation

The Figma fakes section-by-section progress with `setInterval`. The Flask version does it for
real: `global_dossier.html` walks the section list, POSTing each to
`/api/dossier/section` in sequence and updating that row's spinner, progress bar and status
icon as each response lands.

Each call persists a `generation_run` and an audit event, so the progress bar reflects
committed database state rather than animation. Failures mark the row red and the walk
continues to the next section.

---

## 7. Extending it

**A new page:** add a route in `app.py`, a template extending `base.html`, and one entry in
`NAV_ITEMS`. Only add pages that are *APProved* functionality — a client device's own
features are source material to be documented, not screens in this app. The bolus calculator
was briefly built as a page and removed for exactly that reason.

**A new dossier section:** add a dict to `content.DOSSIER_SECTIONS` and a builder to
`content.draft_section`. It appears in the UI, the generation walk and the library with no
further changes.

**A new provider:** add an entry to `llm.PROVIDERS`, an env var to `llm.ENV_KEYS`, and a
`_call_*` transport function. Every provider dropdown is rendered from `PROVIDERS`.

**A new colour:** add it as a `--token` in `:root` and use it through a component class.
Avoid inline hex — the token table above is what keeps the port aligned with the Figma.

**A new export format:** extend `download_document` in `app.py`, which branches on
`deliverable_type`. Slide decks already route through `core/deck.py`; a DOCX path would
follow the same shape — build bytes, write to `storage/`, log the export, `send_file`.

---

## 8. Two rules worth not breaking

Both were live defects found in QA, not hypotheticals:

- **`display` and the `hidden` attribute.** `.field`, `.alert` and friends set `display`, which
  beats the UA stylesheet's `[hidden]` rule. The global `[hidden] { display: none !important; }`
  is what keeps JS visibility toggling working. Without it the API-key fields and the dossier
  progress panel are permanently visible.
- **Inline `<span>`s inside `.option-card__body`.** They sit inside a `<label>`, so they were
  written as spans; without the explicit `display: block` they run together on one line and
  every `margin-bottom` silently does nothing. The rule now sets it for all children.
