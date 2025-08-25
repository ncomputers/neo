# ESC/POS Printing

Experimental notes on working with thermal printers in labs.

## Sending bytes on Linux

Generate ticket bytes and pipe them directly to a device:

```bash
curl -o ticket.bin "http://localhost:8000/api/outlet/demo/print/test?size=80mm"
# USB printers
cat ticket.bin | sudo tee /dev/usb/lp0 > /dev/null
# Serial printers
cat ticket.bin | sudo tee /dev/ttyS0 > /dev/null
```

The device paths vary by system; check `dmesg` or `lsusb` for the correct node.

## Safety

Printing raw bytes can cut paper or trigger cash drawers. Use a test printer in a
controlled environment and never send untrusted data to a device connected to a
live till.

## Fallbacks

If no printer is available, render the ticket as PDF or HTML and preview it in a
browser before sending it to hardware.

## Bridge mode

For production setups a lightweight bridge listens for print events and relays
them to a local ESC/POS device. The API publishes compact JSON messages on
`print:kot:{tenant}` whenever `/api/outlet/{tenant}/print/notify` is called.
An example agent in Python:

```python
import asyncio, json
import redis.asyncio as redis
from escpos.printer import Serial

async def main():
    r = redis.from_url("redis://localhost/0")
    p = Serial(devfile="/dev/usb/lp0")
    pubsub = r.pubsub()
    await pubsub.subscribe("print:kot:demo")
    async for msg in pubsub.listen():
        if msg["type"] != "message":
            continue
        data = json.loads(msg["data"])
        # send ESC/POS commands based on ``data``
        p.text(f"KOT {data['order_id']}\n")
        p.cut()

asyncio.run(main())
```

### systemd unit

```
[Unit]
Description=KOT print bridge
After=network.target

[Service]
ExecStart=/usr/bin/python3 /opt/kot_bridge.py
Restart=on-failure
User=pi
WorkingDirectory=/opt

[Install]
WantedBy=multi-user.target
```
