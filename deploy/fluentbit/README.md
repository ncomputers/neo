# Fluent Bit

Ship Neo JSON logs to multiple targets with Fluent Bit.

## Configuration

`fluent-bit.conf` tails `/var/log/neo/*.log`, parses JSON and forwards logs to:

- stdout
- an OTLP endpoint on `127.0.0.1:4318` via HTTP
- an HTTP endpoint at `http://127.0.0.1:8080/logs`

## systemd service

Example unit file `/etc/systemd/system/fluent-bit.service`:

```ini
[Unit]
Description=Fluent Bit log forwarder

[Service]
ExecStart=/usr/bin/fluent-bit -c /etc/fluent-bit/fluent-bit.conf
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now fluent-bit
```
