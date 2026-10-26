# Developer C — Change Requests Log

> Use this file to request changes in frozen files or files owned by other workstreams.
> See [`docs/requests/template.md`](./template.md) for the standard change request format.

---

# Change Request: CR-001 - Update AI_USAGE.md with Real Failure Case Studies & Extend Dev C Ownership Mapping

**Author / Developer:** Dev C (Frontend UX, QA & Capstone Documentation)  
**Date:** 2026-10-22  
**Status:** DONE (`scripts/ownership_map.py` mapped on `Hoang`; `AI_USAGE.md` composed in Prompt 4 Task 4)  
**Target Frozen File(s):**
- `AI_USAGE.md` (Integrator-owned)
- `scripts/ownership_map.py` (Integrator-owned)

---

## 1. Reason for Change
1. **REQ-28 Compliance:** The project specification requires `AI_USAGE.md` to document at least 2 real AI failure cases with exact evidence and commit hashes (Auth bypass / unverified JWT and Gemini 400 parameter failure).
2. **REQ-34, REQ-40, REQ-41 Deliverables:** Dev C is mandated by project instructions to produce:
   - Visual verification evidence screenshots in `docs/evidence/`
   - Formal capstone report PDF: `docs/REPORT.pdf`
   - Presentation defense deck: `docs/SLIDES.pptx` and `docs/SLIDES.pdf`
   - Video demo checklist: `docs/DEMO_VIDEO_CHECKLIST.md`
   These files need to be explicitly mapped to `devC` in `scripts/ownership_map.py` to satisfy automated ownership verification.

---

## 2. Proposed Changes

### 2.1 scripts/ownership_map.py
Add the following file patterns to `OWNERSHIP_MAP["devC"]`:
```python
        "docs/evidence/*",
        "docs/DEMO_VIDEO_CHECKLIST.md",
        "docs/REPORT.pdf",
        "docs/SLIDES.pdf",
        "docs/SLIDES.pptx",
```

### 2.2 AI_USAGE.md
Incorporate Case Studies 4 and 5:
- **Case Study 4 (Dev B Auth Module):** AI generated login endpoint accepting any password and decoding Google ID tokens without signature verification (`verify_signature=False`), fixed in commit `eef0af827d1904bf24d86c0cbfbc6508cc04a290`.
- **Case Study 5 (Dev A AI Engine):** AI generated Gemini API request with unsupported parameter structure leading to HTTP 400 client error, fixed in commit `192fecc` / `afbb08d`.

---

## 3. Impact Analysis
- **Backward Compatibility:** Zero breaking changes.
- **Module Impact:** Governance and documentation only. Does not touch backend runtime or frontend core logic.

---

## 4. Integration Review
- [x] Reviewed by Lead / Integration Owner (Hoang)
- [x] Verified with `python -m pytest backend/tests/test_api.py backend/tests/common -v`
- [x] Verified with `npm run lint --prefix frontend && npm run build --prefix frontend`

---

# Action Item for Dev C: CR-002 - Regenerate Capstone PDF & Presentation Slides

**Originator:** Integrator (`@BapVitHoang`)  
**Assignee:** Dev C (`@TKhanh`)  
**Date:** 2026-10-23  
**Status:** **LEFT FOR OWNER (`docs/TEAM_ROSTER.md` now has `verified_by_user = True`; regenerate binaries in Prompt 5)**  
**Target Deliverables (Owned by Dev C):**
- `docs/REPORT.pdf`
- `docs/SLIDES.pdf`
- `docs/SLIDES.pptx`

### 1. Reason & Background
During the pre-release release audit, an anti-fabrication scan detected that earlier versions of `docs/REPORT.pdf` (page 1), `docs/SLIDES.pdf` (page 1), and `docs/SLIDES.pptx` (slide 1) contained fabricated student names and unverified student IDs.

All markdown source files on the integration branch (`README.md`, `docs/PROPOSAL.md`, `docs/REPORT.md`) have now been purged and updated with neutral GitHub handles referencing [`docs/TEAM_ROSTER.md`](../TEAM_ROSTER.md).

### 2. Action Required by Dev C
1. Wait for the user/instructor to populate official verified Full Names and Student IDs (MSSV) in [`docs/TEAM_ROSTER.md`](../TEAM_ROSTER.md) (or maintain neutral GitHub identifiers if left empty).
2. Regenerate `docs/REPORT.pdf` from the updated `docs/REPORT.md`.
3. Regenerate `docs/SLIDES.pdf` and `docs/SLIDES.pptx` with title slides matching [`docs/TEAM_ROSTER.md`](../TEAM_ROSTER.md).
4. Verify that `python scripts/check_roster.py` passes with zero violations before committing on `feature/c-frontend-docs`.
