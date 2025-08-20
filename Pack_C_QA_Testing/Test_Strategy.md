# Test Strategy

## Levels
- Unit (logic, utils)
- Integration (API + DB + Redis)
- E2E (Guest PWA, KDS, Billing)
- Non-functional (load/soak, offline/online switching)

## Tools
- Pytest, Playwright, Locust (optional), Docker test env.

## Coverage Targets
- Core modules > 70% statements; critical paths 90%.
