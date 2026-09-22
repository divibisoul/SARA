"""SARA runtime self-check.

Deterministic diagnostics for local CI failures. This is not a replacement
for pytest; it exposes the first abort point and HTTP error payload when the
full suite fails.
"""
from __future__ import annotations

import json
import os
import threading
import urllib.error
import urllib.request

from sara.bootstrap import build_default_system
from sara.core.itr import ITR
from sara.core.etr import ETR
from sara.core.provenance import ProvenanceTracker
from sara.memory import DNA_Tags, TemporalVectorDB, RegenerativeMemory
from sara.security import IdentityCore, EmergencyRollback, EthicalFilterChain
from sara.governance import UbuntuEthics, BuenVivir
from sara.regeneration import RegenerativeLoop
from sara.service.http_api import create_server


def dump(label: str, value) -> None:
    print(f"SELF_CHECK::{label}::{json.dumps(value, ensure_ascii=False, default=str)}")


def plain_loop_check() -> None:
    prov = ProvenanceTracker()
    dna = DNA_Tags()
    temporal = TemporalVectorDB()
    memory = RegenerativeMemory()
    ara = __import__("sara.core", fromlist=["ARA"]).ARA(dna, temporal, prov)
    identity = IdentityCore(prov)
    ubuntu = UbuntuEthics()
    buen = BuenVivir()
    etr = ETR(identity, ubuntu, buen, prov)
    itr = ITR(prov)
    filters = EthicalFilterChain()
    filters.register(ubuntu)
    filters.register(buen)
    rollback = EmergencyRollback()
    loop = RegenerativeLoop(
        ara, etr, itr, identity, memory, temporal, dna, filters, rollback
    )
    report = loop.run("promover autonomia comunitária", cycle_id="selfcheck-plain")
    dump("PLAIN_LOOP", {
        "converged": report.converged,
        "rollback": report.rollback_performed,
        "cycles": report.cycles,
        "context_phases": [s["phase"] for s in report.context_steps],
        "execution_report": report.execution_report,
    })


def full_loop_check() -> None:
    system = build_default_system(fail_closed=True)
    report = system.sistema_vivo.process(
        "promover autonomia comunitária", cycle_id="selfcheck-full"
    ).loop_report
    dump("FULL_LOOP", {
        "converged": report.converged,
        "rollback": report.rollback_performed,
        "cycles": report.cycles,
        "context_phases": [s["phase"] for s in report.context_steps],
        "execution_report": report.execution_report,
    })


def http_check() -> None:
    os.environ["SARA_API_TOKEN"] = "selfcheck-token-123456789"
    server = create_server("127.0.0.1", 0, fail_closed=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        request = urllib.request.Request(
            f"http://{host}:{port}/v1/capabilities",
            headers={"Authorization": "Bearer selfcheck-token-123456789"},
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                raw = response.read()
                dump("HTTP_CAPABILITIES", {
                    "status": response.status,
                    "body": raw.decode("utf-8", "replace"),
                })
        except urllib.error.HTTPError as exc:
            dump("HTTP_CAPABILITIES", {
                "status": exc.code,
                "body": exc.read().decode("utf-8", "replace"),
            })
    finally:
        server.shutdown()
        server.server_close()




def diagnostic_inputs() -> None:
    system = build_default_system(fail_closed=True)
    inputs = (
        "promover autonomia comunitária",
        "promover consciência comunitária",
        "promover autonomia e transparência",
    )
    for index, value in enumerate(inputs, 1):
        report = system.sistema_vivo.process(
            value, cycle_id=f"selfcheck-diagnostic-{index}"
        ).loop_report
        last = report.cycles[-1] if report.cycles else {}
        dump("DIAGNOSTIC", {
            "input": value,
            "converged": report.converged,
            "rollback": report.rollback_performed,
            "phases": [s["phase"] for s in report.context_steps],
            "last_cycle_phases": list(last.get("phases", {}).keys()),
            "aborted_at": last.get("aborted_at"),
            "abort_reason": last.get("abort_reason"),
        })


def trinity_check() -> None:
    system = build_default_system(fail_closed=True)
    unified = system.components["trinity_eru"]
    assessment = unified.assess("promover autonomia com transparência")
    itr = system.components["itr_extended"]
    plan = itr.generate_strategic("preservar autonomia e validar resultado")
    result = itr.execute_composed(plan)
    dump("TRINITY", {
        "assessment": assessment,
        "semantic_guard": result.metrics.get("semantic_guard_passed"),
        "phase_results": result.phase_results,
    })


if __name__ == "__main__":
    plain_loop_check()
    full_loop_check()
    http_check()
    diagnostic_inputs()
    trinity_check()
