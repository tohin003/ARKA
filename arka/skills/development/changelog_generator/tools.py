
from arka.skills.decorators import arka_tool
import subprocess

@arka_tool(
    name="get_git_history",
    description="Get recent git commits.",
    parameters={
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Number of commits"},
            "path": {"type": "string", "description": "Repo path"}
        },
        "required": ["path"]
    }
)
def get_git_history(path: str, limit: int = 20) -> str:
    try:
        cmd = ["git", "-C", path, "log", f"-n {limit}", "--pretty=format:%h - %s (%an)"]
        res = subprocess.check_output(cmd, text=True)
        return res
    except Exception as e:
        return f"Error: {e}"
