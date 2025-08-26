# Accounting export tests

Covers CSV exports for sales register and GST summaries.

Fixtures seed:

- Intra-state invoice with CGST+SGST split.
- Inter-state invoice with IGST.

Tests assert per-line GST values, totals and composition-mode behaviour.
