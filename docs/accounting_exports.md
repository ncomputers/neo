# Accounting exports

Provides CSV downloads for ledger reconciliation.

## Sales register

`GET /api/outlet/{tenant}/accounting/sales_register.csv?from=YYYY-MM-DD&to=YYYY-MM-DD[&composition=true]`

Lists every invoice line item with:

- HSN/SAC code
- Quantity and price
- GST split per line (CGST/SGST/IGST)
- Per-line rounding to two decimals

Columns: `date, invoice_no, item, hsn, qty, price, taxable_value, cgst, sgst, igst, total`.

## GST summary

`GET /api/outlet/{tenant}/accounting/gst_summary.csv?from=YYYY-MM-DD&to=YYYY-MM-DD[&composition=true]`

Aggregates sales by HSN with GST totals.

Columns: `hsn, taxable_value, cgst, sgst, igst, total`.

### Composition mode

When `composition=true`, GST components are zeroed and totals equal taxable values.
