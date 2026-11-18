"""Generate a GitHub-renderable SE guide and runtime reference from source."""
from pathlib import Path
from engine import FACTS, POLICY, ROUTES
root = Path(__file__).parent
out = root / "generated"
out.mkdir(exist_ok=True)
parts = [(root / "README.md").read_text(), "## Generated runtime reference", "### Model routes"]
parts.extend("- **" + name + "**: " + " → ".join(routes) for name,routes in ROUTES.items())
parts.append("### MCP evidence catalog")
parts.extend("- `" + name + "` — " + fact for name,fact in FACTS.items())
parts.extend(["### Planner contract", POLICY])
(out / "SE-workshop.md").write_text("\n\n".join(parts) + "\n")
