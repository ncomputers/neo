# Rate Limit & Blocklist Policy

- Guest APIs: 60 req/min/IP (burst 100).  
- After 3 **rejected** orders within 24h from same IP → blocklist for 24h (configurable).  
- Allow unblock by Super-Admin.
