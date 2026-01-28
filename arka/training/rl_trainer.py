"""
ARKA Training Module
Integration with Microsoft Agent Lightning for RL-based optimization.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class RewardSignal(Enum):
    """Types of reward signals."""
    SUCCESS = "success"           # Task completed successfully
    PARTIAL = "partial"           # Partial success
    FAILURE = "failure"           # Task failed
    TIMEOUT = "timeout"           # Task timed out
    REJECTED = "rejected"         # User rejected output
    ACCEPTED = "accepted"         # User accepted output


@dataclass
class TrainingExample:
    """A single training example for RL."""
    state: Dict[str, Any]         # Input state/context
    action: str                   # Action taken (prompt/response)
    reward: float                 # Reward signal (-1 to 1)
    next_state: Optional[Dict]    # Resulting state
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "action": self.action,
            "reward": self.reward,
            "next_state": self.next_state,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


class RewardFunction:
    """
    Reward function for agent training.
    Calculates rewards based on task outcomes.
    """
    
    def __init__(self):
        # Reward weights
        self.weights = {
            "task_success": 1.0,
            "efficiency_bonus": 0.2,
            "user_satisfaction": 0.5,
            "cost_penalty": -0.1,
            "error_penalty": -0.5,
        }
    
    def calculate(
        self,
        task_success: bool,
        user_feedback: Optional[str] = None,
        tokens_used: int = 0,
        errors: int = 0,
        duration: float = 0.0,
    ) -> float:
        """
        Calculate reward for a task execution.
        
        Args:
            task_success: Whether task completed successfully
            user_feedback: Optional user feedback (positive/negative/neutral)
            tokens_used: Number of tokens used
            errors: Number of errors encountered
            duration: Task duration in seconds
            
        Returns:
            Reward value between -1 and 1
        """
        reward = 0.0
        
        # Base success/failure reward
        if task_success:
            reward += self.weights["task_success"]
        else:
            reward += self.weights["error_penalty"]
        
        # User satisfaction
        if user_feedback:
            if user_feedback.lower() in ["positive", "good", "yes", "accept"]:
                reward += self.weights["user_satisfaction"]
            elif user_feedback.lower() in ["negative", "bad", "no", "reject"]:
                reward -= self.weights["user_satisfaction"]
        
        # Efficiency bonus (fewer tokens is better)
        if tokens_used < 1000 and task_success:
            reward += self.weights["efficiency_bonus"]
        elif tokens_used > 10000:
            reward += self.weights["cost_penalty"]
        
        # Error penalty
        reward += errors * self.weights["error_penalty"]
        
        # Clamp to [-1, 1]
        return max(-1.0, min(1.0, reward))


class SemanticPatternTrainer:
    """
    Feedback-Driven Semantic Memory Trainer.
    
    Instead of traditional RL gradient updates (which require expensive re-training),
    this system uses 'Semantic Memory' to store successful state-action pairs (few-shot examples).
    
    Mechanics:
    1. Successful interactions (Reward > 0.8) are saved to Vector Memory (ChromaDB).
    2. At inference time, relevant past successes are retrieved via RAG and injected into the prompt.
    3. User feedback ('good'/'bad') updates the 'reward' metadata of stored patterns, prioritizing valid examples.
    """
    
    def __init__(self):
        self.reward_fn = RewardFunction()
        from arka.memory.memory_client import get_memory
        self.memory = get_memory()
        self._training_enabled = True
    
    def log_interaction(
        self,
        task: str,
        response: str,
        success: bool,
        user_feedback: Optional[str] = None,
        tokens_used: int = 0,
        metadata: Optional[Dict] = None,
    ):
        """
        Log an interaction for semantic learning.
        Stores successful patterns in memory for future RAG retrieval.
        """
        # Calculate reward
        reward = self.reward_fn.calculate(
            task_success=success,
            user_feedback=user_feedback,
            tokens_used=tokens_used,
        )
        
        # Only store high-value interactions or explicitly feedbacked ones
        if reward < 0.8 and not user_feedback:
            return
            
        timestamp = datetime.now().isoformat()
        
        # Store in semantic memory as a re-usable pattern
        self.memory.add(
            content=f"Task: {task}\nResponse: {response}",
            metadata={
                "type": "rl_pattern",
                "task": task,
                "response": response,
                "reward": reward,
                "timestamp": timestamp,
                "success": success,
                "tokens": tokens_used,
                "feedback": user_feedback or "",
                **(metadata or {}),
            }
        )
    
    def update_last_interaction(self, feedback: str, score_adjustment: float):
        """
        Update the most recent interaction based on user feedback.
        Searches for the most recent 'rl_pattern' memory and adjusts its score.
        """
        # Find most recent RL pattern
        recent = self.memory.search(
            "recent interaction", 
            limit=5, 
            filter_metadata={"type": "rl_pattern"}
        )
        
        if not recent:
            return

        # Sort by timestamp in metadata (descending)
        try:
            recent.sort(key=lambda x: x.metadata.get("timestamp", ""), reverse=True)
            top_entry = recent[0]
            
            # Update metadata locally
            current_reward = float(top_entry.metadata.get("reward", 0.0))
            new_reward = max(-1.0, min(1.0, current_reward + score_adjustment))
            
            top_entry.metadata["reward"] = new_reward
            top_entry.metadata["user_feedback"] = feedback
            
            # Update in Memory (Delete + Add)
            self.memory.delete(top_entry.id)
            self.memory.add(
                content=top_entry.content,
                metadata=top_entry.metadata,
                memory_id=top_entry.id 
            )
        except Exception as e:
            print(f"Error updating interaction: {e}")

    def get_relevant_examples(self, task: str, limit: int = 3) -> List[Dict]:
        """Get relevant successful examples for a task (RAG)."""
        results = self.memory.search(
            task,
            limit=limit,
            filter_metadata={"type": "rl_pattern"}
        )
        
        # Filter for high reward
        good_examples = []
        for r in results:
            if float(r.metadata.get("reward", 0.0)) >= 0.8:
                good_examples.append({
                    "state": {"task": r.metadata.get("task", "")},
                    "action": r.metadata.get("response", ""),
                    "reward": float(r.metadata.get("reward", 0.0))
                })
        
        return good_examples
    
    def get_training_stats(self) -> Dict[str, Any]:
        """Get training statistics."""
        return {
            "status": "active", 
            "backend": "semantic_memory",
            "type": "few_shot_rag"
        }
    
    def export_for_training(self, output_path: Path) -> int:
        """
        Export learned patterns for potential fine-tuning.
        Retrieves all 'rl_pattern' items from memory.
        
        Args:
            output_path: Path to save training data
            
        Returns:
            Number of examples exported
        """
        # Retrieve all learned patterns
        memories = self.memory.get_all(filter_metadata={"type": "rl_pattern"})
        
        examples = []
        for m in memories:
            examples.append({
                "state": {"task": m.metadata.get("task")},
                "action": m.metadata.get("response"),
                "reward": m.metadata.get("reward"),
                "metadata": m.metadata
            })
            
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(examples, indent=2))
        return len(examples)


# Global trainer
_trainer: Optional[SemanticPatternTrainer] = None


def get_trainer() -> SemanticPatternTrainer:
    """Get or create global trainer."""
    global _trainer
    if _trainer is None:
        _trainer = SemanticPatternTrainer()
    return _trainer
