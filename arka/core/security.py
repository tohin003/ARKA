"""
ARKA Security Manager
Handles command validation, whitelisting, and dangerous command detection.
"""

from enum import Enum
from typing import Set, List, Optional
import shlex

class SecurityLevel(Enum):
    SAFE = "safe"
    CONFIRMATION_REQUIRED = "confirmation"
    BLOCKED = "blocked"

class SecurityManager:
    """
    Manages security policies for system interactions.
    """
    
    def __init__(self):
        # Always safe commands
        self.whitelist: Set[str] = {
            "ls", "echo", "cat", "grep", "pwd", "whoami", 
            "mkdir", "touch", "cd", "find", "head", "tail",
            "git status", "git log", "git diff", "date",
            "python --version", "python3 --version", "node -v"
        }
        
        # Dangerous commands that require explicit confirmation
        self.dangerous: Set[str] = {
            "rm", "mv", "cp", "dd", "chmod", "chown", 
            "sudo", "su", "shutdown", "reboot", "kill", 
            "pkill", "killall", "open", "curl", "wget", "ssh"
        }
        
        # Strictly blocked commands (if any)
        self.blocked: Set[str] = {
            "mkfs", ":(){ :|:& };:" # Fork bomb
        }

    def check_command(self, command: str) -> SecurityLevel:
        """
        Check if a command is safe to execute.
        
        Args:
            command: The full command string
            
        Returns:
            SecurityLevel: SAFE, CONFIRMATION_REQUIRED, or BLOCKED
        """
        command = command.strip()
        
        # Empty command is safe (does nothing)
        if not command:
            return SecurityLevel.SAFE
            
        # Check blocked patterns
        for blocked_cmd in self.blocked:
            if blocked_cmd in command:
                return SecurityLevel.BLOCKED
                
        # Parse first token (binary name)
        try:
            parts = shlex.split(command)
            if not parts:
                return SecurityLevel.SAFE
            binary = parts[0]
        except ValueError:
            # shell parsing failed, assume dangerous
            return SecurityLevel.CONFIRMATION_REQUIRED

        # exact match whitelist
        if command in self.whitelist:
            return SecurityLevel.SAFE
            
        # binary match whitelist
        if binary in self.whitelist:
            # Special case for dangerous flags? 
            # For now, let's assume whitelisted binaries are mostly safe unless combined with pipes/redirection
            # But 'cat > file' is dangerous. shlex doesn't split operators.
            if ">" in command or "|" in command:
                return SecurityLevel.CONFIRMATION_REQUIRED
            return SecurityLevel.SAFE
            
        # binary match dangerous
        if binary in self.dangerous:
            return SecurityLevel.CONFIRMATION_REQUIRED
            
        # Default to requiring confirmation for unknown commands
        return SecurityLevel.CONFIRMATION_REQUIRED

# Global instance
_security: Optional[SecurityManager] = None

def get_security_manager() -> SecurityManager:
    global _security
    if _security is None:
        _security = SecurityManager()
    return _security
