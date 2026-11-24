# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 1.x | Yes |
| Earlier, unversioned code | No |

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting on this repository if it is enabled. If it is not, open an issue that asks for a private contact and leave out the technical details.

## Scope

`m15` is a local command-line tool. It opens no network connections and handles no credentials. Treat input files as untrusted; the parser is designed for that. See [docs/SECURITY_AUDIT.md](docs/SECURITY_AUDIT.md).
