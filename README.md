# ARKA - Autonomous Resource & Knowledge Agent

A RAG-based AI Agent CLI with multi-model support, self-improvement via RL, and Claude Code-inspired architecture.

## Features

- **Multi-Model Support**: OpenAI (gpt-4o, o1) + Local LLMs (Qwen3-Coder, Llama3.2 via Ollama)
- **Token & Cost Tracking**: Live display of tokens used and costs incurred
- **Model Toggle**: Switch models per-agent or globally via CLI/config
- **Self-Improvement**: Microsoft Agent Lightning for RL-based optimization
- **Memory Layer**: Mem0 + ChromaDB for persistent context
- **Skill Learning**: Learn from screen recordings, self-code new skills
- **MCP Support**: Connect to Model Context Protocol servers

## Installation

```bash
cd AI_AGENT-V1
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

```bash
# Start ARKA
python -m arka

# With specific model
python -m arka --model gpt-4o-mini

# Slash commands inside ARKA
/model qwen3-coder   # Switch model
/skill list          # List skills
/mcp connect <url>   # Connect MCP server
/budget              # Show remaining budget
```

## Project Structure

```
arka/
├── core/           # Orchestrator, Model Router, Token Tracker
├── agents/         # Planner, Coder, Tester, Debugger
├── memory/         # Mem0, ChromaDB, LlamaIndex loaders
├── tools/          # Bash, File, Browser, MCP
├── skills/         # Skill Forge, trained skills
├── prompts/        # Modular system prompts
└── training/       # Agent Lightning RL wrapper
```

## Configuration

Edit `~/.arka/config.yaml` or `config/config.yaml`:

```yaml
models:
  default: gpt-4o
  coder: qwen3-coder:30b
  memory: llama3.2

budget:
  daily_limit: 5.00  # USD

openai:
  api_key: ${OPENAI_API_KEY}
```

## License

MIT
