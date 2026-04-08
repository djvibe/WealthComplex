# Security Review (2026-04-08)

This document captures a quick static security review of the `wealthgrabber` codebase.

## Scope

Reviewed:
- Source code under `src/wealthgrabber`
- Packaging metadata in `pyproject.toml`
- Tests for behavioral clues

## Findings Summary

### No obvious malicious behavior found

The code appears to be a straightforward CLI wrapper around `ws-api`:
- Prompts for credentials using `getpass`.
- Persists session tokens to OS keyring.
- Uses API client methods to fetch accounts, activities, and positions.
- Prints data in table/json/csv formats.

No direct indicators of malware/backdoors were found, including:
- No shell execution (`os.system`, `subprocess`).
- No dynamic code execution (`eval`, `exec`).
- No filesystem exfiltration logic.
- No outbound calls to arbitrary hosts in this repository code.

### Security-relevant observations

1. **Trust boundary is the `ws-api` dependency**
   - Authentication and API transport are delegated to `ws-api`.
   - This repository does not implement custom crypto or HTTP request handling directly.

2. **Session handling behavior**
   - Session JSON is stored in keyring under a service-scoped key and can be reused for future logins.
   - Cached email is also stored in keyring for convenience.

3. **Exception output may include sensitive details**
   - Some broad exception handlers print raw exception text, which could expose sensitive values in edge cases depending on upstream exceptions.

4. **Dependency hygiene concerns**
   - Dev dependency list includes duplicate `memvid-sdk` entries with different minimum versions.
   - `requests` is declared but not directly used in this repository code (possibly transitively expected).

## Recommended hardening before production use

1. Pin and review exact dependency versions (especially `ws-api`, `keyring`, `typer`).
2. Run dependency audit tooling (`pip-audit`/`uv` equivalent) in CI.
3. Reduce verbose/raw exception printing for auth flows.
4. Consider adding a minimal SECURITY.md with threat model and data handling notes.
5. Validate provenance of the upstream `ws-api` package (publisher, release history, signatures/checksums).

## Reviewer note

This review is static and does not include runtime network inspection. It increases confidence but cannot guarantee absence of malicious behavior in transitive dependencies or remote APIs.

## WS-API package scan (local installed copy)

I also scanned the installed `ws-api` package currently resolved in this environment.

### Version and provenance observed

- Locked package: `ws-api==0.30.0`
- Registry: PyPI (`https://pypi.org/simple`)
- Locked wheel hash: `sha256:cd018de1a1e02188b23f90b5d837752a359eb597e7b26444ead7e12e878fc606`

### Static code findings in `ws-api`

- No use of `eval`/`exec`, `subprocess`, or `os.system` in inspected package files.
- Network behavior appears limited to Wealthsimple endpoints:
  - `https://api.production.wealthsimple.com/v1/oauth/v2`
  - `https://my.wealthsimple.com/graphql`
  - `https://my.wealthsimple.com/app/login`
- Tokens are handled in memory and serialized via `WSAPISession.to_json()` for optional persistence by caller-provided callback.

### Notes

- This does **not** prove safety of future releases; re-run scans after dependency updates.
- Dynamic/runtime exfiltration cannot be fully ruled out by static reading alone.
- Package-level vulnerability audit tooling (`pip-audit`) could not be executed in this environment due outbound connectivity restrictions.
