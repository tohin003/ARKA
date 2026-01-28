"""
ARKA Skill Forge
Learn, store, and execute learned skills.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Skill:
    """A learned skill."""
    name: str
    description: str
    steps: List[str]
    created_at: str
    last_used: Optional[str] = None
    usage_count: int = 0
    success_rate: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "steps": self.steps,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Skill":
        return cls(**data)


class SkillForge:
    """
    Skill learning and execution system.
    Skills are sequences of actions that can be saved and reused.
    """
    
    def __init__(self, skills_dir: Optional[Path] = None):
        self.skills_dir = skills_dir or Path.home() / ".arka" / "skills"
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        
        self._skills: Dict[str, Skill] = {}
        self._load_skills()
    
    def _load_skills(self):
        """Load all skills from disk."""
        for skill_file in self.skills_dir.glob("*.json"):
            try:
                data = json.loads(skill_file.read_text())
                skill = Skill.from_dict(data)
                self._skills[skill.name] = skill
            except Exception:
                pass  # Skip invalid skill files
    
    def _save_skill(self, skill: Skill):
        """Save a skill to disk."""
        skill_file = self.skills_dir / f"{skill.name}.json"
        skill_file.write_text(json.dumps(skill.to_dict(), indent=2))
    
    def learn(
        self,
        name: str,
        description: str,
        steps: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Skill:
        """
        Learn a new skill.
        
        Args:
            name: Unique skill name
            description: What the skill does
            steps: List of steps/actions
            metadata: Optional additional data
            
        Returns:
            The created Skill
        """
        skill = Skill(
            name=name,
            description=description,
            steps=steps,
            created_at=datetime.now().isoformat(),
            metadata=metadata or {},
        )
        
        self._skills[name] = skill
        self._save_skill(skill)
        
        return skill
    
    def get(self, name: str) -> Optional[Skill]:
        """Get a skill by name."""
        return self._skills.get(name)
    
    def list_skills(self) -> List[Skill]:
        """List all available skills."""
        return list(self._skills.values())
    
    def search(self, query: str) -> List[Skill]:
        """Search skills by name or description."""
        query_lower = query.lower()
        return [
            skill for skill in self._skills.values()
            if query_lower in skill.name.lower() 
            or query_lower in skill.description.lower()
        ]
    
    def delete(self, name: str) -> bool:
        """Delete a skill."""
        if name not in self._skills:
            return False
        
        del self._skills[name]
        skill_file = self.skills_dir / f"{name}.json"
        if skill_file.exists():
            skill_file.unlink()
        
        return True
    
    def record_usage(self, name: str, success: bool):
        """Record skill usage for statistics."""
        if name not in self._skills:
            return
        
        skill = self._skills[name]
        skill.usage_count += 1
        skill.last_used = datetime.now().isoformat()
        
        # Update success rate (exponential moving average)
        alpha = 0.3
        skill.success_rate = alpha * (1.0 if success else 0.0) + (1 - alpha) * skill.success_rate
        
        self._save_skill(skill)

    def update_skill_logic(
        self, 
        name: str, 
        new_steps: List[str], 
        new_description: Optional[str] = None,
        metadata_update: Optional[Dict] = None
    ) -> bool:
        """
        Update the core logic (steps) of a skill based on optimization/feedback.
        
        Args:
            name: Skill name
            new_steps: New list of actions/code
            new_description: Optional updated description
            metadata_update: Optional metadata to merge in
            
        Returns:
            True if successful
        """
        if name not in self._skills:
            return False
            
        skill = self._skills[name]
        skill.steps = new_steps
        if new_description:
            skill.description = new_description
            
        if metadata_update:
            skill.metadata.update(metadata_update)
            
        # Add improvement history
        if "optimization_history" not in skill.metadata:
            skill.metadata["optimization_history"] = []
            
        skill.metadata["optimization_history"].append({
            "timestamp": datetime.now().isoformat(),
            "change_type": "logic_optimization",
            "prev_step_count": len(skill.steps)
        })
        
        self._save_skill(skill)
        return True
    
    def export_skill(self, name: str) -> Optional[str]:
        """Export a skill as JSON string."""
        skill = self.get(name)
        if skill:
            return json.dumps(skill.to_dict(), indent=2)
        return None
    
    def import_skill(self, json_data: str) -> Optional[Skill]:
        """Import a skill from JSON string."""
        try:
            data = json.loads(json_data)
            skill = Skill.from_dict(data)
            self._skills[skill.name] = skill
            self._save_skill(skill)
            return skill
        except Exception:
            return None
    
    def get_prompt_for_skill(self, name: str) -> Optional[str]:
        """Generate a prompt that describes how to execute a skill."""
        skill = self.get(name)
        if not skill:
            return None
        
        steps_text = "\n".join(f"{i+1}. {step}" for i, step in enumerate(skill.steps))
        
        return f"""Execute the skill "{skill.name}":

Description: {skill.description}

Steps:
{steps_text}

Follow these steps exactly to complete the task."""


# Global skill forge
_forge: Optional[SkillForge] = None


def get_skill_forge() -> SkillForge:
    """Get or create global skill forge."""
    global _forge
    if _forge is None:
        _forge = SkillForge()
    return _forge
