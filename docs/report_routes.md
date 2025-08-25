# Report Routes

Owner and compliance reporting endpoints.

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/outlet/{tenant}/reports/daybook.pdf?date=YYYY-MM-DD | Owner daybook summary with totals, payment mix and top items (PDF/HTML). |
| GET | /api/outlet/{tenant}/reports/z?date=YYYY-MM-DD&format=csv | Daily Z-report in CSV format. |
| GET | /api/outlet/{tenant}/reports/gst/monthly?month=YYYY-MM&gst_mode=reg | Monthly GST summary. |
| POST | /api/outlet/{tenant}/digest/run?date=YYYY-MM-DD | Trigger daily KPI digest notification (admin-only). Returns channels used. |
| GET | /api/outlet/{tenant}/staff/shifts?date=YYYY-MM-DD&format=csv | Staff shift summary with logins, KOT accepted, tables cleaned, voids and total login time. |
