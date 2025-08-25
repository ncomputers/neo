# API

The API exposes an OpenAPI description and a ready-to-use Postman collection.

## OpenAPI

The running service serves the schema at `/openapi.json`. An exported copy lives at [`openapi.json`](../openapi.json).

## Postman

A collection generated from the OpenAPI schema is available at [`postman/collection.json`](../postman/collection.json).

To explore the API with Postman:

1. Open Postman and click **Import**.
2. Choose the `postman/collection.json` file from this repository.
3. Postman will create a collection with requests organised by tags for easy browsing.

Alternatively, import the raw OpenAPI document by URL using `/openapi.json`.
