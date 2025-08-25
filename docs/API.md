# API

The API exposes an OpenAPI description and a ready-to-use Postman collection.

## OpenAPI

The running service serves the schema at `/openapi.json`. An exported copy lives at [`openapi.json`](../openapi.json) and includes the API title, version and server base URL.

## Postman

A collection generated from the OpenAPI schema is available at [`postman/collection.json`](../postman/collection.json).

To explore the API with Postman:

1. Open Postman and click **Import**.
2. Select the `postman/collection.json` file from this repository.
3. Postman will create a collection with requests organised by tags for easy browsing.

### Authentication

Most endpoints require a bearer token. To obtain one:

1. Send a `POST` request to `/token` with the required credentials.
2. Copy the `access_token` from the response.
3. In Postman, open the collection settings and add an `Authorization` header with the value `Bearer {{token}}`, replacing `{{token}}` with the copied token or an environment variable.

Alternatively, import the raw OpenAPI document by URL using `/openapi.json`.
