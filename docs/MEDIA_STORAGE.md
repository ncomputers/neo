# Media Storage

## Cache headers

Media files are served with a `Cache-Control: public, max-age=86400` header. If an `ETag` is present when uploading, it is stored and returned so clients can issue conditional requests and leverage browser caching.

### CloudFront / NGINX

When fronting media with a CDN or reverse proxy, ensure the `Cache-Control` and `ETag` headers are respected.

- **CloudFront:** forward and cache based on `Cache-Control` so objects can be served from edge locations.
- **NGINX:**
  ```nginx
  location /media/ {
      add_header Cache-Control "public, max-age=86400";
      try_files $uri $uri/ =404;
  }
  ```

## S3 lifecycle

To control storage costs, configure a lifecycle policy:

- Transition objects to the Infrequent Access class after 30 days.
- Remove delete markers or noncurrent versions after 7 days.

Example JSON:

```json
{
  "Rules": [
    {
      "ID": "media-ia",
      "Filter": {"Prefix": ""},
      "Status": "Enabled",
      "Transitions": [
        {"Days": 30, "StorageClass": "STANDARD_IA"}
      ],
      "Expiration": {"Days": 7}
    }
  ]
}
```
