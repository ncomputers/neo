# DB Indexing

This project relies on a focused set of indexes to keep multi-tenant queries fast while avoiding bloat. The tables below list each index, the code that benefits from it, the shape of the filtered query, and why a partial, GIN, BRIN or INCLUDE clause is used.

**Note:** Run `make analyze-hot` after big seeding/import to refresh planner statistics.

## Orders
| Index | Route/Repo benefiting | WHERE clause shape | Notes |
| --- | --- | --- | --- |
| `idx_orders_tenant_status_created` | KDS board ([`api/app/routes_kds.py`](../api/app/routes_kds.py)) | `tenant_id=? AND status=? AND deleted_at IS NULL ORDER BY created_at DESC` | Partial to skip soft deletes, INCLUDE `(total_amount, table_id)` for index-only fetches |
| `idx_orders_tenant_table_open` | Guest order lookups ([`api/app/routes_guest_order.py`](../api/app/routes_guest_order.py)) | `tenant_id=? AND table_id=? AND closed_at IS NULL AND deleted_at IS NULL ORDER BY created_at DESC` | Partial to ignore closed/deleted rows |
| `ux_orders_tenant_idempotency` | Batch ingestion ([`api/app/routes_orders_batch.py`](../api/app/routes_orders_batch.py)) | `tenant_id=? AND idempotency_key IS NOT NULL` | Partial UNIQUE enforces idempotent inserts |
| `brin_orders_created` | Exports & analytics ([`scripts/exports`](../scripts)) | `created_at BETWEEN ? AND ?` | BRIN suits large append-only range scans |

## Order Items
| Index | Route/Repo benefiting | WHERE clause shape | Notes |
| --- | --- | --- | --- |
| `idx_order_items_order` | Order item joins ([`orders_repo_sql`](../api/app/repos_sqlalchemy/orders_repo_sql.py)) | `order_id=?` | Speeds joining items to their order |
| `idx_order_items_tenant_menuitem` | Menu analytics ([`dashboard_repo_sql`](../api/app/repos_sqlalchemy/dashboard_repo_sql.py)) | `tenant_id=? AND menu_item_id=? AND deleted_at IS NULL` | Partial to exclude soft deletes |

## Payments
| Index | Route/Repo benefiting | WHERE clause shape | Notes |
| --- | --- | --- | --- |
| `idx_payments_tenant_order_status` | Settlement lookups ([`invoices_repo_sql`](../api/app/repos_sqlalchemy/invoices_repo_sql.py)) | `tenant_id=? AND order_id=? AND status=? AND deleted_at IS NULL` | Partial for live payments only |
| `ux_payments_tenant_utr` | Payment UTR checks ([`routes_guest_order.py`](../api/app/routes_guest_order.py)) | `tenant_id=? AND utr IS NOT NULL` | Partial UNIQUE prevents duplicate references |

## Menu Items
| Index | Route/Repo benefiting | WHERE clause shape | Notes |
| --- | --- | --- | --- |
| `idx_menu_tenant_category_active` | Category listing ([`menu_repo_sql.list_by_category`](../api/app/repos_sqlalchemy/menu_repo_sql.py)) | `tenant_id=? AND category_id=? AND is_active=TRUE AND deleted_at IS NULL ORDER BY sort_order` | Partial to drop inactive entries |
| `gin_menu_dietary` | Dietary filters ([`menu_repo_sql`](../api/app/repos_sqlalchemy/menu_repo_sql.py)) | `coalesce(dietary,'[]') ?/?|` | GIN accelerates JSONB membership tests |
| `gin_menu_allergens` | Allergen filters ([`menu_repo_sql`](../api/app/repos_sqlalchemy/menu_repo_sql.py)) | `coalesce(allergens,'[]') ?/?|` | GIN accelerates JSONB membership tests |
| `gin_menu_tags` | Tag filters ([`menu_repo_sql`](../api/app/repos_sqlalchemy/menu_repo_sql.py)) | `coalesce(tags,'[]') ?/?|` | GIN accelerates JSONB membership tests |
| `gin_menu_search` | Menu search ([`menu_repo_sql.search`](../api/app/repos_sqlalchemy/menu_repo_sql.py)) | `search_tsv @@ plainto_tsquery(...)` | GIN full-text search |

## Tables
| Index | Route/Repo benefiting | WHERE clause shape | Notes |
| --- | --- | --- | --- |
| `ux_tables_tenant_code_live` | Table lookup ([`orders_repo_sql.create_order`](../api/app/repos_sqlalchemy/orders_repo_sql.py)) | `tenant_id=? AND table_code=? AND deleted_at IS NULL` | Partial UNIQUE ensures one active code per tenant |
| `idx_tables_tenant_state_updated` | Table state polling ([`routes_table_map_sse.py`](../api/app/routes_table_map_sse.py)) | `tenant_id=? AND state=? ORDER BY updated_at DESC` | Timestamp gives most-recent-first results |

## Webhook Events
| Index | Route/Repo benefiting | WHERE clause shape | Notes |
| --- | --- | --- | --- |
| `idx_webhooks_tenant_due` | Webhook retry worker ([`scripts/notify_worker.py`](../scripts/notify_worker.py)) | `tenant_id=? AND state='pending' AND next_attempt_at<=?` | Partial skips completed hooks |

## Exports
| Index | Route/Repo benefiting | WHERE clause shape | Notes |
| --- | --- | --- | --- |
| `idx_exports_tenant_created` | Export listings ([`api/app/routes_exports.py`](../api/app/routes_exports.py)) | `tenant_id=? ORDER BY created_at DESC` | DESC ordering returns newest jobs first |

## Audit Log
| Index | Route/Repo benefiting | WHERE clause shape | Notes |
| --- | --- | --- | --- |
| `brin_audit_created` | Audit exports ([`scripts/audit_dump.py`](../scripts/audit_dump.py)) | `created_at BETWEEN ? AND ?` | BRIN is tiny and ideal for append-only logs |

Monthly partitions (`audit_log_yYYYYmMM`) keep the table lean. Remove old partitions with `scripts/audit_partition_retention.py` (run with `--keep-months` to control retention).

## Devices
| Index | Route/Repo benefiting | WHERE clause shape | Notes |
| --- | --- | --- | --- |
| `ux_devices_tenant_fingerprint` | Device registration ([`routes_devices.py`](../api/app/routes_devices.py)) | `tenant_id=? AND fingerprint IS NOT NULL AND deleted_at IS NULL` | Partial UNIQUE deduplicates devices |

## Promos
| Index | Route/Repo benefiting | WHERE clause shape | Notes |
| --- | --- | --- | --- |
| `idx_promos_tenant_code_active` | Promo application ([`routes_promos.py`](../api/app/routes_promos.py)) | `tenant_id=? AND code=? AND is_active=TRUE AND deleted_at IS NULL` | Partial keeps index small |

## Rate Limits
| Index | Route/Repo benefiting | WHERE clause shape | Notes |
| --- | --- | --- | --- |
| `idx_ratelimit_tenant_ip_window` | Guest rate limiting ([`guest_rate_limit`](../docs/guest_rate_limit.md)) | `tenant_id=? AND ip=? AND window_start=?` | Btree lookup for throttling |

## How to verify
1. Populate sample data: `python scripts/seed_large_outlet.py`
2. Run the plan check: `pytest api/tests/test_indexes_explain.py`
3. Compare query plans against baselines with `python scripts/plan_guard.py baseline.json new_run.json`
