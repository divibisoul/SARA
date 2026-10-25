# SARA — Public upstream integration status
**Snapshot:** 2026-10-25 · **Inspected SARA main:** `bad23bf1a3d7585d91573a584454f1683e5d2cfe`  
**Audit branch:** `audit/ai-nucleus-status-2026-10-25`

## Source pinned

| Public source | Pinned SHA | Intended use | State |
|---|---|---|---|
| [Pydantic AI](https://github.com/pydantic/pydantic-ai) | `6bc07cf18b0641ea92343d8c589cfb922108b802` | Optional typed structured-agent capability around explicit tasks | SOURCE_PINNED; runtime PROJECTED, not proven active |

## Preserve SARA's native intelligence

SARA owns regeneration, ethics, identity, memory, provenance, rollback, governance and its ARA → ETR → ITR/regenerative cycle. Pydantic AI may add typed model-assisted planning or classification only behind explicit registered handlers. It must not silently replace deterministic governance gates, memory provenance or rollback authority.

Evidence inspected:
- `integrations/capability-boundary.json` declares Pydantic AI but `runtime_state` is `PROJECTED`.
- `pyproject.toml` does not declare Pydantic AI as an application dependency, and no live adapter or authenticated Mesh transaction was observed.
- `src/sara/core/connected_runtime.py` explicitly prevents modules marked `PENDING_INFRASTRUCTURE` from being treated as active.

## Required proof

1. Pin package/source provenance and add an optional adapter behind SARA's existing module registry; don't add an always-on dependency to the core unless justified by an exact test.
2. Ensure model output is typed/validated and always passes through IdentityCore + ETR before any action.
3. Preserve source evidence, correlation, rollback hash and module status in the returned report.
4. Test the native regenerative cycle without the external provider, then test the optional provider failure path and the real provider path separately.
5. Only then connect a SARA-owned capability through Mesh and verify the authenticated response and correlation continuity.

**Gate:** `SOURCE_PINNED / ADAPTER_PLANNED / RUNTIME_UNVERIFIED`. No external model is allowed to become SARA's governance authority.
