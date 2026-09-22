            state.iteration = idx
            state.transition(CycleState.RUNNING, f"iteration_{idx}", now_iso())
            if self._working_memory is not None:
                self._working_memory.put("iteration_context", {
                    "cycle_id": cid,
                    "iteration": idx,
                    "current_state": ctx.current,
                })
            cycle = {"idx": idx, "phases": {}}
            pre_state = {"cycle": idx, "input": ctx.current, "ts": now_iso()}
            pre_hash = self._rollback.capture(f"{cid}::{idx}::pre", pre_state, scope="cycle")
            cycle["pre_hash"] = pre_hash

            # Ponte ERU: o ciclo operacional também é observado pela memória
            # histórica. A Trindade continua operando normalmente; a ERU apenas
            # congela os limites do estado para detectar drift posteriormente.
            eru_bridge = (
                self._trinity.bridge()
                if self._trinity is not None and hasattr(self._trinity, "bridge")
                else None
            )
            if eru_bridge is not None:
                eru_bridge.observe(
                    cid, f"LOOP_{idx}_INPUT",
                    {"iteration": idx, "state": ctx.current},
                )
                eru_bridge.observe_capabilities(cid, f"LOOP_{idx}_INPUT")

            try:
                if self._trinity is not None and hasattr(self._trinity, "checkpoint"):
                    checkpoint = self._trinity.checkpoint(
                        pre_state,
                        cycle_id=cid,
                        phase=f"ITERATION_{idx}_PRE",
                        name="before",
                    )
                    cycle["eru_checkpoint"] = checkpoint
                    self._record(
                        ctx,
                        CyclePhase.AUDIT,
                        "ERU_Engine",
                        bool(checkpoint.get("verified")),
                        checkpoint=checkpoint,
                    )
                    if not checkpoint.get("verified"):
                        raise _Aborted("PREFLIGHT", "eru_checkpoint_not_verified")

                self._run_phases_canonical(ctx, cycle, idx)
                if self._auditor is not None and hasattr(self._auditor, "check"):
                    audit_results = self._auditor.check(ctx, cycle)
                    cycle["cycle_audit"] = audit_results
                    audit_failures = [r for r in audit_results if not r.get("ok", False)]
                    if audit_failures:
                        raise _Aborted(
                            "VALIDATION",
                            "cycle_auditor_failure:" + ";".join(
                                r.get("name", "unknown") for r in audit_failures
                            ),
                        )
                if eru_bridge is not None:
                    eru_bridge.observe(
                        cid, f"LOOP_{idx}_FINAL",
                        {
                            "iteration": idx,
                            "state": ctx.current,
                            "phases": list(cycle.get("phases", {}).keys()),
                        },
                    )
                    eru_bridge.observe_capabilities(cid, f"LOOP_{idx}_FINAL")
                    cycle["eru_audit"] = eru_bridge.audit_cycle(cid)

                invariant_report = self._invariants.validate_cycle(ctx, cycle)
                cycle["invariants"] = invariant_report.as_dict()
                if not invariant_report.ok:
                    raise _Aborted("VALIDATION", ";".join(invariant_report.blocking_failures))

                post_etr = self._etr.validate(ctx.current, mode="default")
                post_multi = (
                    self._etr.validate_multi_framework(ctx.current)
                    if hasattr(self._etr, "validate_multi_framework")
                    else None
                )
                post_flaws = self._collect_flaws(ctx.current)
                trinity_reaudit = (
                    self._trinity.assess(ctx.current)
                    if self._trinity is not None and hasattr(self._trinity, "assess")
                    else None
                )
                cycle["post_validation"] = {
                    "approved": post_etr.approved,
                    "reason": post_etr.reason,
                    "decision_status": getattr(post_multi, "decision_status", None),
                    "evidence_sufficient": getattr(post_multi, "evidence_sufficient", None),
                    "flaws": [f.kind for f in post_flaws],
                }
                cycle["trinity_reaudit"] = trinity_reaudit

                multi_ok = (
                    post_multi is None
                    or (
                        post_multi.approved
                        and post_multi.evidence_sufficient
                    )
                )
                trinity_ok = (
                    trinity_reaudit is None
                    or (
                        not any(trinity_reaudit.get("flaws", {}).get(k, [])
                                for k in ("lexical", "semantic", "structural", "relational"))
                        and bool(trinity_reaudit.get("ethics", {}).get("approved"))
                    )
                )
                final_checkpoint = (
                    self._trinity.checkpoint(
                        {"iteration": idx, "state": ctx.current},
                        cycle_id=cid,
                        phase=f"ITERATION_{idx}_POST",
                        name="after",
                    )
                    if self._trinity is not None and hasattr(self._trinity, "checkpoint")
                    else None
                )
                cycle["eru_result_checkpoint"] = final_checkpoint
                checkpoint_ok = final_checkpoint is None or bool(final_checkpoint.get("verified"))

                converged = (
                    post_etr.approved
                    and multi_ok
                    and trinity_ok
                    and not post_flaws
                    and bool(
                        ctx.flags.get(
                            "execution_ok",
                            ctx.artifacts.get("execution_ok", False),
                        )
                    )
                    and invariant_report.ok
                    and checkpoint_ok
                )
                cycle["converged"] = converged
                if self._working_memory is not None:
                    self._working_memory.put("last_cycle_result", {
                        "cycle_id": cid,
                        "iteration": idx,
                        "converged": converged,
                        "state": ctx.current,
                    })
                report.cycles.append(cycle)

                if converged:
                    state.transition(CycleState.CONVERGED, "all_criteria_satisfied", now_iso())
                    report.converged = True
                    report.final_state = ctx.current
                    break

                state.transition(CycleState.REGENERATING, "residual_flaws", now_iso())
                if idx == self._max_cycles:
                    restored = self._rollback.restore(pre_hash)
                    report.rollback_performed = restored.restored
                    if restored.restored:
                        ctx.current = restored.state.get("input", ctx.input)
                        state.transition(CycleState.ROLLED_BACK, "max_iterations_without_convergence", now_iso())
            except _Aborted as exc: