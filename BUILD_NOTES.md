# APProved — Python Prototype Build Notes

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Copy env file

```bash
cp .env.example .env
```

(Optional — the app will work with defaults.)

### 3. Launch

```bash
python app.py
```

The server starts on `http://localhost:5000` and your browser opens automatically.

---

## What's Implemented

### Client View (✓ Complete)
- **Consent flow** — audit logging consent gate runs first
- **Engagement creation** — client creates a new engagement
- **File upload** — drag-and-drop or browse; every file gets a SHA-256 checksum
- **Specification form** — client fills in tone, audience, regulations, markets, languages, key messages, brand assets
- **Brief versioning** — specifications are stored as immutable versioned briefs
- **Review & summary** — client sees the full brief before it goes to the expert team

### User View (✓ Core flows, generation pending)
- **Engagement list** — expert sees all engagements ready for work
- **Inherited context** — expert views the client's brief (read-only)
- **Prompt workspace** — three-layer composition:
  - Layer 1: Client baseline (with per-field injection toggles)
  - Layer 2: Deliverable template (auto-generated)
  - Layer 3: Expert overlay (editable)
- **Model selection** — choose provider (Anthropic, OpenAI, Google) and model
- **API key handling** — user provides key for this run (never stored)

### Audit Trail (✓ Complete)
- **Append-only database** — immutable records of every action
- **Event types** — consent, upload, brief creation, prompt composition
- **Traceability** — every event tagged with actor, timestamp, and references

### Database (✓ SQLite with full schema)
- Engagement, BriefVersion, UploadedFile, GenerationRun, ReviewRound, AuditEvent
- Versioned briefs with change tracking
- File checksums for reproducibility

---

## What's Next

These will be wired in Phase 2:

1. **Generation** — POST to `/api/generate/` runs the LLM via Anthropic/OpenAI/Google SDK
2. **Judge scoring** — automated compliance check before human review
3. **Review loops** — internal expert review + client feedback rounds
4. **Branded export** — DOCX with client's brand template

---

## Project Structure

```
app.py                    # Main entry point — python app.py launches server & browser
core/
  models.py               # SQLAlchemy ORM + audit trail schema
  audit.py                # Append-only event logging
  briefs.py               # Brief versioning + field diffs
  gates.py                # Consent + data quality gates
  llm.py                  # Provider abstraction (stub — ready for phase 2)
templates/
  base.html               # Base layout
  index.html              # Landing page
  client/
    index.html            # Client engagements list
    new_engagement.html
    consent.html
    upload.html
    specification.html
    review.html
  user/
    index.html            # User engagements list
    context.html          # View client brief
    prompt.html           # Compose prompt
  404.html, 500.html
static/
  css/
    style.css             # Global styles + responsive layout
storage/
  .gitkeep
requirements.txt
.env.example
BUILD_NOTES.md (this file)
```

---

## Testing the Flow

### Client Side
1. Navigate to `/client`
2. Create new engagement → "Acme Therapeutics"
3. Provide consent to audit logging
4. Upload a sample file (efficacy, safety, etc.)
5. Fill in specifications (tone, markets, regulatory, etc.)
6. Review brief

### User Side
1. Navigate to `/user`
2. See the client's engagement listed
3. Click "View" to see the brief (read-only context)
4. Click "Compose Prompt" to try the prompt workspace
5. Layer 1 shows client baseline; Layer 3 is your editable overlay
6. Select a provider and model

Every action is logged to the audit trail. Check `storage/approved.db` (SQLite) to see records.

---

## Database

SQLite file is at `storage/approved.db`. To inspect:

```bash
sqlite3 storage/approved.db
> .tables
> SELECT * FROM audit_event;
> .exit
```

---

## API & Generation (Stub)

The `/user/<engagement_id>/prompt` POST endpoint currently logs the prompt composition but doesn't invoke LLM generation. Phase 2 will wire this up using `core/llm.py` with provider clients.

---

## Notes for Phase 2

- **Parallel drafting** — split generation into per-section calls (drafting.py from the main repo)
- **Judge scoring** — automated rubric before human review (judge.py)
- **Review loops** — internal expert + client feedback with brief amendment support (review.py)
- **DOCX export** — brand template support (docx_export.py)

---

## Troubleshooting

**"Port 5000 already in use"**
- Kill the process: `lsof -ti:5000 | xargs kill -9`
- Or edit `app.py` to change the port

**"Database locked"**
- Close any open SQLite connections
- Delete `storage/approved.db` and restart (development only)

**"Template not found"**
- Verify the `templates/` directory exists and templates are there
- Check Flask `template_folder` in `app.py`

---

## Architecture Notes

The two-view split (Client + User) is deliberate and mirrors `review.py`'s evaluator-optimizer pattern:

- **Client view** collects requirements and provides feedback
- **User view** (APProved expert) composes prompts and iterates
- **Audit trail** makes both sides accountable and traceability reproducible

API keys are never stored — they're session-scoped and redacted from audit logs.

Client text (requirements, files, feedback) is treated as *data, not instructions* — never sent directly to the LLM as prompt commands.
