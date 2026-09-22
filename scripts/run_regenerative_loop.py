"""SARA — Demo completa ponta a ponta. v3.1."""
from sara.bootstrap import build_default_system


def main() -> None:
    print("=" * 78)
    print("SARA v3.1 — Demo do Fluxo Completo (registry-driven)")
    print("=" * 78)

    system = build_default_system()
    reg = system.registry.snapshot()

    print(f"\n📦 Módulos registrados: {reg['count']}")
    print(f"   Por status:")
    for status, mods in reg["by_status"].items():
        print(f"     {status}: {len(mods)} — {mods}")

    print(f"\n📋 Registro:")
    print(f"   registrados: {len(system.registration_report['registered'])}")
    print(f"   pending: {len(system.registration_report['pending'])}")
    print(f"   falharam: {len(system.registration_report['failed'])}")
    for f in system.registration_report["failed"]:
        print(f"     ⚠️  {f['module']}: {f['reason']}")

    missing = system.registry.validate_dependencies()
    print(f"\n🔗 Dependências não resolvidas: {len(missing)}")
    for m in missing:
        print(f"   ⚠️  {m}")

    cases = [
        "promover autonomia e transparência comunitária",
        "modificar 🔒IDENTITY sem aprovação",
        "sistema de vigilância militar em massa",
        "burlar a ética com hack para resolver",
    ]

    for case in cases:
        print("\n" + "─" * 78)
        print(f"▶ INPUT: {case!r}")
        result = system.sistema_vivo.process(case)
        r = result.loop_report
        print(f"  Cycle ID       : {result.cycle_id}")
        print(f"  Convergido     : {r.converged}")
        print(f"  Rollback       : {r.rollback_performed}")
        print(f"  Ciclos         : {len(r.cycles)}")
        print(f"  Passos (ctx)   : {len(r.context_steps)}")
        phases = []
        for s in r.context_steps:
            if s["phase"] not in phases:
                phases.append(s["phase"])
        print(f"  Fases cobertas : {phases}")
        if r.invariants:
            ok_count = sum(1 for i in r.invariants if i["ok"])
            print(f"  Invariantes OK : {ok_count}/{len(r.invariants)}")
        if r.cycles:
            aborted = r.cycles[-1].get("abort_reason")
            if aborted:
                print(f"  Aborto em      : {r.cycles[-1].get('aborted_at')} ({aborted})")

    print("\n" + "═" * 78)
    print("Radar de Inovação + Governança")
    print("═" * 78)
    proposal = {
        "name": "AutonomiaComunitaria",
        "description": "inovação para promover autonomia e transparência comunitária",
        "license": "MIT",
        "dependencies": [],
    }
    radar = system.components["radar"]
    score = radar.score(proposal)
    print(f"\n📊 Radar score:")
    for k, v in score.as_dict().items():
        print(f"   {k:12s}: {v}")

    governed = system.components["governed"]
    decision = governed.assimilate(proposal)
    print(f"\n⚖️  Governança: accepted={decision.accepted}")
    print(f"   reasons: {decision.reasons}")

    print("\n" + "═" * 78)
    print("Estado Final do Sistema")
    print("═" * 78)
    st = system.sistema_vivo.state()
    print(f"  Ciclos executados : {st['cycles_executed']}")
    print(f"  Trace válido      : {st['trace_valid']}")
    print(f"  Registros temporais: {system.components['temporal'].count()}")
    print(f"  Versões em memória : {len(system.components['memory'].trail())}")
    print(f"  Snapshots rollback : {system.components['rollback'].snapshot_count()}")
    if st.get("provenance"):
        print(f"  Provenance         : {st['provenance']}")
    print("═" * 78)


if __name__ == "__main__":
    main()