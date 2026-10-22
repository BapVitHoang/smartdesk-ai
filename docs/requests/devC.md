# Developer C — Change Requests Log

> Use this file to request changes in frozen files or files owned by other workstreams.
> See [`docs/requests/template.md`](./template.md) for the standard change request format.

---

# Change Request: CR-001 - Update AI_USAGE.md with Real Failure Case Studies & Extend Dev C Ownership Mapping

**Author / Developer:** Dev C (Frontend UX, QA & Capstone Documentation)  
**Date:** 2026-10-22  
**Status:** Approved by Integrator  
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

