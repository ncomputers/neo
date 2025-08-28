# Billing Invoices

This module implements GST-compliant invoices and credit notes for SaaS
subscriptions.

## Numbering

Invoice numbers follow the scheme `SaaS/{FY}/{seq}` where `FY` is the
financial year such as `2025-26` and `seq` is a zero padded counter
reset every year per series. Credit notes use the `CN` series.

## Tax split

`split_tax` divides a gross amount into taxable value and CGST/SGST or
IGST depending on whether the supplier and buyer state codes match.
The default GST rate is 18%.

## SAC and configuration

The SAC code, supplier GSTIN and default series are read from
environment variables (`BILL_SAC_CODE`, `BILL_SUPPLIER_GSTIN`,
`BILL_INVOICE_SERIES`).

## Credit notes

Credit notes reference an existing invoice and store a negative amount
when refunds are issued. A PDF is rendered alongside the original
invoice and stored on disk.

## Storage

Generated PDFs are written under
`storage/billing_invoices/<tenant>/<year>/<number>.pdf`.

## Limitations

* HTML templates are minimal and intended for further styling.
* If WeasyPrint/xhtml2pdf are unavailable, the rendered HTML is saved
  with a `.pdf` extension.
* Email delivery is not wired up.

_Sample screenshots: TODO_
