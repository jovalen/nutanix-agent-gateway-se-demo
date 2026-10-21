from dataclasses import dataclass
import os


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


@dataclass
class Settings:
    demo_mode: str = env("DEMO_MODE", "live")
    nai_url: str = env("NAI_UNIFIED_ENDPOINT_URL")
    nai_endpoint_name: str = env("NAI_UNIFIED_ENDPOINT_NAME")
    nai_key: str = env("NAI_API_KEY")
    mcp_url: str = env("MCP_URL", "http://mcp-mock:8001/mcp")
    mcp_key: str = env("MCP_API_KEY")
    mcp_protocol_version: str = env("MCP_PROTOCOL_VERSION", "2025-06-18")
    # Lab-only workaround for an hPOC certificate/hostname mismatch. Keep true in production.
    # TLS_VERIFY applies to both the Unified Endpoint and MCP. MCP_TLS_VERIFY remains
    # as a backwards-compatible fallback for older .env files.
    tls_verify: bool = env("TLS_VERIFY", env("MCP_TLS_VERIFY", "true")).lower() not in {"0", "false", "no", "off"}
    policy_tool: str = env("MCP_POLICY_TOOL", "get_customer_policy")
    claim_tool: str = env("MCP_CLAIM_TOOL", "get_claim_status")
    repair_tool: str = env("MCP_REPAIR_TOOL", "find_repair_shops")
    create_claim_tool: str = env("MCP_CREATE_CLAIM_TOOL", "create_claim")
    blocked_tool: str = env("MCP_BLOCKED_TOOL", "approve_claim_payout")
    mock_llm: bool = env("MOCK_LLM", "false").lower() in {"1", "true", "yes"}

    @property
    def models(self) -> dict[str, str]:
        # Kept as a compatibility shape for the existing UI. NAI chooses the
        # underlying provider(s) behind this single Unified Endpoint.
        return {"unified_endpoint": self.nai_endpoint_name or "not-configured"}

    @property
    def tools(self) -> dict[str, str]:
        return {"policy": self.policy_tool, "claim": self.claim_tool, "repair": self.repair_tool, "create_claim": self.create_claim_tool, "blocked": self.blocked_tool}


settings = Settings()
