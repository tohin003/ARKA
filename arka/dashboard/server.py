"""
ARKA Dashboard Server
FastAPI-based monitoring and management dashboard.
"""

import os
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional, TYPE_CHECKING
import time

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from arka import __version__
from arka.config import get_config
from arka.core.orchestrator import Orchestrator
from arka.core.token_tracker import TokenTracker
from arka.core.resource_monitor import get_resource_monitor
from arka.core.budget_manager import get_budget_manager
from arka.memory import get_memory
from arka.skills import get_skill_forge
from arka.tools import get_tool_registry

# Global instances
orchestrator = Orchestrator()  # Should share state with main process ideally
# Note: In a real app, we'd need a way to share state between CLI and Server
# For now, we'll instantiate new ones which share DB/Config state

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    get_resource_monitor().start()
    yield
    # Shutdown
    get_resource_monitor().stop()

app = FastAPI(title="ARKA Dashboard", version=__version__, lifespan=lifespan)

# Templates
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
if not os.path.exists(templates_dir):
    os.makedirs(templates_dir)
templates = Jinja2Templates(directory=templates_dir)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # Fetch initial stats for server-side rendering
    monitor = get_resource_monitor()
    snapshot = monitor.get_snapshot()
    budget = get_budget_manager().get_status()
    
    stats = {
        "resources": {
            "cpu": snapshot.cpu_percent,
            "ram": snapshot.ram_percent,
            "status": snapshot.status.value,
        },
        "budget": {
            "daily_spent": budget.daily_spent,
            "daily_limit": budget.daily_limit,
        }
    }
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "version": __version__,
        "config": get_config(),
        "stats": stats,
    })

@app.get("/api/status")
async def get_status():
    """Get overall system status."""
    monitor = get_resource_monitor()
    snapshot = monitor.get_snapshot()
    budget = get_budget_manager().get_status()
    
    return {
        "resources": {
            "cpu": snapshot.cpu_percent,
            "ram": snapshot.ram_percent,
            "status": snapshot.status.value,
            "summary": snapshot.summary,
        },
        "budget": {
            "daily_spent": budget.daily_spent,
            "daily_limit": budget.daily_limit,
            "session_spent": budget.session_spent,
            "session_limit": budget.session_limit,
            "is_warning": budget.is_warning,
            "is_exceeded": budget.is_exceeded,
        },
        "orchestrator": orchestrator.get_status(),
    }

@app.get("/api/memory/search")
async def search_memory(q: str):
    """Search memory."""
    client = get_memory()
    return client.search(q)

@app.get("/api/skills")
async def list_skills():
    """List available skills."""
    forge = get_skill_forge()
    return [s.to_dict() for s in forge.list_skills()]

@app.get("/api/tools")
async def list_tools():
    """List registered tools."""
    registry = get_tool_registry()
    from arka.tools import register_default_tools
    if not registry.list_tools():
        register_default_tools()
        
    return registry.get_schemas()

def run_server(host: str = "0.0.0.0", port: int = 8080):
    """Run the dashboard server."""
    uvicorn.run(app, host=host, port=port)
