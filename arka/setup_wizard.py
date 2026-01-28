"""
ARKA Setup Wizard
Interactive first-run setup for model provider and API key configuration.
"""

import os
from pathlib import Path
from typing import Optional, Tuple
import json

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table


console = Console()

# Supported providers
PROVIDERS = {
    "1": {
        "name": "OpenAI",
        "env_var": "OPENAI_API_KEY",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-5.2-codex", "o1", "o1-mini"],
        "default": "gpt-4o",
    },
    "2": {
        "name": "Anthropic",
        "env_var": "ANTHROPIC_API_KEY",
        "models": ["claude-sonnet-4-20250514", "claude-3-5-haiku-20241022"],
        "default": "claude-sonnet-4-20250514",
    },
    "3": {
        "name": "Google (Gemini)",
        "env_var": "GOOGLE_API_KEY",
        "models": ["gemini-2.0-flash", "gemini-2.5-pro"],
        "default": "gemini-2.0-flash",
    },
}

CONFIG_DIR = Path.home() / ".arka"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.json"


def load_credentials() -> dict:
    """Load saved credentials."""
    if CREDENTIALS_FILE.exists():
        try:
            return json.loads(CREDENTIALS_FILE.read_text())
        except Exception:
            pass
    return {}


def save_credentials(provider: str, api_key: str, model: str):
    """Save credentials securely."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    creds = load_credentials()
    creds["provider"] = provider
    creds["api_key"] = api_key
    creds["model"] = model
    
    CREDENTIALS_FILE.write_text(json.dumps(creds, indent=2))
    CREDENTIALS_FILE.chmod(0o600)  # Restrict permissions


def get_api_key_from_env(provider_info: dict) -> Optional[str]:
    """Check if API key is already in environment."""
    return os.environ.get(provider_info["env_var"])


def set_api_key_in_env(provider_info: dict, api_key: str):
    """Set API key in current environment."""
    os.environ[provider_info["env_var"]] = api_key


def is_setup_complete() -> bool:
    """Check if setup has been completed and load credentials."""
    creds = load_credentials()
    if not creds.get("provider") or not creds.get("api_key"):
        return False
    
    # Load saved key into environment
    provider = creds.get("provider")
    api_key = creds.get("api_key")
    
    for pid, pinfo in PROVIDERS.items():
        if pinfo["name"] == provider:
            # Set the API key in environment
            os.environ[pinfo["env_var"]] = api_key
            return True
    
    # Unknown provider but has key - try OpenAI as default
    os.environ["OPENAI_API_KEY"] = api_key
    return True


def run_setup_wizard() -> Tuple[str, str, str]:
    """
    Run the interactive setup wizard.
    
    Returns:
        Tuple of (provider_name, api_key, default_model)
    """
    console.clear()
    console.print()
    console.print(Panel(
        "[bold cyan]Welcome to ARKA![/bold cyan]\n\n"
        "Let's set up your AI provider. This is a one-time setup.",
        title="🚀 First Run Setup",
        border_style="cyan",
    ))
    console.print()
    
    # Step 1: Choose provider
    table = Table(title="Available Providers")
    table.add_column("#", style="bold cyan")
    table.add_column("Provider", style="bold")
    table.add_column("Models")
    
    for num, info in PROVIDERS.items():
        models_str = ", ".join(info["models"][:3])
        if len(info["models"]) > 3:
            models_str += "..."
        table.add_row(num, info["name"], models_str)
    
    console.print(table)
    console.print()
    
    choice = Prompt.ask(
        "[bold]Choose a provider[/bold]",
        choices=list(PROVIDERS.keys()),
        default="1"
    )
    
    provider_info = PROVIDERS[choice]
    provider_name = provider_info["name"]
    
    console.print(f"\n[green]✓[/green] Selected: [bold]{provider_name}[/bold]\n")
    
    # Step 2: API Key
    # First check environment
    existing_key = get_api_key_from_env(provider_info)
    if existing_key:
        masked = existing_key[:8] + "..." + existing_key[-4:]
        use_existing = Confirm.ask(
            f"Found existing API key in environment: [dim]{masked}[/dim]. Use this key?"
        )
        if use_existing:
            api_key = existing_key
        else:
            console.print("[dim]Paste your API key (it will be visible):[/dim]")
            api_key = Prompt.ask(
                f"Enter your [bold]{provider_name} API Key[/bold]"
            )
    else:
        console.print(Panel(
            f"You can get your API key from:\n"
            f"[link]https://platform.openai.com/api-keys[/link] (OpenAI)\n"
            f"[link]https://console.anthropic.com/[/link] (Anthropic)\n"
            f"[link]https://aistudio.google.com/apikey[/link] (Google)",
            title="API Key Info",
            border_style="dim",
        ))
        console.print()
        console.print("[dim]Paste your API key below:[/dim]")
        
        api_key = Prompt.ask(
            f"Enter your [bold]{provider_name} API Key[/bold]"
        )
    
    if not api_key:
        console.print("[red]API key is required![/red]")
        raise SystemExit(1)
    
    # Step 3: Choose default model
    console.print()
    console.print("[bold]Available models:[/bold]")
    for i, model in enumerate(provider_info["models"], 1):
        default_marker = " [dim](recommended)[/dim]" if model == provider_info["default"] else ""
        console.print(f"  {i}. {model}{default_marker}")
    
    console.print()
    model_choice = Prompt.ask(
        "Choose default model (number or name)",
        default=provider_info["default"]
    )
    
    # Handle numeric input
    if model_choice.isdigit():
        idx = int(model_choice) - 1
        if 0 <= idx < len(provider_info["models"]):
            model_choice = provider_info["models"][idx]
    
    # Validate model
    if model_choice not in provider_info["models"]:
        model_choice = provider_info["default"]
    
    console.print(f"\n[green]✓[/green] Using model: [bold cyan]{model_choice}[/bold cyan]\n")
    
    # Save credentials
    save_creds = Confirm.ask("Save credentials for future sessions?", default=True)
    if save_creds:
        save_credentials(provider_name, api_key, model_choice)
        console.print("[green]✓[/green] Credentials saved to ~/.arka/credentials.json")
    
    # Set in environment for current session
    set_api_key_in_env(provider_info, api_key)
    
    console.print()
    console.print(Panel(
        f"[green]✓ Setup complete![/green]\n\n"
        f"Provider: [bold]{provider_name}[/bold]\n"
        f"Model: [bold cyan]{model_choice}[/bold cyan]\n\n"
        f"Starting ARKA...",
        border_style="green",
    ))
    console.print()
    
    return provider_name, api_key, model_choice


def ensure_setup() -> Tuple[str, str]:
    """
    Ensure setup is complete, running wizard if needed.
    
    Returns:
        Tuple of (provider_name, default_model)
    """
    creds = load_credentials()
    
    # Check if we have saved credentials
    if creds.get("provider") and creds.get("api_key"):
        provider = creds["provider"]
        model = creds.get("model", "gpt-4o")
        
        # Set API key in environment
        for pid, pinfo in PROVIDERS.items():
            if pinfo["name"] == provider:
                set_api_key_in_env(pinfo, creds["api_key"])
                break
        
        return provider, model
    
    # Check environment variables
    for pid, pinfo in PROVIDERS.items():
        if get_api_key_from_env(pinfo):
            return pinfo["name"], pinfo["default"]
    
    # Run setup wizard
    provider, api_key, model = run_setup_wizard()
    return provider, model
