ALTER TABLE billing_invoices
  ADD COLUMN number TEXT,
  ADD COLUMN fy_code TEXT,
  ADD COLUMN place_of_supply TEXT,
  ADD COLUMN supplier_gstin TEXT,
  ADD COLUMN buyer_gstin TEXT,
  ADD COLUMN sac_code TEXT,
  ADD COLUMN cgst_inr NUMERIC(10,2),
  ADD COLUMN sgst_inr NUMERIC(10,2),
  ADD COLUMN igst_inr NUMERIC(10,2),
  ADD COLUMN pdf_path TEXT;

CREATE TABLE IF NOT EXISTS billing_credit_notes(
  id BIGSERIAL PRIMARY KEY,
  invoice_id BIGINT REFERENCES billing_invoices(id) ON DELETE CASCADE,
  number TEXT,
  fy_code TEXT,
  amount_inr NUMERIC(10,2),
  tax_inr NUMERIC(10,2),
  reason TEXT,
  pdf_path TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS billing_series(
  id BIGSERIAL PRIMARY KEY,
  series TEXT NOT NULL,
  fy_code TEXT NOT NULL,
  seq INT NOT NULL DEFAULT 0,
  UNIQUE(series, fy_code)
);
