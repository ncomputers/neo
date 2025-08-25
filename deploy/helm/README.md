# Neo Helm Chart

This chart deploys the Neo API, worker, and Nginx components and references an external Redis service.

## Usage

```bash
helm install neo ./neo
```

Configuration values for environment variables, resource requests, probes, and autoscaling can be adjusted in `values.yaml`.
