# UAT Checklist

## Guest flow: scan→menu→add→place→bill→pay
- **Expected Result:** Guest completes full ordering and payment without errors.
- [ ] Pass    [ ] Fail

## Split payments, coupons, tips
- **Expected Result:** System handles split payments, applies coupons, and records tips correctly.
- [ ] Pass    [ ] Fail

## QR rotate + re-scan
- **Expected Result:** Rotating QR codes remain scannable and session persists after re-scan.
- [ ] Pass    [ ] Fail

## Offline add→reconnect→batch ingest
- **Expected Result:** Orders added offline sync correctly once connection restores and appear in batch ingest.
- [ ] Pass    [ ] Fail

## Hotel mode tasks (if enabled)
- **Expected Result:** Hotel-specific flows (room lookup, folio posting) operate as designed.
- [ ] Pass    [ ] Fail

## Day close & digest
- **Expected Result:** End-of-day close generates digest without discrepancies.
- [ ] Pass    [ ] Fail

## Exports (with resume cursor)
- **Expected Result:** Export jobs complete and can resume from cursor position.
- [ ] Pass    [ ] Fail

## Soft-delete table & item
- **Expected Result:** Delete a table and a menu item; orders are blocked while deleted and succeed once restored.
- [ ] Pass    [ ] Fail

## Quota boundaries
- **Expected Result:** Hit quotas for tables, menu items, images, and exports; expect 403 FEATURE_LIMIT with an upgrade hint.
- [ ] Pass    [ ] Fail

