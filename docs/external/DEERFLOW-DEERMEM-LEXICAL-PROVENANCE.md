# DeerMem → SARA Lexical Retrieval Provenance

**Source:** `bytedance/deer-flow`  
**Source file:** `backend/packages/harness/deerflow/agents/memory/backends/deermem/deermem/core/retrieval.py`  
**Source commit inspected:** `a619f8e0d0f01e0bdf993562e9f50624bf2df98c`  
**Source license:** MIT  
**SARA target:** `src/sara/memory/lexical_retrieval.py`

## Adapted capabilities

The SARA module preserves the following useful mechanisms found in the source:

- SQLite FTS5 lexical indexing;
- BM25 relevance scoring;
- confidence-weighted ranking;
- time-decay weighting;
- category filtering;
- user/agent scope isolation;
- atomic replacement of a fact by its stable identifier.

The implementation in SARA is an **additive adaptation**, not a replacement of `TemporalVectorDB` or `RegenerativeMemory`.

## Authority

`LexicalRetrieval` is a memory capability. It does not become a new orchestration, governance, or regeneration authority.

The existing SARA memory components remain intact:

- `TemporalVectorDB` — temporal/vector memory;
- `RegenerativeMemory` — versioned state memory;
- `WorkingMemory` — working context;
- `LexicalRetrieval` — lexical retrieval complement.

## Validation state

The capability has deterministic unit tests. Runtime-wide effectiveness is not claimed until SARA integration tests exercise it through the relevant memory workflows.
