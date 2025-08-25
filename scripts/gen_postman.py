import json
import sys
import uuid
from pathlib import Path


def generate(
    openapi_path: Path = Path("openapi.json"),
    output_path: Path = Path("docs/postman_collection.json"),
) -> None:
    spec_text = openapi_path.read_text()
    spec = json.loads(spec_text)
    collection = {
        "info": {
            "name": spec.get("info", {}).get("title", "API"),
            "_postman_id": str(uuid.uuid5(uuid.NAMESPACE_URL, spec_text)),
            "schema": (
                "https://schema.getpostman.com/json/collection/v2.1.0/"
                "collection.json"
            ),
        },
        "item": [],
    }

    by_tag = {}
    for path, methods in spec.get("paths", {}).items():
        for method, details in methods.items():
            tag = (details.get("tags") or ["General"])[0]
            item = {
                "name": details.get("summary", f"{method.upper()} {path}"),
                "request": {
                    "method": method.upper(),
                    "header": [],
                    "url": {
                        "raw": "{{baseUrl}}" + path,
                        "host": ["{{baseUrl}}"],
                        "path": [p for p in path.strip("/").split("/") if p],
                    },
                },
            }
            by_tag.setdefault(tag, []).append(item)

    collection["item"] = [
        {"name": tag, "item": sorted(items, key=lambda x: x["name"])}
        for tag, items in sorted(by_tag.items())
    ]
    output_path.write_text(json.dumps(collection, indent=2))


if __name__ == "__main__":
    openapi = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("openapi.json")
    output = (
        Path(sys.argv[2]) if len(sys.argv) > 2 else Path("docs/postman_collection.json")
    )
    generate(openapi, output)
