    def _phase_monitoring(self, ctx, cycle):
        # Registra a fase canônica antes das integrações auxiliares.
        cycle["phases"]["monitoring"] = {
            "trace_valid": self._trace.verify() if self._trace is not None else False,
        }
        probabilistic = ctx.artifacts.get("probabilistic")
        if isinstance(probabilistic, dict):
            nodes = list(probabilistic.get("nodes", []))
            cycle["phases"]["monitoring"]["probabilistic"] = {
                "node_count": len(nodes),
                "mean_confidence": (
                    sum(float(node.get("confidence", 0.0)) for node in nodes) / len(nodes)
                    if nodes else None
                ),
                "mean_entropy": (
                    sum(float(node.get("entropy", 0.0)) for node in nodes) / len(nodes)
                    if nodes else None
                ),
            }
            ctx.emit_decision({
                "event": "probabilistic_monitoring",
                "cycle_id": ctx.cycle_id,
                "nodes": nodes,
            })
        if self._gov_backend is not None and hasattr(self._gov_backend, "register_decision"):
            self._gov_backend.register_decision({