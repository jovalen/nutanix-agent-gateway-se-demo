from typing import Any
import re


def choose_tool(message: str, *, policy_tool: str, claim_tool: str, repair_tool: str,
                create_claim_tool: str, blocked_tool: str) -> tuple[str | None, dict[str, Any]]:
    """Select only the deterministic demo operation; sensitive payout intent wins first."""
    text = message.casefold()
    payment_words = r"(?:payout|payment|compensation|indemnizaci[oó]n|pago|transfer)"
    authorization_words = r"(?:approve|authorize|authorise|execute|pay|process|release|issue|send|aprobar|autorizar|ejecutar|pagar|transferir)"
    if (
        re.search(rf"\b{authorization_words}\b(?:.{{0,120}})\b{payment_words}\b", text)
        or re.search(rf"\b{payment_words}\b(?:.{{0,120}})\b{authorization_words}\b", text)
    ):
        return blocked_tool, {"claim_id": "CLM-2026-1043", "amount": 1840}
    if any(x in text for x in ("payout", "compensation", "indemnización", "indemnizacion", "payment", "pago")):
        return claim_tool, {"claim_id": "CLM-2026-1043"}
    create_verbs = ("open", "create", "file", "start", "abrir", "crear", "declarar")
    if any(x in text for x in ("open a claim", "create a claim", "file a claim", "new claim", "abrir un parte", "crear parte", "declarar siniestro")) or (any(x in text for x in create_verbs) and any(x in text for x in ("claim", "parte", "siniestro"))):
        return create_claim_tool, {
            "customer_id": "CUST-2048",
            "description": "Minor parking collision",
            "vehicle": "Seat Leon 2023",
        }
    if any(x in text for x in ("repair shop", "garage", "body shop", "repair center", "taller", "reparación", "reparacion")):
        return repair_tool, {"postcode": "28001", "specialty": "bodywork"}
    if any(x in text for x in ("claim", "status", "siniestro", "estado", "parte")):
        return claim_tool, {"claim_id": "CLM-2026-1043"}
    if any(x in text for x in ("policy", "coverage", "deductible", "excess", "póliza", "poliza", "cobertura", "franquicia")):
        return policy_tool, {"customer_id": "CUST-2048"}
    return None, {}
