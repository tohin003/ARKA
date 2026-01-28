"""
ARKA CLI Main Entry Point
Full system access with orchestrator, memory, and resource monitoring.
"""

import sys
import os
import argparse
import json
from pathlib import Path
from typing import Optional

# Load .env file for API keys (before any other imports that need them)
try:
    from dotenv import load_dotenv
    load_dotenv()  # Loads from .env in project root
except ImportError:
    pass  # dotenv not installed, rely on environment variables

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text
from rich.layout import Layout
from rich.table import Table

from arka import __version__
from arka.config import get_config, reload_config
from arka.core.model_router import ModelRouter
from arka.core.token_tracker import TokenTracker
from arka.core.resource_monitor import ResourceMonitor
from arka.core.budget_manager import BudgetManager
from arka.core.orchestrator import Orchestrator
from arka.memory.memory_client import MemoryClient
from arka.setup_wizard import ensure_setup, is_setup_complete
from arka.tools.tool_executor import get_tool_executor, TOOL_DEFINITIONS


# Lazy import to avoid breaking CLI if deps missing
def get_dashboard_runner():
    from arka.dashboard import run_server
    return run_server


console = Console()


class ArkaCLI:
    """
    ARKA Command Line Interface.
    Full system access with orchestrator, memory, and resource monitoring.
    """
    
    def __init__(self, model: Optional[str] = None):
        self.config = get_config()
        self.router = ModelRouter(self.config)
        self.tracker = TokenTracker(self.config)
        self.tool_executor = get_tool_executor()
        
        # Initialize integrations
        self.memory = MemoryClient()
        self.resource_monitor = ResourceMonitor()
        self.budget_manager = BudgetManager(daily_limit=self.config.budget.daily_limit)
        self.orchestrator = Orchestrator(
            router=self.router, 
            tracker=self.tracker, 
            config=self.config,
            tool_executor=self.tool_executor
        )
        
        self.messages = []  # Conversation history
        self.session_id = f"session_{int(__import__('time').time())}"
        
        # Load persona
        persona = self.memory.get_persona()
        persona_context = f"\n\n## User Persona:\n{persona}" if persona else ""
        
        # Comprehensive system prompt with all tools
        self.system_prompt = f"""You are ARKA, an Autonomous Resource & Knowledge Agent with FULL SYSTEM ACCESS on macOS.{persona_context}

## Available Tools:
### App Control
- open_application: Open any app (Safari, Chrome, Comet, Finder, VS Code, Spotify, etc.)
- quit_application: Close an app
- bring_app_to_front: Focus an app
- get_running_apps: List running apps

### Browser
- open_url: Open URL in any browser
- search_google: Google search
- search_youtube: YouTube search
- new_browser_tab: Open new tab

### Files
- open_folder: Open folder in Finder
- read_file: Read file contents
- write_file: Write to file
- list_directory: List folder contents

### System
- run_shell: Execute shell command
- run_in_terminal: Run command in Terminal (visible)
- type_text: Type at cursor
- press_key: Press keyboard key
- get_clipboard / set_clipboard: Clipboard operations

### Apps
- play_music: Apple Music / Spotify
- create_note: Apple Notes
- create_reminder: Apple Reminders

ALWAYS use tools when the user asks to interact with the system. Be proactive and helpful."""
        
        # Try to initialize OpenAI client
        self.router.reinitialize_client()
        
        # Start resource monitoring
        self.resource_monitor.start()
        
        # Override model if specified
        if model:
            self.router.switch_model(model)
            self.tracker.set_current_model(model)
        
        self.running = True
        
        # Load recent memory context
        self._load_memory_context()
    
    def _load_memory_context(self):
        """Load recent context from memory."""
        try:
            recent = self.memory.search("recent conversation", limit=3)
            if recent:
                context = "\n".join([r.get("content", "") for r in recent])
                if context.strip():
                    self.messages.append({
                        "role": "system",
                        "content": f"Recent context from memory:\n{context[:500]}"
                    })
        except Exception:
            pass  # Memory might not be initialized
    
    def _save_to_memory(self, user_msg: str, assistant_msg: str):
        """Save conversation to long-term memory."""
        try:
            self.memory.store(
                content=f"User: {user_msg}\nARKA: {assistant_msg}",
                metadata={"session": self.session_id, "type": "conversation"}
            )
        except Exception:
            pass
    
    def render_header(self) -> Panel:
        """Render the status bar header."""
        status = self.tracker.get_status_display()
        return Panel(
            f"[bold cyan]ARKA[/bold cyan] v{__version__} | {status}",
            style="dim",
            height=3,
        )
    
    def render_welcome(self):
        """Display welcome message."""
        # Check resource status
        res = self.resource_monitor.get_snapshot()
        resource_info = f"CPU: {res.cpu_percent:.0f}% | RAM: {res.ram_percent:.0f}%"
        
        console.print()
        console.print(Panel(
            f"[bold cyan]ARKA[/bold cyan] - Autonomous Resource & Knowledge Agent\n"
            f"[dim]{resource_info}[/dim]\n\n"
            "Type your request or use slash commands:\n"
            "  [dim]/model <name>[/dim]  - Switch model\n"
            "  [dim]/status[/dim]        - Show detailed stats\n"
            "  [dim]/budget[/dim]        - Show budget info\n"
            "  [dim]/memory[/dim]        - Search memory\n"
            "  [dim]/hotkey[/dim]        - Setup global hotkey\n"
            "  [dim]/help[/dim]          - Show all commands\n"
            "  [dim]/quit[/dim]          - Exit ARKA",
            title=f"v{__version__}",
            border_style="cyan",
        ))
        console.print()
    
    def handle_slash_command(self, command: str) -> bool:
        """
        Handle slash commands.
        Returns True if command was handled.
        """
        parts = command[1:].split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if cmd in ("quit", "exit", "q"):
            self.running = False
            console.print("[dim]Goodbye![/dim]")
            return True
        
        elif cmd == "model":
            if args:
                try:
                    self.router.switch_model(args)
                    self.tracker.set_current_model(args)
                    console.print(f"[green]✓[/green] Switched to model: [cyan]{args}[/cyan]")
                except ValueError as e:
                    console.print(f"[red]✗[/red] {e}")
            else:
                models = self.router.list_models()
                table = Table(title="Available Models")
                table.add_column("Model", style="cyan")
                table.add_column("Current", style="green")
                
                for model in models:
                    current = "◉" if model == self.router.current_model else ""
                    table.add_row(model, current)
                
                console.print(table)
            return True
        
        elif cmd == "status":
            stats = self.tracker.get_detailed_stats()
            
            table = Table(title="Session Statistics")
            table.add_column("Metric", style="cyan")
            table.add_column("Value")
            
            table.add_row("Current Model", stats["current_model"])
            table.add_row("Total Tokens", f"{stats['session']['total_tokens']:,}")
            table.add_row("Input Tokens", f"{stats['session']['input_tokens']:,}")
            table.add_row("Output Tokens", f"{stats['session']['output_tokens']:,}")
            table.add_row("Session Cost", f"${stats['session']['cost']:.4f}")
            table.add_row("Requests", str(stats['session']['request_count']))
            
            # Add resource info
            res = self.resource_monitor.get_snapshot()
            table.add_row("CPU Usage", f"{res.cpu_percent:.1f}%")
            table.add_row("RAM Usage", f"{res.ram_percent:.1f}%")
            
            console.print(table)
            return True
        
        elif cmd == "budget":
            stats = self.tracker.get_detailed_stats()
            budget_check = self.tracker.check_budget()
            
            color = "green" if budget_check["daily_ok"] else "red"
            if budget_check["warning"]:
                color = "yellow"
            
            console.print(Panel(
                f"Daily Limit: ${stats['daily']['budget_limit']:.2f}\n"
                f"Spent Today: ${stats['daily']['cost']:.2f}\n"
                f"Remaining: [{color}]${stats['daily']['remaining']:.2f}[/{color}]",
                title="Budget Status",
                border_style=color,
            ))
            return True
        
        elif cmd == "memory":
            if args:
                results = self.memory.search(args, limit=5)
                if results:
                    console.print(f"[cyan]Found {len(results)} memories:[/cyan]")
                    for i, r in enumerate(results, 1):
                        console.print(f"  {i}. {r.get('content', '')[:100]}...")
                else:
                    console.print("[dim]No memories found.[/dim]")
            else:
                console.print("[dim]Usage: /memory <search query>[/dim]")
            return True
        
        elif cmd == "hotkey":
            console.print("[cyan]Setting up global hotkey (Cmd+B)...[/cyan]")
            try:
                from arka.hotkey_service import install_launch_agent
                install_launch_agent()
                console.print("[green]✓ Hotkey installed! Restart to activate.[/green]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
                console.print("[dim]Install pynput: pip install pynput[/dim]")
            return True
        
        elif cmd == "resources":
            res = self.resource_monitor.get_snapshot()
            cpu_color = "green" if res.cpu_percent < 70 else ("yellow" if res.cpu_percent < 90 else "red")
            ram_color = "green" if res.ram_percent < 75 else ("yellow" if res.ram_percent < 90 else "red")
            
            console.print(Panel(
                f"[{cpu_color}]CPU: {res.cpu_percent:.1f}%[/{cpu_color}]\n"
                f"[{ram_color}]RAM: {res.ram_percent:.1f}%[/{ram_color}]\n"
                f"Disk: {res.disk_percent:.1f}%",
                title="System Resources",
                border_style="blue",
            ))
            return True

        elif cmd == "learn":
            if not args:
                console.print("[dim]Usage: /learn <task_name>[/dim]")
                return True
            
            console.print(f"[cyan]Starting visual learning for '{args}'...[/cyan]")
            try:
                from arka.vision.visual_learner import get_visual_learner
                learner = get_visual_learner()
                msg = learner.start_learning(args)
                console.print(f"[green]{msg}[/green]")
                console.print("[bold]Perform the task now. Capture runs every 2s.[/bold]")
            except Exception as e:
                console.print(f"[red]Error starting learner: {e}[/red]")
            return True

        elif cmd in ("finish_learning", "done"):
            console.print("[cyan]Analyzing visual demonstration...[/cyan]")
            try:
                from arka.vision.visual_learner import get_visual_learner
                learner = get_visual_learner()
                result = learner.stop_and_process(user_description=args)
                
                if result.get("success"):
                    console.print(Panel(
                        f"{result['message']}\n\nSteps:\n" + "\n".join(f"  {i+1}. {s}" for i, s in enumerate(result.get('steps', [])[:5])),
                        title="✓ Skill Learned",
                        border_style="green"
                    ))
                    console.print("[dim]Use /feedback <skill_name> <yes/no> to improve learning.[/dim]")
                else:
                    console.print(Panel(result.get('message', 'Unknown error'), title="Learning Failed", border_style="red"))
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
            return True
        
        elif cmd == "feedback":
            # /feedback skill_name yes/no [notes]
            parts = args.split(maxsplit=2)
            if len(parts) < 2:
                console.print("[dim]Usage: /feedback <skill_name> <yes/no> [notes][/dim]")
                return True
            
            skill_name = parts[0]
            success = parts[1].lower() in ("yes", "y", "true", "1", "good")
            notes = parts[2] if len(parts) > 2 else ""
            
            try:
                from arka.vision.visual_learner import get_visual_learner
                learner = get_visual_learner()
                msg = learner.provide_feedback(skill_name, success, notes)
                console.print(f"[green]{msg}[/green]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
            return True
        
        elif cmd == "help":
            console.print(Panel(
                "[bold]Slash Commands[/bold]\n\n"
                "/model [name]   - Switch model or list available\n"
                "/status         - Show session statistics\n"
                "/budget         - Show budget information\n"
                "/memory <query> - Search conversation memory\n"
                "/resources      - Show CPU/RAM usage\n"
                "/hotkey         - Setup global Cmd+B hotkey\n"
                "/learn <task>   - Start visual learning session\n"
                "/finish_learning- Stop learning and create skill\n"
                "/clear          - Clear screen\n"
                "/quit           - Exit ARKA",
                title="Help",
                border_style="blue",
            ))
            return True
        
        elif cmd == "clear":
            console.clear()
            return True
            
        elif cmd in ("good", "like", "upvote"):
            from arka.training.rl_trainer import get_trainer
            trainer = get_trainer()
            trainer.update_last_interaction("good", 0.5)
            console.print("[green]Thanks for the feedback! I've reinforced that behavior.[/green]")
            return True
            
        elif cmd in ("bad", "dislike", "downvote"):
            from arka.training.rl_trainer import get_trainer
            trainer = get_trainer()
            trainer.update_last_interaction("bad", -0.5)
            console.print("[red]Sorry about that. I've noted to avoid that in the future.[/red]")
            return True
        
        else:
            console.print(f"[yellow]Unknown command: /{cmd}[/yellow]")
            return True
        
        return False
    
    def process_message(self, message: str):
        """Process a user message and get AI response via Orchestrator (Swarm)."""
        # Check system resources (Active Monitoring)
        if not self.resource_monitor.should_proceed():
            res = self.resource_monitor.get_snapshot()
            console.print(f"[yellow]⚠ System load high ({res.summary}). Queuing task...[/yellow]")
            
            # Wait for resources to free up
            if self.resource_monitor.wait_for_resources(timeout=30):
                console.print("[green]✓ Resources recovered. Resuming execution.[/green]")
            else:
                console.print("[red]⚠ Resource wait timed out. Proceeding with caution...[/red]")

        # Check budget before proceeding
        budget = self.tracker.check_budget()
        if budget["exceeded"]:
            console.print("[red]⚠ Budget exceeded! Use /budget to check limits.[/red]")
            return
        
        # Start processing
        model = self.router.current_model
        
        # Show thinking indicator
        with console.status(f"[bold cyan]⚡ [{model}] Orchestrating Agents...[/bold cyan]"):
            try:
                # Delegate to Orchestrator (handles Swarm, Tools, Memory)
                response = self.orchestrator.chat(message)
                
                console.print()
                console.print(Panel(
                    response,
                    title=f"[{model}]",
                    border_style="green",
                ))
                
                # Note: Orchestrator handles its own usage tracking now
                
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
    
    def run(self):
        """Main CLI loop."""
        self.render_welcome()
        
        while self.running:
            try:
                # Show status in prompt
                status = self.tracker.get_status_display()
                console.print(f"[dim]{status}[/dim]")
                
                # Get user input
                user_input = Prompt.ask("[bold cyan]>[/bold cyan]")
                
                if not user_input.strip():
                    continue
                
                # Handle slash commands
                if user_input.startswith("/"):
                    self.handle_slash_command(user_input)
                else:
                    self.process_message(user_input)
                    
            except KeyboardInterrupt:
                console.print("\n[dim]Goodbye![/dim]")
                break
            except EOFError:
                break
        
        console.print("[dim]Session ended.[/dim]")


def main():
    """CLI entry point."""
    # Allow both - and / as prefix characters for arguments
    parser = argparse.ArgumentParser(
        description="ARKA - Autonomous Resource & Knowledge Agent",
        prefix_chars='-/'
    )
    parser.add_argument(
        "--model", "/model", "-m",
        help="Specify initial model (e.g., gpt-4o, gpt-5.2-codex)",
    )
    parser.add_argument(
        "--config", "/config", "-c",
        help="Path to config file",
    )
    parser.add_argument(
        "--dashboard", "/dashboard", "-d",
        action="store_true",
        help="Run the dashboard server",
    )
    parser.add_argument(
        "--setup", "/setup",
        action="store_true",
        help="Re-run setup wizard",
    )
    parser.add_argument(
        "--version", "/version", "-v",
        action="store_true",
        help="Show version and exit",
    )
    parser.add_argument(
        "/hotkey",
        action="store_true",
        dest="hotkey_mode",
        help="Start in global hotkey mode"
    )
    
    args = parser.parse_args()
    
    if args.version:
        console.print(f"ARKA v{__version__}")
        sys.exit(0)
        
    if args.setup:
        from arka.setup_wizard import run_setup
        run_setup()
        return

    # Initialize config (assuming get_config and reload_config are available)
    # The original code had reload_config(args.config) later, this is a slight reordering
    # to fit the provided snippet's implied flow.
    # If get_config is not defined, this will cause an error.
    # For now, I'll keep the original reload_config logic.
    
    if args.hotkey_mode:
        from arka.hotkey_service import HotkeyService
        print("Starting ARKA Hotkey Service...")
        # Run blocking so the script doesn't exit
        service = HotkeyService()
        service.run_blocking()
        return

    # Check for legacy positional args if argparse didn't catch /hotkey
    if len(sys.argv) > 1 and sys.argv[1] == "/hotkey":
        from arka.hotkey_service import HotkeyService
        print("Starting ARKA Hotkey Service...")
        service = HotkeyService()
        service.run_blocking()
        return
        
    if args.dashboard:
        console.print("[bold green]Starting ARKA Dashboard on http://localhost:8080[/bold green]")
        run_server = get_dashboard_runner()
        run_server(port=8080)
        sys.exit(0)
    
    if args.config:
        reload_config(args.config)
        
    # Interactive check for existing credentials (user request)
    # Only verify if we have a key and we're in standard interactive mode
    current_key = os.environ.get("OPENAI_API_KEY")
    is_interactive_mode = not (args.hotkey_mode or args.dashboard or args.version or args.model or args.setup)
    
    if current_key and is_interactive_mode:
        # Mask key for display
        masked = current_key[:8] + "..." + current_key[-4:] if len(current_key) > 12 else "***"
        
        console.print()
        console.print(Panel(
            f"[bold]Saved OpenAI API Key found:[/bold] [dim]{masked}[/dim]",
            title="🔐 Credentials",
            border_style="cyan"
        ))
        
        if not Confirm.ask("Use these credentials?", default=True):
            # User wants to change credentials
            console.print("[dim]Enter new API key:[/dim]")
            new_key = Prompt.ask("OpenAI API Key", password=True)
            if new_key:
                os.environ["OPENAI_API_KEY"] = new_key.strip()
                # Update .env
                try:
                    from dotenv import set_key
                    env_path = Path(".env")
                    if not env_path.exists():
                         env_path.touch()
                    set_key(env_path, "OPENAI_API_KEY", new_key.strip())
                    console.print("[green]✓ Updated .env file[/green]")
                except ImportError:
                    console.print("[yellow]Could not save to local .env (python-dotenv not installed)[/yellow]")
            console.print()
    
    # Run setup wizard on first launch or if --setup flag
    if args.setup or not is_setup_complete():
        provider, model = ensure_setup()
        if not args.model:
            args.model = model
    
    cli = ArkaCLI(model=args.model)
    cli.run()


if __name__ == "__main__":
    main()

