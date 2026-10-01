from datetime import UTC, datetime, timedelta

from sara.memory.lexical_retrieval import LexicalRetrieval


def test_lexical_retrieval_ranks_matching_facts_and_supports_scope():
    engine = LexicalRetrieval()
    engine.index_fact(
        "a",
        "alpha beta reasoning",
        confidence=0.9,
        scope_user="u1",
        scope_agent="agent-a",
    )
    engine.index_fact(
        "b",
        "alpha unrelated",
        confidence=0.1,
        scope_user="u1",
        scope_agent="agent-a",
    )
    engine.index_fact(
        "c",
        "alpha beta hidden",
        confidence=1.0,
        scope_user="u2",
        scope_agent="agent-a",
    )

    rows = engine.search("alpha beta", scope_user="u1", scope_agent="agent-a")
    assert [fact.fact_id for fact, _ in rows] == ["a", "b"]


def test_lexical_retrieval_supports_category_and_replacement():
    engine = LexicalRetrieval()
    created = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    engine.index_fact("x", "tool discovery", category="tools", created_at=created)
    engine.index_fact("x", "tool discovery updated", category="tools", created_at=created)

    rows = engine.search("updated", category="tools")
    assert [fact.fact_id for fact, _ in rows] == ["x"]


def test_lexical_retrieval_is_additive_and_describable():
    engine = LexicalRetrieval()
    engine.index_fact(
        "old",
        "historical reasoning",
        created_at=(datetime.now(UTC) - timedelta(days=30)).isoformat().replace("+00:00", "Z"),
    )
    info = engine.describe()
    assert info["name"] == "LexicalRetrieval"
    assert info["backend"] == "sqlite-fts5"
    assert info["facts"] == 1
