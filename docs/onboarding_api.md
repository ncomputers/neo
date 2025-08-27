# Onboarding API

The onboarding wizard exposes REST endpoints to persist setup progress.

## GET `/api/onboarding/{id}`
Returns the current session data including `current_step` and any saved
sections.

## POST `/api/onboarding/start`
Creates a new session and returns an `onboarding_id`.

## POST `/api/onboarding/{id}/profile`
Stores basic outlet profile and sets `current_step` to `profile`.

## POST `/api/onboarding/{id}/tax`
Stores tax settings and sets `current_step` to `tax`.

## POST `/api/onboarding/{id}/tables`
Allocates table codes and sets `current_step` to `tables`.

## POST `/api/onboarding/{id}/payments`
Persists payment configuration and sets `current_step` to `payments`.

All progress is saved to a lightweight SQLite store so sessions survive process
restarts. Fetching a session automatically creates it if absent, allowing the
wizard to resume from the last recorded step.
