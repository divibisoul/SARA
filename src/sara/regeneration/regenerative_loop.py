            else:
                reason = "ethical_filter_chain_failure"
            raise _Aborted("VALIDATION", reason)

    def _phase_persistence(self, ctx, cycle, idx, result):
        feedback_refs = ctx.external_context.get("user_feedback_refs")
        probabilistic = ctx.artifacts.get("probabilistic")
        evidence = {
            "feedback_refs": list(feedback_refs) if isinstance(feedback_refs, list) else [],
            "probabilistic": probabilistic if isinstance(probabilistic, dict) else None,
        }
        rid = self._temporal.insert({
            "cycle_id": ctx.cycle_id, "iteration": idx,
            "input": ctx.input, "state": ctx.current,
            "execution": getattr(result, "metrics", {}),
            "evidence": evidence,
        })
        self._memory.store({
            "cycle_id": ctx.cycle_id, "iteration": idx,
            "state": ctx.current, "temporal_id": rid,
            "evidence": evidence,
        }, label=f"{ctx.cycle_id}::iteration::{idx}")
        memory_persisted = self._memory.persist_if_configured()
        temporal_persisted = self._temporal.persist_if_configured()
        cycle["phases"]["persistence"] = {
            "temporal_id": rid,
            "memory_persisted": memory_persisted,
            "temporal_persisted": temporal_persisted,
        }
        self._record(ctx, CyclePhase.PERSISTENCE, "RegenerativeMemory", True,
                     temporal_id=rid,
                     memory_persisted=memory_persisted,
                     temporal_persisted=temporal_persisted)
