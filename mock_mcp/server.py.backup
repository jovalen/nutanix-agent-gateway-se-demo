from fastapi import FastAPI
from datetime import datetime, timezone

app = FastAPI(title="SeguroAuto Demo MCP", version="0.2.0")
TOOLS = [
    {"name": "get_customer_policy", "description": "Consulta read-only de póliza y coberturas del cliente.", "inputSchema": {"type": "object", "properties": {"customer_id": {"type": "string"}}, "required": ["customer_id"]}},
    {"name": "get_claim_status", "description": "Consulta read-only del estado de un siniestro.", "inputSchema": {"type": "object", "properties": {"claim_id": {"type": "string"}}, "required": ["claim_id"]}},
    {"name": "find_repair_shops", "description": "Busca talleres concertados por código postal y especialidad.", "inputSchema": {"type": "object", "properties": {"postcode": {"type": "string"}, "specialty": {"type": "string"}}}},
    {"name": "create_claim", "description": "Crea un parte de siniestro iniciado por el cliente.", "inputSchema": {"type": "object", "properties": {"customer_id": {"type": "string"}, "description": {"type": "string"}, "vehicle": {"type": "string"}}}},
    {"name": "approve_claim_payout", "description": "Acción sensible: aprobar un pago; requiere revisión humana y está bloqueada en la demo.", "inputSchema": {"type": "object", "properties": {"claim_id": {"type": "string"}, "amount": {"type": "number"}}}},
]


def text(value: object) -> dict:
    return {"content": [{"type": "text", "text": str(value)}]}


@app.get("/health")
async def health():
    return {"status": "ok", "server": "seguroauto-demo-mcp", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.post("/mcp")
async def mcp_rpc(payload: dict):
    method, request_id = payload.get("method"), payload.get("id")
    if method == "initialize":
        result = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {"listChanged": False}}, "serverInfo": {"name": "seguroauto-demo-mcp", "version": "0.2.0"}}
    elif method == "notifications/initialized":
        result = {}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        params, name = payload.get("params", {}), payload.get("params", {}).get("name")
        args = params.get("arguments", {})
        if name == "get_customer_policy":
            result = text({"customer_id": args.get("customer_id", "CUST-2048"), "policy": "AUTO-ES-88421", "vehicle": "Seat Leon 2023", "status": "active", "coverage": ["daños propios", "lunas", "asistencia 24h"], "excess": 300})
        elif name == "get_claim_status":
            result = text({"claim_id": args.get("claim_id", "CLM-2026-1043"), "status": "peritación programada", "updated": "2026-10-20", "estimated_resolution": "3-5 días laborables", "next_step": "El perito contactará con el cliente"})
        elif name == "find_repair_shops":
            result = text({"postcode": args.get("postcode", "28001"), "specialty": args.get("specialty", "carrocería"), "shops": [{"name": "Taller Centro Madrid", "distance": "1.8 km", "availability": "mañana 10:30"}, {"name": "AutoCare Salamanca", "distance": "2.4 km", "availability": "jueves 09:00"}]})
        elif name == "create_claim":
            result = text({"claim_id": "CLM-2026-1051", "status": "recibido", "message": "El parte ha sido registrado. Recibirás confirmación por email."})
        elif name == "approve_claim_payout":
            return {"jsonrpc": "2.0", "id": request_id, "result": {"isError": True, **text("DENEGADO POR POLÍTICA: aprobar indemnizaciones requiere revisión humana. No se ha ejecutado ningún pago.")}}
        else:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": f"Unknown tool: {name}"}}
    else:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Unsupported method: {method}"}}
    return {"jsonrpc": "2.0", "id": request_id, "result": result}
