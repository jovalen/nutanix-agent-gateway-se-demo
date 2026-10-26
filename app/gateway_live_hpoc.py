"""Backward-compatible import path for the former HPOC gateway helper.

The implementation now lives in ``app.gateway`` so TLS, correlation IDs and
response handling cannot drift between Live code paths.
"""
from .gateway import GatewayError, UnifiedEndpointClient, gateway_monitor_data, normalize_usage

__all__ = ["GatewayError", "UnifiedEndpointClient", "gateway_monitor_data", "normalize_usage"]
