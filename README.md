# ARKA - Autonomous Resource & Knowledge Agent

> **"Think -> Plan -> Execute"**

ARKA is a next-generation AI Agent CLI designed with a strict **Thinking-First** architecture. It separates high-level reasoning (using OpenAI o1) from fast, low-latency execution (using Vision/GPT-4o), connected by a **Rolling Plan** feedback loop and Reinforcement Learning.

## 🧠 Core Architecture

ARKA follows a strict **Anti-Gravity** pattern to prevent execution loops and ensure long-horizon task success:

### 1. Receptionist (Router)
- **Role**: Understands user intent.
- **Model**: Fast LLM (`gpt-5.2` / `gpt-4o`).
- **Action**: Routes complex tasks to the **Planner**.

### 2. Planner (The Brain)
- **Role**: Decomposes vague requirements into granular steps.
- **Model**: **OpenAI o1 (Reasoning Model)**.
- **Output**: A structured initial plan.

### 3. Execution with "Rolling Plan" (The Hands)
- **Role**: Executes the plan in interaction "chunks".
- **Model**: **GuiAgent (Vision)**.
- **The Loop**:
    1.  **Execute 5 Steps**: The Vision model performs 5 atomic actions (clicks, types) based on the current plan.
    2.  **Checkpoint (o1)**: The agent pauses and sends the execution history back to the **Reasoning Model (o1)**.
    3.  **Success Check**: o1 checks if the goal is met (e.g., "Video is playing"). If yes, STOP.
    4.  **Re-Plan**: If not done, o1 generates the **Next 5 Steps**.
    5.  **Repeat**: This cycle continues until success or strict loop guards intervene.

### 4. Reinforcement Learning (RL)
- **Role**: Learn from mistakes and user preference.
- **Mechanism**:
    -   After every task, the user provides a rating **(1-5)** via CLI.
    -   **Positive Feedback**: Strengthens the memory of the strategy used.
    -   **Negative Feedback**: Stores "Mistakes to Avoid".
    -   **Future Injection**: When planning similar tasks, o1 receives a context block: `=== LEARNED MISTAKES ===`, preventing repeated errors.

---

## ✨ Features

- **Architectural Integrity**: Enforced "Think -> Plan -> Execute" workflow.
- **Rolling Plans**: Dynamic course correction every 5 steps using Reasoning Models.
- **Vision-First GUI**: Uses screenshots and DOM trees for precise element interaction.
- **External RL Feedback**: User-in-the-loop reinforcement learning.
- **Self-Healing**: Automatic recovery from error states using Plan reflection.
- **Multi-Model Support**: OpenAI (gpt-4o, o1) + Local LLMs (Qwen3-Coder, Llama3.2).
- **Cost Tracking**: Live display of tokens and API costs per session.

---

## 🚀 Installation

```bash
git clone https://github.com/tohin003/ARKA.git
cd ARKA
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 💻 Usage

```bash
# Start ARKA CLI
python -m arka

# With specific model configuration
python -m arka --model gpt-4o-mini
```

### CLI Commands
- `rl_feedback>`: (Appears after task) Rate the agent's performance (1-5).
- `/model <name>`: Switch active models.
- `/skill list`: View learned capabilities.
- `/budget`: Check API usage and remaining budget.
- `Cmd+Shift+P`: **Global Emergency Stop** (Pause Agent).

---

## ⚙️ Configuration

Edit `config/config.yaml` to tune the architecture:

```yaml
models:
  default: gpt-4o
  planner: o1-preview      # The Brain (Thinking)
  gui_vision: gpt-4o       # The Hands (Acting)
  gui_reasoner: o1-preview # The Checkpoint Auditor

agent:
  max_checkpoints: 10      # Max "Rolling Plan" loops before termination
  checkpoint_interval: 5   # Steps to take before consulting o1
```

## 📂 Project Structure

```
arka/
├── core/           # Orchestrator (Receptionist) & Router
├── agents/         # Planner (o1), GuiAgent (Vision + Rolling Loop)
├── memory/         # Semantic Memory & RL Trainer
├── tools/          # System Tools (Browser, File, Shell)
├── skills/         # Learned Behaviors
└── training/       # Reinforcement Learning Module
```

## License

MIT
