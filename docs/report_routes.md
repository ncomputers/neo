# Report Routes

Owner and compliance reporting endpoints.

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/outlet/{tenant}/reports/daybook.pdf?date=YYYY-MM-DD | Owner daybook summary (PDF/HTML). |
| GET | /api/outlet/{tenant}/reports/z?date=YYYY-MM-DD&format=csv | Daily Z-report in CSV format. |
| GET | /api/outlet/{tenant}/reports/gst/monthly?month=YYYY-MM&gst_mode=reg | Monthly GST summary. |
