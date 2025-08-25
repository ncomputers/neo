# Soft Delete for Tables and Menu Items

Tables and menu items now support soft deletion using a `deleted_at` timestamp.
Deleted resources are hidden from standard queries and excluded from guest
operations. Admin requests may include removed records by passing the query
parameter `include_deleted=true`.

Database-level partial unique indexes ensure that active tables and menu items
do not collide on their identifiers while still allowing reuse once a record is
soft deleted.

## Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/outlet/{tenant}/tables/{code}/delete` | `PATCH` | Mark a table as deleted. Audited as `table.soft_delete`. |
| `/api/outlet/{tenant}/tables/{code}/restore` | `POST` | Restore a deleted table. Audited as `table.restore`. |
| `/api/outlet/{tenant}/menu/items/{id}/delete` | `PATCH` | Soft delete a menu item. Audited as `item.soft_delete`. |
| `/api/outlet/{tenant}/menu/items/{id}/restore` | `POST` | Restore a menu item. Audited as `item.restore`. |

Attempting to place an order on a deleted table or with a deleted menu item
returns `403` with the `GONE_RESOURCE` error code.

Exports include deleted menu items with a `status` column indicating whether
an item is `active` or `deleted`.
