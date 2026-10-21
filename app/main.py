from pathlib import Path
from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from .settings import settings
from .gateway import GatewayError, UnifiedEndpointClient
from .mcp import MCPClient, MCPError

app = FastAPI(title="SeguroAuto — Nutanix Agent Gateway Demo", version="0.2.0")
BASE = Path(__file__).parent
llm = UnifiedEndpointClient(settings)
mcp = MCPClient(settings)


class AssistantRequest(BaseModel):
    model_key: str = Field(default="unified_endpoint", pattern="^unified_endpoint$")
    message: str = Field(min_length=1, max_length=8000)
    view: str = Field(default="customer")


class ToolRequest(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


@app.get("/")
async def index():
    return FileResponse(BASE / "static/index.html")


@app.get("/static/{path:path}")
async def static_files(path: str):
    return FileResponse(BASE / "static" / path)


@app.get("/api/config")
async def config():
    return {"product": "SeguroAuto", "mode": settings.demo_mode, "gateway_configured": bool(settings.nai_url and settings.nai_key and settings.nai_endpoint_name), "mcp_configured": bool(settings.mcp_url), "mcp_url": settings.mcp_url, "endpoint_name": settings.nai_endpoint_name, "models": settings.models, "tools": settings.tools}


@app.get("/api/health")
async def health():
    result = {"app": "ok", "gateway": "not-configured", "mcp": "not-tested"}
    if settings.nai_url and settings.nai_key and settings.nai_endpoint_name and not settings.mock_llm:
        result["gateway"] = "configured"
    elif settings.mock_llm:
        result["gateway"] = "mock"
    try:
        await mcp.list_tools()
        result["mcp"] = "reachable"
    except MCPError as exc:
        result["mcp"] = f"error: {exc}"
    return result


@app.get("/api/tools")
async def tools():
    try:
        return {"tools": await mcp.list_tools(), "endpoint": settings.mcp_url}
    except MCPError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/mcp/call")
async def call_tool(request: ToolRequest):
    try:
        result = await mcp.call_tool(request.name, request.arguments)
        return {"tool": request.name, "result": result, "endpoint": settings.mcp_url}
    except MCPError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def choose_tool(message: str) -> tuple[str | None, dict[str, Any]]:
    text = message.lower()
    if any(word in text for word in ["indemnización", "indemnizacion", "pago", "pagar", "transferencia"]):
        return settings.blocked_tool, {"claim_id": "CLM-2026-1043", "amount": 1840}
    if any(word in text for word in ["abrir", "crear", "declarar", "siniestro nuevo"]):
        return settings.create_claim_tool, {"customer_id": "CUST-2048", "description": "Colisión leve en aparcamiento", "vehicle": "Seat Leon 2023"}
    if any(word in text for word in ["taller", "reparación", "reparacion", "perito"]):
        return settings.repair_tool, {"postcode": "28001", "specialty": "carrocería"}
    if any(word in text for word in ["estado", "siniestro", "parte", "claim"]):
        return settings.claim_tool, {"claim_id": "CLM-2026-1043"}
    if any(word in text for word in ["póliza", "poliza", "cobertura", "franquicia", "seguro"]):
        return settings.policy_tool, {"customer_id": "CUST-2048"}
    return None, {}


def tool_text(result: dict[str, Any]) -> str:
    content = result.get("content", [])
    return "\n".join(item.get("text", str(item)) for item in content) if isinstance(content, list) else str(result)


@app.post("/api/assistant")
async def assistant(request: AssistantRequest):
    model = settings.nai_endpoint_name or "rehearsal-unified-endpoint"
    selected_tool, arguments = choose_tool(request.message)
    tool_result: dict[str, Any] | None = None
    blocked = False
    try:
        available = await mcp.list_tools()
        if selected_tool:
            if selected_tool not in {tool.get("name") for tool in available}:
                raise MCPError(f"La herramienta '{selected_tool}' no está publicada por el MCP")
            tool_result = await mcp.call_tool(selected_tool, arguments)
            blocked = bool(tool_result.get("isError"))
        context = tool_text(tool_result) if tool_result else "No se ha invocado ninguna herramienta; responde con la información disponible en la conversación."
        system = ("Eres el asistente virtual de SeguroAuto. Responde en español, con tono claro y empático. "
                  "No inventes coberturas ni importes. Si una operación requiere aprobación humana, dilo claramente. "
                  f"Vista actual: {request.view}. Contexto de sistema obtenido mediante MCP:\n{context}")
        result = await llm.chat(model, [{"role": "system", "content": system}, {"role": "user", "content": request.message}])
        return {**result, "model_key": request.model_key, "endpoint_name": result.get("endpoint_name", model), "tool": selected_tool, "tool_result": tool_result, "blocked": blocked, "view": request.view, "usage": result.get("usage", {})}
    except (MCPError, GatewayError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/guided-run")
async def guided_run(request: AssistantRequest):
    model = settings.nai_endpoint_name or "rehearsal-unified-endpoint"
    steps: list[dict[str, Any]] = []
    try:
        available = await mcp.list_tools()
        names = {tool.get("name") for tool in available}
        steps.append({"step": "mcp_policy", "status": "ok", "detail": f"{len(available)} herramientas publicadas para el agente"})
        calls = [(settings.policy_tool, {"customer_id": "CUST-2048"}), (settings.claim_tool, {"claim_id": "CLM-2026-1043"}), (settings.repair_tool, {"postcode": "28001", "specialty": "carrocería"})]
        evidence = []
        for name, arguments in calls:
            if name not in names:
                raise MCPError(f"La herramienta configurada '{name}' no está publicada por el MCP")
            result = await mcp.call_tool(name, arguments)
            evidence.append(f"{name}: {tool_text(result)}")
            steps.append({"step": "mcp_tool_call", "status": "ok", "tool": name})
        prompt = ("Resume este caso de SeguroAuto para un cliente. Indica cobertura, estado del siniestro, "
                  "siguiente paso y taller recomendado. No inventes datos.\n\n" + "\n".join(evidence))
        answer = await llm.chat(model, [{"role": "system", "content": "Responde en español con bullets breves y tono empático."}, {"role": "user", "content": prompt}])
        steps.append({"step": "llm_summary", "status": "ok", "model": model, "transport": answer["transport"]})
        return {"answer": answer["content"], "model": model, "steps": steps, "usage": answer.get("usage", {}), "transport": answer.get("transport"), "usage_source": answer.get("usage_source")}
    except (MCPError, GatewayError) as exc:
        steps.append({"step": "error", "status": "error", "detail": str(exc)})
        raise HTTPException(status_code=502, detail={"message": str(exc), "steps": steps}) from exc
