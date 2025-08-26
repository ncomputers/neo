# Pilot Survey

Use this form to collect staff feedback after the pilot.

## Questions
1. How intuitive was the ordering flow?
2. Were there any errors or delays?
3. Rate reliability on a scale of 1-5.
4. What features should be improved?
5. Additional comments?

## Submission
- Collect responses via Google Form or internal survey tool.
- Review results weekly during the pilot.
- Share a summary with stakeholders after the pilot.

## API
Submit NPS feedback via `POST /api/pilot/{tenant}/feedback` with JSON `{"score": 9, "comment": "Great"}`.
A daily cron runs `scripts/pilot_nps_digest.py` to email NPS summaries per outlet.
