# Known issues

## Monitor URL validation and `is_site_local`

The monitor URL validation path currently references
`IPv4Address.is_site_local`, which is not available in the Python standard
library's `ipaddress` implementation. A monitor detail request can therefore
fail with an `AttributeError` when URL validation runs.

This is intentionally documented rather than fixed in this housekeeping pass.
It needs a focused security review because the validator protects the monitor
HTTP client from SSRF targets. The eventual fix should preserve the existing
private, loopback, link-local, multicast, reserved, and metadata-host blocking
behavior and add regression tests before merging.
