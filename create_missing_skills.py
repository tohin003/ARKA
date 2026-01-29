import os
from pathlib import Path

BASE = Path("arka/skills")

SKILLS = {
    "development/changelog_generator": {
        "desc": "Generate changelogs from git history.",
        "tools": """
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
"""
    },
    "business/domain_namer": {
        "desc": "Brainstorm and check domain availability.",
        "tools": """
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
"""
    },
    "business/lead_researcher": {
        "check_deps": "googlesearch-python",
        "desc": "Research companies and leads using web search.",
        "tools": """
from arka.skills.decorators import arka_tool
from googlesearch import search
import requests

@arka_tool(
    name="find_company_info",
    description="Find info about a company.",
    parameters={
        "type": "object",
        "properties": {
            "company": {"type": "string"}
        },
        "required": ["company"]
    }
)
def find_company_info(company: str) -> str:
    try:
        results = list(search(f"{company} official site contact", num_results=3))
        return f"Found URLs: {results}"
    except Exception as e:
        return f"Error: {e}"
"""
    },
    "communication/article_extractor": {
        "desc": "Extract main content from URLs.",
        "tools": """
from arka.skills.decorators import arka_tool
import requests
from bs4 import BeautifulSoup

@arka_tool(
    name="extract_article_text",
    description="Extract main text from a web article.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string"}
        },
        "required": ["url"]
    }
)
def extract_article_text(url: str) -> str:
    try:
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.content, 'html.parser')
        # Simple extraction of p tags
        text = "\\n".join([p.text for p in soup.find_all('p')])
        return text[:5000] # Limit
    except Exception as e:
        return f"Error: {e}"
"""
    },
    "communication/brainstorming": {
        "desc": "Structured brainstorming techniques (SCAMPER, Six Hats).",
        "tools": None # Prompt only
    }
}

def create():
    for name, data in SKILLS.items():
        path = BASE / name
        path.mkdir(parents=True, exist_ok=True)
        
        # SKILL.md
        md = f"""---
name: {path.name}
description: {data['desc']}
---

# {path.name.replace('_', ' ').title()}

{data['desc']}
"""
        (path / "SKILL.md").write_text(md)
        
        # tools.py
        if data.get("tools"):
            (path / "tools.py").write_text(data["tools"])
            
        # requirements.txt
        rec = data.get("check_deps", "")
        if rec:
            (path / "requirements.txt").write_text(rec)
            
        print(f"Created {name}")

if __name__ == "__main__":
    create()
