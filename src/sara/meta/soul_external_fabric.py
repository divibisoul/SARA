from __future__ import annotations
from dataclasses import dataclass
from typing import Final

@dataclass(frozen=True)
class ExternalProvider:
    id: str
    source: str
    revision: str
    canonical_owner: str
    mesh_targets: tuple[str, ...]
    capabilities: tuple[str, ...]
    sara_functions: tuple[str, ...]
    direct_affinity: bool
    state: str

EXTERNAL_PROVIDERS: Final[tuple[ExternalProvider, ...]] = (
    ExternalProvider("superpowers","https://github.com/obra/superpowers","8ca22dba9a94f28898bbce59f2537ff4d87c747d","N07",["N07"],["agentic-skills","subagents","planning","tdd","review","debugging"],["governance.engineering","sara.audit"],True,"CATALOG_BOUND"),
    ExternalProvider("superagi","https://github.com/TransformerOptimus/SuperAGI","c3c1982e7bd6a11cfed53c5a193ea502f924b1b6","N07",["N07"],["autonomous-agents","tools","memory","multimodal","telemetry"],["sara.external.capability","sara.audit"],False,"CATALOG_BOUND"),
    ExternalProvider("langgraph","https://github.com/langchain-ai/langgraph","157a06dda988d85afeb8751ff27b35ab3f4f8bf4","N07",["N07","N01"],["stateful-agents","durable-workflows","orchestration"],["sara.external.capability","sara.audit"],False,"CATALOG_BOUND"),
    ExternalProvider("crewai","https://github.com/crewAIInc/crewAI","8078f9130c35a47be95d4a55bf1d73b3fd44fc88","N07",["N07"],["multi-agent-crews","flows","role-specialization"],["sara.external.capability","sara.audit"],False,"CATALOG_BOUND"),
    ExternalProvider("microsoft-agent-framework","https://github.com/microsoft/agent-framework","a2f4506c0ba30cea7c9bbe907fc158c0db2cc6a3","N07",["N07"],["agents","workflows","MCP","A2A"],["sara.external.capability","sara.audit"],False,"CATALOG_BOUND"),
    ExternalProvider("openhands","https://github.com/OpenHands/OpenHands","2414d6ee5e31bede2e78211f72b58e9949575a75","N06",["N06"],["software-agents","tool-use","execution"],["sara.external.capability","sara.audit"],False,"CATALOG_BOUND"),
    ExternalProvider("metagpt","https://github.com/FoundationAgents/MetaGPT","11cdf466d042aece04fc6cfd13b28e1a70341b1f","N06",["N06"],["role-based-agents","multi-agent-collaboration","software-process"],["sara.external.capability","sara.audit"],False,"CATALOG_BOUND"),
    ExternalProvider("agentscope","https://github.com/agentscope-ai/agentscope","72f3f6fa0b2fc38b8517f408ab616f0f2bd229e6","N03",["N03","N07"],["agents","teams","tools","memory","sandbox","A2A","voice"],["sara.external.capability","sara.audit"],False,"CATALOG_BOUND"),
    ExternalProvider("letta-code","https://github.com/letta-ai/letta-code","1fcc9666817ab852bc2532a3a989f712e1fd6c19","N01",["N01"],["stateful-agents","persistent-memory","identity"],["memory.external.stateful","sara.state"],True,"CATALOG_BOUND"),
    ExternalProvider("browser-use","https://github.com/browser-use/browser-use","302d8fcb245a7a63fb7531a4734c9ce3c7792779","N04",["N04"],["browser-agents","web-automation"],["sara.audit","safety.external.execution"],False,"CATALOG_BOUND"),
    ExternalProvider("smolagents","https://github.com/huggingface/smolagents","c30b115286e000e98711fae5e85993547b73d826","N06",["N06"],["code-agents","tools","MCP","multimodal"],["sara.external.capability","sara.audit"],False,"CATALOG_BOUND"),
    ExternalProvider("pydantic-ai","https://github.com/pydantic/pydantic-ai","6bc07cf18b0641ea92343d8c589cfb922108b802","N01",["N01","JEV"],["typed-agents","tools","subagents","durable-execution"],["rgo.trinity.process","validation.typed"],True,"CATALOG_BOUND"),
    ExternalProvider("llama-index","https://github.com/run-llama/llama_index","962940ddc079cc21701d28d1237c84c82a7c5164","N05",["N05"],["RAG","indexing","retrieval","agent-workflows"],["memory.external.retrieval","sara.audit"],False,"CATALOG_BOUND"),
    ExternalProvider("dspy","https://github.com/stanfordnlp/dspy","ba3f9198efe5d125c7c1a2b40b1f1e6166209bd2","N06",["N06"],["LM-programming","optimization","reasoning-pipelines"],["sara.audit","strategy.optimization"],False,"CATALOG_BOUND"),
    ExternalProvider("whisper","https://github.com/openai/whisper","86098128c0b4f24f0e2aa2994de830614b474227","N03",["N03"],["speech-to-text"],["sara.audit","multimodal.validation"],False,"CATALOG_BOUND"),
    ExternalProvider("kokoro","https://github.com/hexgrad/kokoro","dfb907a02bba8152ca444717ca5d78747ccb4bec","N03",["N03"],["text-to-speech"],["sara.audit","multimodal.validation"],False,"CATALOG_BOUND"),
    ExternalProvider("everything-claude-code","https://github.com/affaan-m/ECC","ef648e01899ba3e8dc6371642deaaf64b4477775","N07",["N07"],["skills","instincts","memory-optimization","continuous-learning","security-scanning","research-first-development"],["governance.engineering","sara.audit"],True,"CATALOG_BOUND"),
    ExternalProvider("swarmclaw","https://github.com/swarmclawai/swarmclaw","ed38ba5329c20e48c03b4a4028f4a76a1a75e2d1","N07",["N07"],["multi-agent-swarms","memory","MCP","delegation","scheduling"],["sara.external.capability","sara.audit"],False,"CATALOG_BOUND"),
    ExternalProvider("mem0","https://github.com/mem0ai/mem0","abb81c88e1f738a8117d8293530fbc31a5ef8fd9","N06",["N06","SARA"],["persistent-agent-memory","memory-management"],["mem0.status@1.0.0","mem0.add@1.0.0","mem0.search@1.0.0","mem0.list@1.0.0"],True,"ADAPTER_BOUND"),
    ExternalProvider("letta","https://github.com/letta-ai/letta","5bcdd177d70fa2b31a754cfcd801e77b2e1ab16a","N06",["N06","SARA"],["stateful-agents","advanced-memory","learning"],["memory.external.stateful","sara.state"],True,"CATALOG_BOUND"),
    ExternalProvider("langfuse","https://github.com/langfuse/langfuse","f75c661dbe8c6b85523c81486b39e8403ac2c141","N07",["N07","SARA"],["tracing","evaluation","datasets","LLM-observability"],["sara.trace","observability.evaluation"],True,"CATALOG_BOUND"),
    ExternalProvider("vllm","https://github.com/vllm-project/vllm","7dfe3338d5f15dd3ccb233326aa65fde46e427ad","N07",["N07"],["high-throughput-inference","serving"],["execution.external.compute","governance.execution"],False,"CATALOG_BOUND"),
    ExternalProvider("sglang","https://github.com/sgl-project/sglang","65f759144d192671af5301568113e38686999871","N07",["N07"],["high-performance-serving","multimodal-serving"],["execution.external.compute","governance.execution"],False,"CATALOG_BOUND"),
    ExternalProvider("ray","https://github.com/ray-project/ray","f8a314bf077c9772fee2a8a1073368ca2ef9360b","N07",["N07"],["distributed-compute","actors","parallelism","AI workloads"],["execution.external.compute","governance.execution"],False,"CATALOG_BOUND"),
    ExternalProvider("megatron-lm","https://github.com/NVIDIA/Megatron-LM","160561d12927b36b1429ac35f86793cb2ece0ec6","N07",["N07"],["large-scale-transformer-training","distributed-training"],["execution.external.compute","governance.execution"],False,"CATALOG_BOUND"),
)

_INDEX = {item.id:item for item in EXTERNAL_PROVIDERS}

def resolve_external_provider(provider_id: str) -> ExternalProvider:
    key = str(provider_id).strip().lower()
    if not key or key not in _INDEX:
        raise ValueError(f"SARA_EXTERNAL_PROVIDER_UNKNOWN:{provider_id}")
    return _INDEX[key]

def providers_for_function(function_id: str) -> tuple[ExternalProvider, ...]:
    key = str(function_id).strip()
    return tuple(item for item in EXTERNAL_PROVIDERS if key in item.sara_functions)

def fabric_manifest() -> dict:
    return {
        "component":"SARA",
        "graph":"SOUL-34-capability-fabric",
        "provider_count":len(EXTERNAL_PROVIDERS),
        "providers":[item.__dict__ for item in EXTERNAL_PROVIDERS],
        "rule":"source -> SARA governance/memory evidence or canonical owner; no second authority",
    }
