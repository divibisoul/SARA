"""SARA — Contrato de Ativação para módulos PENDING_INFRASTRUCTURE.
Status: IMPLEMENTED.
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ActivationRequirement:
    module: str
    required_infrastructure: str
    activation_method: str
    fallback_behavior: str
    activates_phases: tuple[str, ...] = ()
    verification_hook: str = ""


@dataclass
class ActivationPlan:
    requirements: list[ActivationRequirement] = field(default_factory=list)

    def add(self, req: ActivationRequirement) -> None:
        self.requirements.append(req)

    def pending(self) -> list[ActivationRequirement]:
        return list(self.requirements)

    def for_module(self, name: str) -> ActivationRequirement | None:
        for r in self.requirements:
            if r.module == name:
                return r
        return None


CANONICAL_ACTIVATION_PLAN = ActivationPlan()
CANONICAL_ACTIVATION_PLAN.add(ActivationRequirement(
    module="SafeSandbox",
    required_infrastructure="Backend de isolamento (Docker/Firecracker/nsjail)",
    activation_method="inject_backend",
    fallback_behavior="analyze_static() permanece funcional; execute() levanta NotImplementedError",
    activates_phases=("execution",),
    verification_hook="is_isolation_ready",
))
CANONICAL_ACTIVATION_PLAN.add(ActivationRequirement(
    module="QuantumCrawler",
    required_infrastructure="APIs de rede (GitHub/HuggingFace/arXiv) + credenciais + rate limiter",
    activation_method="inject_backends",
    fallback_behavior="scan() e list_sources() usam os backends configurados; sem rede os erros de transporte são explícitos",
    activates_phases=("governance",),
    verification_hook="is_backends_ready",
))
CANONICAL_ACTIVATION_PLAN.add(ActivationRequirement(
    module="NeuralLens",
    required_infrastructure="Token GitHub/GitLab para extract_from_repo",
    activation_method="inject_repo_client",
    fallback_behavior="extract() local permanece; extract_from_repo() levanta NotImplementedError",
    activates_phases=("governance",),
    verification_hook="is_repo_client_ready",
))
CANONICAL_ACTIVATION_PLAN.add(ActivationRequirement(
    module="QuantumScanner",
    required_infrastructure="Acesso local ao alvo + ferramenta file; objdump opcional para análise profunda",
    activation_method="local_toolchain_detection",
    fallback_behavior="Python é analisado localmente; outros arquivos usam file quando disponível",
    activates_phases=(),
    verification_hook="is_target_access_ready",
))
CANONICAL_ACTIVATION_PLAN.add(ActivationRequirement(
    module="LegalAI",
    required_infrastructure="API de patentes (USPTO/INPI/EPO) + nó Ethereum (opcional)",
    activation_method="inject_patent_oracle",
    fallback_behavior="validate_license() + verify_chain() locais permanecem; check_patent() retorna BLOQUEADO_INFRASTRUCTURE sem oracle e executa consulta HTTP quando configurado",
    activates_phases=("governance",),
    verification_hook="is_patent_oracle_ready",
))
CANONICAL_ACTIVATION_PLAN.add(ActivationRequirement(
    module="DecisionTrace",
    required_infrastructure="Nó IPFS ou gateway",
    activation_method="inject_ipfs_client",
    fallback_behavior="cadeia local permanece; publish_to_ipfs() levanta NotImplementedError",
    activates_phases=("persistence",),
    verification_hook="is_ipfs_ready",
))
CANONICAL_ACTIVATION_PLAN.add(ActivationRequirement(
    module="TransystemSARA",
    required_infrastructure="Endpoints externos explicitamente autorizados + credenciais quando exigidas",
    activation_method="inject_http_adapters",
    fallback_behavior="sistemas sem adapter retornam BLOCKED_INFRASTRUCTURE; list_sources() permanece",
    activates_phases=(),
    verification_hook="is_credentials_ready",
))
CANONICAL_ACTIVATION_PLAN.add(ActivationRequirement(
    module="GovernanceBackend",
    required_infrastructure="Framework web (React/Vue) + endpoint HTTP",
    activation_method="inject_ui_backend",
    fallback_behavior="backend local permanece; UI levanta NotImplementedError",
    activates_phases=("monitoring",),
    verification_hook="is_ui_ready",
))