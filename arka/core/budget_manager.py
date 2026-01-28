"""
ARKA Budget Manager
Enforce spending limits and provide budget controls.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime, date
import json
from pathlib import Path


@dataclass
class BudgetAlert:
    """A budget alert/warning."""
    level: str  # "warning", "critical", "exceeded"
    message: str
    timestamp: str
    current_spend: float
    limit: float


@dataclass
class BudgetStatus:
    """Current budget status."""
    daily_limit: float
    daily_spent: float
    daily_remaining: float
    session_limit: float
    session_spent: float
    session_remaining: float
    is_exceeded: bool
    is_warning: bool
    alerts: List[BudgetAlert] = field(default_factory=list)
    
    @property
    def summary(self) -> str:
        status = "⚠ EXCEEDED" if self.is_exceeded else ("⚠ Warning" if self.is_warning else "✓ OK")
        return f"Daily: ${self.daily_spent:.2f}/${self.daily_limit:.2f} | Session: ${self.session_spent:.2f}/${self.session_limit:.2f} [{status}]"


class BudgetManager:
    """
    Budget management and enforcement.
    Tracks spending and enforces limits.
    """
    
    def __init__(
        self,
        daily_limit: float = 10.0,
        session_limit: float = 3.0,
        warning_threshold: float = 0.80,
        persist_path: Optional[Path] = None,
    ):
        self.daily_limit = daily_limit
        self.session_limit = session_limit
        self.warning_threshold = warning_threshold
        self.persist_path = persist_path or Path.home() / ".arka" / "budget.json"
        
        self._session_spent = 0.0
        self._daily_data: Dict[str, float] = {}
        self._alerts: List[BudgetAlert] = []
        
        self._load()
    
    def _load(self):
        """Load persistent budget data."""
        if self.persist_path.exists():
            try:
                data = json.loads(self.persist_path.read_text())
                self._daily_data = data.get("daily_data", {})
            except Exception:
                pass
    
    def _save(self):
        """Save persistent budget data."""
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "daily_data": self._daily_data,
            "last_updated": datetime.now().isoformat(),
        }
        self.persist_path.write_text(json.dumps(data, indent=2))
    
    def _today_key(self) -> str:
        """Get today's date key."""
        return date.today().isoformat()
    
    @property
    def daily_spent(self) -> float:
        """Get today's spending."""
        return self._daily_data.get(self._today_key(), 0.0)
    
    @property
    def session_spent(self) -> float:
        """Get current session spending."""
        return self._session_spent
    
    def record_cost(self, cost: float, model: str = "unknown"):
        """
        Record a cost.
        
        Args:
            cost: Cost in USD
            model: Model that incurred the cost
        """
        # Update session
        self._session_spent += cost
        
        # Update daily
        today = self._today_key()
        self._daily_data[today] = self._daily_data.get(today, 0.0) + cost
        
        # Save
        self._save()
        
        # Check for alerts
        self._check_alerts()
    
    def _check_alerts(self):
        """Check and create budget alerts."""
        status = self.get_status()
        
        if status.is_exceeded:
            self._alerts.append(BudgetAlert(
                level="exceeded",
                message="Budget limit exceeded! Operations paused.",
                timestamp=datetime.now().isoformat(),
                current_spend=status.daily_spent,
                limit=status.daily_limit,
            ))
        elif status.is_warning:
            pct = (status.daily_spent / status.daily_limit) * 100
            self._alerts.append(BudgetAlert(
                level="warning",
                message=f"Budget warning: {pct:.0f}% of daily limit used.",
                timestamp=datetime.now().isoformat(),
                current_spend=status.daily_spent,
                limit=status.daily_limit,
            ))
    
    def get_status(self) -> BudgetStatus:
        """Get current budget status."""
        daily_spent = self.daily_spent
        session_spent = self.session_spent
        
        daily_remaining = max(0, self.daily_limit - daily_spent)
        session_remaining = max(0, self.session_limit - session_spent)
        
        is_exceeded = daily_spent >= self.daily_limit or session_spent >= self.session_limit
        is_warning = (
            daily_spent >= self.daily_limit * self.warning_threshold or
            session_spent >= self.session_limit * self.warning_threshold
        )
        
        return BudgetStatus(
            daily_limit=self.daily_limit,
            daily_spent=daily_spent,
            daily_remaining=daily_remaining,
            session_limit=self.session_limit,
            session_spent=session_spent,
            session_remaining=session_remaining,
            is_exceeded=is_exceeded,
            is_warning=is_warning,
            alerts=self._alerts[-5:],  # Last 5 alerts
        )
    
    def can_proceed(self, estimated_cost: float = 0.0) -> bool:
        """
        Check if we can proceed with an operation.
        
        Args:
            estimated_cost: Estimated cost of the operation
            
        Returns:
            True if within budget
        """
        status = self.get_status()
        
        if status.is_exceeded:
            return False
        
        # Check if estimated cost would exceed
        if estimated_cost > 0:
            would_exceed = (
                self.daily_spent + estimated_cost > self.daily_limit or
                self.session_spent + estimated_cost > self.session_limit
            )
            return not would_exceed
        
        return True
    
    def reset_session(self):
        """Reset session spending (call on new session)."""
        self._session_spent = 0.0
        self._alerts.clear()
    
    def set_limits(
        self,
        daily_limit: Optional[float] = None,
        session_limit: Optional[float] = None,
    ):
        """Update budget limits."""
        if daily_limit is not None:
            self.daily_limit = daily_limit
        if session_limit is not None:
            self.session_limit = session_limit
    
    def get_history(self, days: int = 7) -> Dict[str, float]:
        """Get spending history for recent days."""
        result = {}
        today = date.today()
        
        for i in range(days):
            day = date(today.year, today.month, today.day - i) if today.day > i else today
            key = day.isoformat()
            result[key] = self._daily_data.get(key, 0.0)
        
        return result
    
    def get_alerts(self, limit: int = 10) -> List[BudgetAlert]:
        """Get recent alerts."""
        return self._alerts[-limit:]


# Global budget manager
_manager: Optional[BudgetManager] = None


def get_budget_manager() -> BudgetManager:
    """Get or create global budget manager."""
    global _manager
    if _manager is None:
        _manager = BudgetManager()
    return _manager
