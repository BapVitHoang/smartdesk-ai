# Developer C — Change Requests & Action Items Log

> Use this file to request changes in frozen files or coordinate work across modules.
> See [`docs/requests/template.md`](./template.md) for the standard change request format.

---

## Action Item for Dev C (CR-002): Regenerate Capstone PDF & Presentation Slides

**Originator:** Integrator (`@BapVitHoang`)  
**Assignee:** Dev C (`@TKhanh`)  
**Date:** 2026-10-23  
**Status:** **Action Required upon Roster Completion**  
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
