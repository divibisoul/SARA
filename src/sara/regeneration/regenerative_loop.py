            if not self._prov.verify_integrity():
                raise _Aborted("PREFLIGHT", "provenance_integrity_failed")

    def run(
        self,
        input_text: str,
        cycle_id: str | None = None,
        context_data: dict[str, Any] | None = None,
    ) -> LoopReport:
        cid = cycle_id or f"cycle-{now_iso()}"
        sink = TraceSink(self._trace, self._temporal, self._prov)
        ctx = CycleContext(cid, str(input_text), str(input_text), sink)
        if context_data:
            ctx.external_context = dict(context_data)
            probabilistic = context_data.get("probabilistic")
            if isinstance(probabilistic, dict):
                ctx.register_artifact("probabilistic", probabilistic)
                ctx.emit_decision({
                    "event": "probabilistic_context_attached",
                    "cycle_id": cid,
                    "nodes": [
                        {
                            "name": node.get("name"),
                            "source": node.get("source"),
                            "confidence": node.get("confidence"),
                            "entropy": node.get("entropy"),
                            "provenance": node.get("provenance"),
                        }
                        for node in probabilistic.get("nodes", [])
                    ],
                })
            feedback_refs = context_data.get("user_feedback_refs")
            if isinstance(feedback_refs, list):
                refs = [str(ref) for ref in feedback_refs if str(ref).strip()]
                if refs:
                    ctx.register_artifact("feedback_evidence_refs", refs)
        if self._working_memory is not None:
            self._working_memory.put("cycle_context", {
                "cycle_id": cid,
                "input": str(input_text),
                "stage": "preflight",
            })
        self._preflight(ctx)

        report = LoopReport(
            cycle_id=cid, input=str(input_text)[:200], cycles=[],
            final_state=str(input_text), rollback_performed=False, converged=False,
        )
        report.filter_classification = [r.__dict__ for r in self._filters.classify(ctx.current)]

        state = RegenerativeState(cid)
        state.transition(CycleState.PREFLIGHT, "invariants_ok", now_iso())

        for idx in range(1, self._max_cycles + 1):
            state.iteration = idx
            state.transition(CycleState.RUNNING, f"iteration_{idx}", now_iso())
            if self._working_memory is not None:
                self._working_memory.put("iteration_context", {
                    "cycle_id": cid,
                    "iteration": idx,
                    "current_state": ctx.current,