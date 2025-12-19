# THOTH-SYS: System Integrity Verifier
Validates builds, schemas, and operational readiness.

## Verification Checks
- Bridge node health (deps, port, schema validation, endpoints respond)
- File structure integrity (required files present, hierarchy correct)
- Integration points (HUD connectivity, event log access)
- Deployment readiness (env vars set, deps resolved, launch scripts executable)
