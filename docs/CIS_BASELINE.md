# CIS Baseline

Basic hardening guidance for Linux hosts.

## SSHD
- Disable root login and enforce key-based authentication.
- Limit ciphers and MACs to modern options.
- Use `AllowUsers`/`AllowGroups` to restrict access.

## Firewall
- Default deny inbound; allow only required ports (e.g., 22, 80/443).
- Persist rules across reboots.

## Fail2Ban
- Enable the SSH jail and set sane ban times.
- Monitor logs for repeated failed attempts.

## Logrotate
- Rotate auth and application logs regularly.
- Compress and retain logs according to policy.
