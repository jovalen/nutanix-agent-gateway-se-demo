from dataclasses import dataclass
import os


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


@dataclass(frozen=True)
class Settings:
    demo_mode: str = env("DEMO_MODE", "live")
    nai_url: str = env("NAI_UNIFIED_ENDPOINT_URL")
    nai_key: str = env("NAI_API_KEY")
    model_openai: str = env("NAI_MODEL_OPENAI", "openai-demo")
    model_anthropic: str = env("NAI_MODEL_ANTHROPIC", "claude-demo")
    model_private: str = env("NAI_MODEL_PRIVATE", "private-demo")
    mcp_url: str = env("MCP_URL", "http://mcp-mock:8001/mcp")
    mcp_key: str = env("MCP_API_KEY")
    policy_tool: str = env("MCP_POLICY_TOOL", "get_customer_policy")
    claim_tool: str = env("MCP_CLAIM_TOOL", "get_claim_status")
    repair_tool: str = env("MCP_REPAIR_TOOL", "find_repair_shops")
    create_claim_tool: str = env("MCP_CREATE_CLAIM_TOOL", "create_claim")
    blocked_tool: str = env("MCP_BLOCKED_TOOL", "approve_claim_payout")
    mock_llm: bool = env("MOCK_LLM", "false").lower() in {"1", "true", "yes"}

    @property
    def models(self) -> dict[str, str]:
        return {"openai": self.model_openai, "anthropic": self.model_anthropic, "private": self.model_private}

    @property
    def tools(self) -> dict[str, str]:
        return {"policy": self.policy_tool, "claim": self.claim_tool, "repair": self.repair_tool, "create_claim": self.create_claim_tool, "blocked": self.blocked_tool}


settings = Settings()
