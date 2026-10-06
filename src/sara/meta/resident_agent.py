from __future__ import annotations

SARA_RESIDENT_AGENT = {
    "id": "SARA.resident",
    "name": "Agent-Regeneration Steward",
    "nucleus": "SARA",
    "version": "1.0.0",
    "role": "audit-ethics-regeneration-memory-governance",
    "execution_mode": "embedded-local-runtime",
    "lifecycle": "BOUND",
    "published_capabilities": [
        "sara.audit@1.0.0",
        "sara.regenerate@1.0.0",
        "sara.cycle@1.0.0",
        "sara.state@1.0.0",
        "sara.trace@1.0.0",
        "mem0.status@1.0.0",
        "mem0.add@1.0.0",
        "mem0.search@1.0.0",
        "mem0.list@1.0.0",
        "external.capability.resolve@1.0.0",
        "external.capability.fabric.describe@1.0.0",
    ],
    "upstream_provider_count": 25,
    "external_fabric": "soul_external_fabric",
    "authority": "SARA owns regeneration, governance, evidence and memory-boundary decisions; external providers amplify these capabilities.",
}
