# Data Model (ERD - Mermaid)

```mermaid
erDiagram
  OUTLETS ||--o{ TABLES : has
  OUTLETS ||--o{ OUTLET_STAFF : employs
  TABLES ||--o{ ORDERS : runs
  ORDERS ||--o{ ORDER_ITEMS : contains
  ORDERS ||--o{ INVOICES : generates
  INVOICES ||--o{ PAYMENTS : records
  MENU_CATEGORIES ||--o{ MENU_ITEMS : groups
  CUSTOMERS ||--o{ INVOICES : billed_to
  
  OUTLETS { uuid id PK
            uuid tenant_id
            text name
            text domain
            text tz
            text gst_mode
            text rounding }
  TABLES { uuid id PK
           uuid outlet_id FK
           text code
           text qr_token }
  MENU_ITEMS { uuid id PK
               uuid category_id FK
               text name
               numeric price
               bool is_veg
               numeric gst_rate
               text hsn_sac
               bool show_fssai
               bool out_of_stock }
  ORDERS { uuid id PK
           uuid table_id FK
           text status
           timestamptz placed_at
           timestamptz accepted_at
           timestamptz ready_at
           timestamptz served_at }
  ORDER_ITEMS { uuid id PK
                uuid order_id FK
                uuid item_id FK
                text name_snapshot
                numeric price_snapshot
                int qty
                text status }
  INVOICES { uuid id PK
             uuid order_group_id
             text number UNIQUE
             jsonb bill_json
             jsonb gst_breakup
             numeric total
             text mode
             timestamptz created_at }
  PAYMENTS { uuid id PK
             uuid invoice_id FK
             text mode
             numeric amount
             text utr
             bool verified
             timestamptz created_at }
```
