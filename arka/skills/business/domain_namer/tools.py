
from arka.skills.decorators import arka_tool
import socket

@arka_tool(
    name="check_domain_dns",
    description="Check if a domain resolves (basic availability check).",
    parameters={
        "type": "object",
        "properties": {
            "domain": {"type": "string", "description": "Domain to check"}
        },
        "required": ["domain"]
    }
)
def check_domain_dns(domain: str) -> str:
    try:
        socket.gethostbyname(domain)
        return f"TAKEN: {domain} resolves to an IP."
    except socket.gaierror:
        return f"AVAILABLE (Likely): {domain} does not resolve."
    except Exception as e:
        return f"Error: {e}"
