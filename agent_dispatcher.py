import psutil
import threading
import time
from daily_memory import DailyMemory

class AgentDispatcher:
    """
    Agent Dispatcher - The "Brain" that manages tasks and sub-agents.
    Monitors resources and decides whether to execute or queue tasks.
    """
    def __init__(self, memory_logger=None):
        self.active_tasks = []
        self.memory = memory_logger or DailyMemory()
        self.cpu_threshold = 80  # Percentage
        self.ram_threshold = 90  # Percentage

    # ========== RESOURCE MONITORING ==========
    def get_resource_status(self):
        """Get current CPU and RAM usage."""
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory().percent
        return {"cpu": cpu, "ram": ram}

    def resources_available(self):
        """Check if resources are available for a new task."""
        status = self.get_resource_status()
        if status["cpu"] > self.cpu_threshold:
            return False, f"CPU high ({status['cpu']}%)"
        if status["ram"] > self.ram_threshold:
            return False, f"RAM high ({status['ram']}%)"
        return True, "Resources OK"

    # ========== TASK MANAGEMENT ==========
    def execute_task(self, task_fn, task_name, *args, **kwargs):
        """
        Execute a task if resources are available.
        Otherwise, notify user and queue.
        """
        available, reason = self.resources_available()
        
        if not available:
            self.memory.log_event("SYSTEM", f"Task '{task_name}' queued: {reason}")
            print(f"[Dispatcher] Cannot start '{task_name}': {reason}. Queuing...")
            # TODO: Implement actual queue
            return False

        # Execute in a thread
        self.memory.log_event("SYSTEM", f"Starting task: {task_name}")
        thread = threading.Thread(target=task_fn, args=args, kwargs=kwargs, name=task_name)
        thread.start()
        self.active_tasks.append(thread)
        return True

    def spawn_subagent(self, task_fn, task_name, *args, **kwargs):
        """
        Spawn a sub-agent (just a named thread for now).
        In the future, this could be a separate process or container.
        """
        return self.execute_task(task_fn, task_name, *args, **kwargs)

    def wait_for_all(self):
        """Wait for all active tasks to complete."""
        for task in self.active_tasks:
            task.join()
        self.active_tasks = []

    # ========== INSTANT ASSIST TRIGGER ==========
    def instant_assist(self, user_request, context=None):
        """
        Main entry point for 'Instant Assist' feature.
        Called when user triggers help (e.g., hotkey, CLI).
        """
        self.memory.log_event("USER", f"Instant Assist triggered: {user_request}")
        
        # Placeholder: In a real system, this would:
        # 1. Capture screen (Screen Intelligence)
        # 2. Query Vector DB for context
        # 3. Use Qwen to plan actions
        # 4. Execute via System Controller
        
        print(f"[Instant Assist] Request: {user_request}")
        print(f"[Instant Assist] Context: {context}")
        
        # Return placeholder response
        return {"status": "processing", "request": user_request}

if __name__ == "__main__":
    dispatcher = AgentDispatcher()
    
    print("Resource Status:", dispatcher.get_resource_status())
    available, reason = dispatcher.resources_available()
    print(f"Resources Available: {available} ({reason})")
    
    # Test task execution
    def sample_task():
        print("[Task] Running sample task...")
        time.sleep(2)
        print("[Task] Done!")
    
    dispatcher.execute_task(sample_task, "SampleTask")
    dispatcher.wait_for_all()
