# AGENTS_TODO.md
## MIRRORNODE Agents — Ground Truth Priorities

### Shared Base
- Route command execution through LUCIAN `POST /dispatch`
- Expose health surfaces honestly
- Audit runtime actions with `emit_audit()`
- Avoid documenting non-existent endpoints
- Keep repo roles aligned with real runtime boundaries

### LUCIAN (Port 7700) **Focus:** Orchestration & Manifest
- [ ] Keep `POST /dispatch` as the canonical command entry point
- [ ] Keep `/manifest` current with real lattice state
- [ ] Keep `/lattice/status` aligned with reachable node health
- [ ] Ensure dispatch actions emit canon audit records
- [ ] Tighten command registry visibility from `canon.api.commands`

### OSIRIS (Port 7701) **Focus:** Payment & Commerce
- [ ] Keep Stripe routes isolated to commerce concerns
- [ ] Maintain `/health`, `/heartbeat`, `/identity`, `/stripe/status`
- [ ] Audit checkout, invoice, refund, subscription, and webhook flows
- [ ] Keep UI shell concerns out of commerce runtime

### HERMES (Port 7702) **Focus:** Messaging & Protocol
- [ ] Implement runtime or document registry-only status clearly
- [ ] Add health endpoint when runtime exists

### THOTH (Port 7703) **Focus:** Services & Health
- [ ] Implement runtime or document registry-only status clearly
- [ ] Add health endpoint when runtime exists

### THEIA (Port 7704) **Focus:** Witness & Observation
- [ ] Implement runtime or document registry-only status clearly
- [ ] Add health endpoint when runtime exists

### PTAH (Port 7705) **Focus:** Creation & Bridge
- [ ] Implement runtime or document registry-only status clearly
- [ ] Add health endpoint when runtime exists

### EVE (Port 7706) **Focus:** Embodiment & Physical Manifest
- [ ] Implement runtime or document registry-only status clearly
- [ ] Add health endpoint when runtime exists

### Cleanup
- [ ] Remove stale references to `/system/execute`
- [ ] Remove stale references to replay and trace requirements not yet implemented
- [ ] Separate aspirational architecture from active runtime truth
