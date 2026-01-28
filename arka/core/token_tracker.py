"""
ARKA Token Tracker
Tracks token usage and costs across sessions.
Provides live status display and budget enforcement.
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Dict, List

from arka.config import get_config, Config
from arka.core.model_router import MODEL_COSTS


@dataclass
class UsageRecord:
    """Single usage record for tracking."""
    timestamp: float
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    agent: str = "main"


@dataclass
class SessionStats:
    """Stats for current session."""
    start_time: float = field(default_factory=time.time)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    records: List[UsageRecord] = field(default_factory=list)


class TokenTracker:
    """
    Tracks token usage and costs.
    Provides budget enforcement and status display.
    """
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.session = SessionStats()
        self._daily_cost: float = 0.0
        self._daily_date: date = date.today()
        self._current_model: str = self.config.models.default
        self._context_used: int = 0
        
        # Load daily stats from disk
        self._load_daily_stats()
    
    @property
    def context_limit(self) -> int:
        """Get context limit for current model."""
        return self.config.tokens.context_limits.get(self._current_model, 8192)
    
    def record_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        agent: str = "main"
    ) -> float:
        """
        Record token usage and return the cost.
        
        Returns:
            Cost in USD for this usage.
        """
        # Calculate cost
        costs = MODEL_COSTS.get(model, {"input": 0.0, "output": 0.0})
        cost = (input_tokens / 1000 * costs["input"] + 
                output_tokens / 1000 * costs["output"])
        
        # Create record
        record = UsageRecord(
            timestamp=time.time(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            agent=agent,
        )
        
        # Update session stats
        self.session.records.append(record)
        self.session.total_input_tokens += input_tokens
        self.session.total_output_tokens += output_tokens
        self.session.total_cost += cost
        
        # Update daily stats
        self._check_daily_reset()
        self._daily_cost += cost
        
        # Update context tracking
        self._context_used = input_tokens
        self._current_model = model
        
        # Save daily stats
        self._save_daily_stats()
        
        return cost
    
    def check_budget(self) -> Dict[str, bool]:
        """
        Check if budget limits are exceeded.
        
        Returns:
            Dict with 'session_ok', 'daily_ok', 'warning' flags.
        """
        self._check_daily_reset()
        
        session_ok = self.session.total_cost < self.config.budget.session_limit
        daily_ok = self._daily_cost < self.config.budget.daily_limit
        warning = (self._daily_cost / self.config.budget.daily_limit 
                   >= self.config.budget.warning_threshold)
        
        return {
            "session_ok": session_ok,
            "daily_ok": daily_ok,
            "warning": warning and daily_ok,
            "exceeded": not session_ok or not daily_ok,
        }
    
    def get_status_display(self) -> str:
        """
        Get formatted status string for CLI display.
        
        Returns:
            String like: "[gpt-4o] Tokens: 12.3k/128k | Cost: $0.42 | Budget: $4.58"
        """
        # Format tokens
        total_tokens = self.session.total_input_tokens + self.session.total_output_tokens
        if total_tokens >= 1000:
            tokens_str = f"{total_tokens / 1000:.1f}k"
        else:
            tokens_str = str(total_tokens)
        
        # Format context limit
        context_limit = self.context_limit
        if context_limit >= 1000:
            limit_str = f"{context_limit // 1000}k"
        else:
            limit_str = str(context_limit)
        
        # Format costs
        session_cost = f"${self.session.total_cost:.2f}"
        remaining = self.config.budget.daily_limit - self._daily_cost
        remaining_str = f"${max(0, remaining):.2f}"
        
        return (f"[{self._current_model}] "
                f"Tokens: {tokens_str}/{limit_str} | "
                f"Cost: {session_cost} | "
                f"Budget: {remaining_str}")
    
    def get_detailed_stats(self) -> Dict:
        """Get detailed statistics for dashboard."""
        return {
            "session": {
                "start_time": self.session.start_time,
                "duration_seconds": time.time() - self.session.start_time,
                "input_tokens": self.session.total_input_tokens,
                "output_tokens": self.session.total_output_tokens,
                "total_tokens": (self.session.total_input_tokens + 
                                self.session.total_output_tokens),
                "cost": self.session.total_cost,
                "request_count": len(self.session.records),
            },
            "daily": {
                "date": str(self._daily_date),
                "cost": self._daily_cost,
                "budget_limit": self.config.budget.daily_limit,
                "remaining": self.config.budget.daily_limit - self._daily_cost,
            },
            "current_model": self._current_model,
            "context_limit": self.context_limit,
        }
    
    def get_usage_by_agent(self) -> Dict[str, Dict]:
        """Get token usage broken down by agent."""
        by_agent: Dict[str, Dict] = {}
        
        for record in self.session.records:
            if record.agent not in by_agent:
                by_agent[record.agent] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost": 0.0,
                    "requests": 0,
                }
            
            by_agent[record.agent]["input_tokens"] += record.input_tokens
            by_agent[record.agent]["output_tokens"] += record.output_tokens
            by_agent[record.agent]["cost"] += record.cost
            by_agent[record.agent]["requests"] += 1
        
        return by_agent
    
    def set_current_model(self, model: str):
        """Update current model for context tracking."""
        self._current_model = model
    
    def _check_daily_reset(self):
        """Reset daily stats if date has changed."""
        today = date.today()
        if today != self._daily_date:
            self._daily_date = today
            self._daily_cost = 0.0
    
    def _get_stats_path(self) -> Path:
        """Get path for daily stats file."""
        stats_dir = Path.home() / ".arka" / "stats"
        stats_dir.mkdir(parents=True, exist_ok=True)
        return stats_dir / f"daily_{self._daily_date}.json"
    
    def _load_daily_stats(self):
        """Load daily stats from disk."""
        self._check_daily_reset()
        stats_path = self._get_stats_path()
        
        if stats_path.exists():
            try:
                with open(stats_path) as f:
                    data = json.load(f)
                    self._daily_cost = data.get("cost", 0.0)
            except (json.JSONDecodeError, IOError):
                self._daily_cost = 0.0
    
    def _save_daily_stats(self):
        """Save daily stats to disk."""
        stats_path = self._get_stats_path()
        
        try:
            with open(stats_path, "w") as f:
                json.dump({
                    "date": str(self._daily_date),
                    "cost": self._daily_cost,
                    "updated": time.time(),
                }, f)
        except IOError:
            pass  # Non-critical, continue without saving
