# Known issues

## Monitor URL validation and `is_site_local` — resolved

Resolved in commit `fix: correct SSRF IP validation attribute error`. The
invalid `IPv4Address.is_site_local` reference was removed. Validation now uses
the supported `ipaddress` attributes for private, loopback, link-local,
multicast, reserved, and unspecified IPv4 and IPv6 addresses.

Regression tests cover literal private, loopback, link-local, and legitimate
public IP URLs. The validator continues to reject local and metadata hostnames
and preserves the existing SSRF protection behavior.
