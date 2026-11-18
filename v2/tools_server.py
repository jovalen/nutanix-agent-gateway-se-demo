"""Deploy behind an NAI MCP connector for live workshops. Synthetic incident records."""
from mcp.server.fastmcp import FastMCP
from engine import FACTS
server = FastMCP("checkout-evidence", host="0.0.0.0", stateless_http=True)
for name, fact in FACTS.items():
    def make_tool(value):
        def read() -> str:
            return value
        return read
    server.add_tool(make_tool(fact), name=name, description=name.replace("_", " "))
if __name__ == "__main__":
    server.run(transport="streamable-http")
