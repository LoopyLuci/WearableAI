# Security policy

## Reporting security vulnerabilities

Report vulnerabilities privately by opening a GitHub Security Advisory in this repository.

Do not open public issues for security vulnerabilities.

## Scope

- Firmware: `arp-2040/firmware`
- Host tools: `arp-2040/host-tools`
- MCP toolkit: `arduino-mcp-toolkit`
- Dashboard: `arduino-dashboard`

## Expectations

- Security-sensitive changes should include a short rationale in the PR.
- OTA and signing paths should not regress ATECC608A or mbedTLS behavior.
- Patch releases for security issues are preferred over breaking changes.
