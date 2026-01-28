"""
ARKA Resource Monitor
Monitor CPU, RAM, and system resources to prevent overload.
"""

import time
import threading
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class ResourceStatus(Enum):
    """Resource status levels."""
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class ResourceSnapshot:
    """A snapshot of system resources."""
    timestamp: float
    cpu_percent: float
    ram_percent: float
    ram_used_gb: float
    ram_total_gb: float
    disk_percent: float
    status: ResourceStatus = ResourceStatus.OK
    
    @property
    def summary(self) -> str:
        return f"CPU: {self.cpu_percent:.1f}% | RAM: {self.ram_percent:.1f}% ({self.ram_used_gb:.1f}/{self.ram_total_gb:.1f}GB)"


@dataclass
class ResourceThresholds:
    """Thresholds for resource warnings."""
    cpu_warning: float = 99.0
    cpu_critical: float = 99.9
    ram_warning: float = 99.0
    ram_critical: float = 99.9
    disk_warning: float = 90.0
    disk_critical: float = 95.0


class ResourceMonitor:
    """
    Monitor system resources and trigger callbacks on thresholds.
    """
    
    def __init__(
        self,
        thresholds: Optional[ResourceThresholds] = None,
        check_interval: float = 1.0,
    ):
        self.thresholds = thresholds or ResourceThresholds()
        self.check_interval = check_interval
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable[[ResourceSnapshot], None]] = []
        self._history: List[ResourceSnapshot] = []
        self._max_history = 100
        self._paused = False
    
    def get_snapshot(self) -> ResourceSnapshot:
        """Get current resource snapshot."""
        if not PSUTIL_AVAILABLE:
            return ResourceSnapshot(
                timestamp=time.time(),
                cpu_percent=0.0,
                ram_percent=0.0,
                ram_used_gb=0.0,
                ram_total_gb=8.0,
                disk_percent=0.0,
                status=ResourceStatus.OK,
            )
        
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        
        # Determine status
        status = ResourceStatus.OK
        if cpu >= self.thresholds.cpu_critical or mem.percent >= self.thresholds.ram_critical:
            status = ResourceStatus.CRITICAL
        elif cpu >= self.thresholds.cpu_warning or mem.percent >= self.thresholds.ram_warning:
            status = ResourceStatus.WARNING
        
        return ResourceSnapshot(
            timestamp=time.time(),
            cpu_percent=cpu,
            ram_percent=mem.percent,
            ram_used_gb=mem.used / (1024 ** 3),
            ram_total_gb=mem.total / (1024 ** 3),
            disk_percent=disk.percent,
            status=status,
        )
    
    def start(self):
        """Start background monitoring."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop background monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
    
    def _monitor_loop(self):
        """Background monitoring loop."""
        while self._running:
            snapshot = self.get_snapshot()
            
            # Store in history
            self._history.append(snapshot)
            if len(self._history) > self._max_history:
                self._history.pop(0)
            
            # Check if we should pause
            if snapshot.status == ResourceStatus.CRITICAL:
                self._paused = True
            elif snapshot.status == ResourceStatus.OK:
                self._paused = False
            
            # Trigger callbacks
            for callback in self._callbacks:
                try:
                    callback(snapshot)
                except Exception:
                    pass
            
            time.sleep(self.check_interval)
    
    def add_callback(self, callback: Callable[[ResourceSnapshot], None]):
        """Add a callback to be called on each check."""
        self._callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[ResourceSnapshot], None]):
        """Remove a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    @property
    def is_paused(self) -> bool:
        """Check if operations should be paused due to high resources."""
        return self._paused
    
    def should_proceed(self) -> bool:
        """Check if it's safe to proceed with operations."""
        snapshot = self.get_snapshot()
        # Fail if in WARNING or CRITICAL state
        return snapshot.status == ResourceStatus.OK
    
    def wait_for_resources(self, timeout: float = 60.0) -> bool:
        """
        Wait until resources are available.
        
        Args:
            timeout: Maximum wait time
            
        Returns:
            True if resources became available, False if timeout
        """
        start = time.time()
        while time.time() - start < timeout:
            if self.should_proceed():
                return True
            time.sleep(1.0)
        return False
    
    def get_history(self, limit: int = 10) -> List[ResourceSnapshot]:
        """Get recent resource history."""
        return self._history[-limit:]
    
    def get_average(self, window: int = 10) -> Dict[str, float]:
        """Get average resource usage over recent window."""
        recent = self._history[-window:] if self._history else [self.get_snapshot()]
        
        return {
            "cpu": sum(s.cpu_percent for s in recent) / len(recent),
            "ram": sum(s.ram_percent for s in recent) / len(recent),
            "disk": sum(s.disk_percent for s in recent) / len(recent),
        }


# Global monitor
_monitor: Optional[ResourceMonitor] = None


def get_resource_monitor() -> ResourceMonitor:
    """Get or create global resource monitor."""
    global _monitor
    if _monitor is None:
        _monitor = ResourceMonitor()
    return _monitor
