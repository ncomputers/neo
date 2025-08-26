# GST Engine

The `api/app/tax/gst_engine.py` module centralises GST invoice calculations. It builds an invoice from item dictionaries, applies GST/HSN data when required and ensures all monetary values are rounded to ₹0.01.

## Item lines and rounding

Each item passed to `generate_invoice` includes a `price` and may define `qty`, a GST rate, and an HSN code. When `gst_mode` is `reg` and a GST rate is present, the resulting invoice contains that rate and the optional HSN code on the item line. Line totals, accumulated taxes and the final grand total are quantised to `0.01` using `ROUND_HALF_UP`, so each amount is rounded to the nearest paise.

## GST modes

The `gst_mode` argument controls whether tax lines are produced:

- `reg` – registered businesses. GST rates are applied, tax lines are generated and, for intrastate invoices, the tax is split evenly into CGST and SGST. For interstate invoices the full amount is reported as IGST.
- `comp` – composition scheme. Item prices are retained but no tax lines are added.
- `unreg` – unregistered businesses. Like `comp`, taxes are not calculated or included.

