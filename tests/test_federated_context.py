from sara.bootstrap import build_default_system
from sara.infra.hashing import hash_json

def test_federated_context_is_consumed_and_hashed() -> None:
    system = build_default_system(fail_closed=True)
    context = {
        "session_id": "n06-session",
        "client": "n06",
        "pipeline": {"selected_chat_model": "chat-model"},
        "probabilistic": {"observed": True},
    }
    result = system.sistema_vivo.process(
        "preservar contexto e validar resultado",
        cycle_id="n06-context-cycle",
        federated_context=context,
    )
    assert result.federated_context_hash == hash_json(context)
    assert result.loop_report.cycle_id == "n06-context-cycle"
    assert result.loop_report.cycles
