"""
AI Agent - Main Entry Point
This is the brain that connects:
- Memory (Vector DB)
- Perception (Screen Intelligence)
- Action (System Controller)
- Reasoning (Qwen 3 Coder via Ollama)
"""
import ollama
from memory_engine import MemoryEngine
from system_controller import SystemController
from screen_intelligence import ScreenIntelligence
from agent_dispatcher import AgentDispatcher
from daily_memory import DailyMemory

class Agent:
    def __init__(self, model_name="qwen3-coder:30b"):
        print("Initializing Agent...")
        self.model = model_name
        
        # Core modules
        self.memory = MemoryEngine()
        self.controller = SystemController()
        self.vision = ScreenIntelligence()
        self.daily_log = DailyMemory()
        self.dispatcher = AgentDispatcher(memory_logger=self.daily_log)
        
        self.daily_log.log_event("SYSTEM", "Agent initialized.")
        print("Agent ready.")

    def think(self, user_request, context=""):
        """
        Use Qwen to reason about a request.
        """
        # Build prompt with context from memory
        memory_context = self.memory.query_similar(user_request, n_results=3)
        memory_snippets = "\n".join(memory_context['documents'][0]) if memory_context['documents'] else ""
        
        system_prompt = f"""You are an AI Agent with full system access on a Mac. You can:
1. Control the mouse and keyboard (click, type, scroll)
2. Take screenshots and read the screen
3. Access the user's personal data (resumes, browsing history)
4. Execute shell commands

User Persona Context:
{memory_snippets[:1000]}

When the user asks for help, plan the steps needed and then execute them.
Be concise and action-oriented.
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_request}
        ]
        
        if context:
            messages.insert(1, {"role": "assistant", "content": f"Current context: {context}"})
        
        response = ollama.chat(model=self.model, messages=messages)
        return response['message']['content']

    def act(self, action_plan):
        """
        Execute an action plan on the system.
        This is a placeholder - actual implementation would parse
        the action_plan and call appropriate SystemController methods.
        """
        # TODO: Parse action plan into executable steps
        print(f"[Act] Would execute: {action_plan[:200]}...")
        self.daily_log.log_event("ACTION", action_plan[:100])

    def assist(self, request):
        """
        Main interface for user requests.
        """
        self.daily_log.log_event("USER", f"Request: {request}")
        
        # Get screen context
        _, screenshot_path = self.vision.capture_screen(save=True)
        
        # Think about the request
        response = self.think(request)
        
        self.daily_log.log_event("AGENT", f"Response: {response[:100]}...")
        return response

    def run_cli(self):
        """
        Simple CLI loop for testing.
        """
        print("\n=== AI Agent CLI ===")
        print("Type 'quit' to exit.\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                if user_input.lower() in ['quit', 'exit']:
                    break
                if not user_input:
                    continue
                    
                response = self.assist(user_input)
                print(f"\nAgent: {response}\n")
                
            except KeyboardInterrupt:
                print("\nExiting...")
                break

if __name__ == "__main__":
    agent = Agent()
    agent.run_cli()
