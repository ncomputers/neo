# Load & Soak Plan

- Peak: 50 tables active, 10 orders/minute, 200 WS clients.
- Goals: API p95 < 700 ms; zero data loss; KDS latency < 1s.
- Soak: 6 hours continuous with rotating orders; monitor memory/cpu.
