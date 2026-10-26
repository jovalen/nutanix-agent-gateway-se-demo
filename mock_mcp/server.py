from __future__ import annotations

import asyncio

"""SeguroAuto MCP server using Streamable HTTP sessions.

This deliberately keeps the business data in-memory, but implements the
session handshake expected by an MCP Connector:
initialize -> Mcp-Session-Id -> notifications/initialized -> tools/list/tools/call
"""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

app = FastAPI(title="SeguroAuto Demo MCP", version="0.3.0")

PROTOCOL_VERSION = "2025-06-18"
SESSIONS: set[str] = set()

TOOLS = [
    {
        "name": "get_customer_policy",
        "description": "Consulta read-only de póliza y coberturas del cliente.",
        "inputSchema": {
            "type": "object",
            "properties": {"customer_id": {"type": "string"}},
            "required": ["customer_id"],
        },
    },
    {
        "name": "get_claim_status",
        "description": "Consulta read-only del estado de un siniestro.",
        "inputSchema": {
            "type": "object",
            "properties": {"claim_id": {"type": "string"}},
            "required": ["claim_id"],
        },
    },
    {
        "name": "find_repair_shops",
        "description": "Busca talleres concertados por código postal y especialidad.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "postcode": {"type": "string"},
                "specialty": {"type": "string"},
            },
        },
    },
    {
        "name": "create_claim",
        "description": "Crea un parte de siniestro iniciado por el cliente.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string"},
                "description": {"type": "string"},
                "vehicle": {"type": "string"},
            },
        },
    },
]


def text(value: object) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": str(value)}]}


def rpc_result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def rpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": code, "message": message},
    }


def session_headers(session_id: str | None = None) -> dict[str, str]:
    headers = {"MCP-Protocol-Version": PROTOCOL_VERSION}
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    return headers


def require_session(session_id: str | None) -> str | None:
    if not session_id or session_id not in SESSIONS:
        return None
    return session_id


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "server": "seguroauto-demo-mcp",
        "protocol": PROTOCOL_VERSION,
        "sessions": len(SESSIONS),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/mcp")
async def mcp_rpc(
    request: Request,
    mcp_session_id: str | None = Header(default=None, alias="Mcp-Session-Id"),
):
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(
            rpc_error(None, -32700, "Invalid JSON"),
            status_code=400,
            headers=session_headers(mcp_session_id),
        )

    method = payload.get("method")
    request_id = payload.get("id")
    params = payload.get("params") or {}

    # Streamable HTTP MCP handshake. The server creates the session and returns
    # its identifier in the response header; the Connector then reuses it.
    if method == "initialize":
        requested = params.get("protocolVersion", PROTOCOL_VERSION)
        negotiated = requested if requested == PROTOCOL_VERSION else PROTOCOL_VERSION
        session_id = str(uuid4())
        SESSIONS.add(session_id)
        result = {
            "protocolVersion": negotiated,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {
                "name": "seguroauto-demo-mcp",
                "version": "0.3.0",
            },
        }
        return JSONResponse(
            rpc_result(request_id, result),
            headers=session_headers(session_id),
        )

    # Notifications have no JSON-RPC id and should be acknowledged without a
    # JSON body. NAI accepts either 202 or 204 for this notification.
    session_id = require_session(mcp_session_id)
    if method == "notifications/initialized":
        if session_id is None:
            return JSONResponse(
                rpc_error(request_id, -32000, "MCP session is required"),
                status_code=400,
                headers=session_headers(mcp_session_id),
            )
        return Response(status_code=202, headers=session_headers(session_id))

    if session_id is None:
        return JSONResponse(
            rpc_error(request_id, -32000, "Invalid or missing Mcp-Session-Id"),
            status_code=400,
            headers=session_headers(mcp_session_id),
        )

    if method == "ping":
        return JSONResponse(rpc_result(request_id, {}), headers=session_headers(session_id))

    if method == "tools/list":
        return JSONResponse(
            rpc_result(request_id, {"tools": TOOLS}),
            headers=session_headers(session_id),
        )

    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        if name == "get_customer_policy":
            result = text(
                {
                    "customer_id": args.get("customer_id", "CUST-2048"),
                    "policy": "AUTO-ES-88421",
                    "vehicle": "Seat Leon 2023",
                    "status": "active",
                    "coverage": ["daños propios", "lunas", "asistencia 24h"],
                    "excess": 300,
                }
            )
        elif name == "get_claim_status":
            result = text(
                {
                    "claim_id": args.get("claim_id", "CLM-2026-1043"),
                    "status": "peritación programada",
                    "updated": "2026-10-20",
                    "estimated_resolution": "3-5 días laborables",
                    "next_step": "El perito contactará con el cliente",
                }
            )
        elif name == "find_repair_shops":
            result = text(
                {
                    "postcode": args.get("postcode", "28001"),
                    "specialty": args.get("specialty", "carrocería"),
                    "shops": [
                        {"name": "Taller Centro Madrid", "distance": "1.8 km", "availability": "mañana 10:30"},
                        {"name": "AutoCare Salamanca", "distance": "2.4 km", "availability": "jueves 09:00"},
                    ],
                }
            )
        elif name == "create_claim":
            result = text(
                {
                    "claim_id": "CLM-2026-1051",
                    "status": "recibido",
                    "message": "El parte ha sido registrado. Recibirás confirmación por email.",
                }
            )
        elif name == "approve_claim_payout":
            # Defensive response for direct calls; the tool is intentionally not
            # published in tools/list and the application guard runs earlier.
            result = {
                "isError": True,
                **text("DENEGADO POR POLÍTICA: aprobar indemnizaciones requiere revisión humana. No se ha ejecutado ningún pago."),
            }
        else:
            return JSONResponse(
                rpc_error(request_id, -32602, f"Unknown tool: {name}"),
                status_code=200,
                headers=session_headers(session_id),
            )
        return JSONResponse(
            rpc_result(request_id, result),
            headers=session_headers(session_id),
        )

    if method == "notifications/cancelled":
        return Response(status_code=202, headers=session_headers(session_id))

    return JSONResponse(
        rpc_error(request_id, -32601, f"Unsupported method: {method}"),
        status_code=200,
        headers=session_headers(session_id),
    )


@app.get("/mcp")
async def mcp_stream(
    mcp_session_id: str | None = Header(default=None, alias="Mcp-Session-Id"),
):
    """Open the Streamable HTTP SSE channel for an existing MCP session.

    NAI's MCP Connector may open this channel after initialize and close it
    during session cleanup. The demo has no server-initiated notifications, so
    it sends a valid SSE comment plus periodic keepalives.
    """
    session_id = require_session(mcp_session_id)
    if session_id is None:
        return JSONResponse(
            rpc_error(None, -32000, "Invalid or missing Mcp-Session-Id"),
            status_code=400,
            headers=session_headers(mcp_session_id),
        )

    async def events():
        yield ": connected\n\n"
        while session_id in SESSIONS:
            await asyncio.sleep(15)
            yield ": keepalive\n\n"

    headers = session_headers(session_id)
    headers.update({"Cache-Control": "no-cache", "Connection": "keep-alive"})
    return StreamingResponse(events(), media_type="text/event-stream", headers=headers)


@app.delete("/mcp")
async def close_session(
    mcp_session_id: str | None = Header(default=None, alias="Mcp-Session-Id"),
):
    if mcp_session_id:
        SESSIONS.discard(mcp_session_id)
    return Response(status_code=204)
