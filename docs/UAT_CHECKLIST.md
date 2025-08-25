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
- **Expected Result:** Deleted tables or items block new orders until restored; restoring re-enables ordering.
- [ ] Pass    [ ] Fail

## Quota boundaries
- **Expected Result:** Hitting quota limits returns FEATURE_LIMIT hints.
- [ ] Pass    [ ] Fail

