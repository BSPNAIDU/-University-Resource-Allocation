

## Submission-critical fixes applied (November 2026)

- Bulk classroom import now skips classrooms that already exist for the logged-in university and inserts only new classrooms.
- The Resources page reports added and skipped classroom counts rather than rejecting the entire form.
- Room-unavailability reallocation is grouped by `session_id`, checks actual session overlap, preserves unaffected allocations, and writes the required `session_id` on every replacement allocation.
- The Seat Allocation page uses the existing `api_client` import convention and normalizes the session response once.
- The Reallocation page reflects the existing automatic reallocation behaviour triggered by changing room availability.
- New timetable sessions use the logged-in university's current available classroom capacity (300 only as a fallback when no rooms exist).

These changes preserve the existing FastAPI + Streamlit application and its university-scoped database design. No database reset is required for these source changes.
