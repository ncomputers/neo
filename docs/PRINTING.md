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
