"""
ARKA Skill Registry
The backbone of the skill system. Scans, validates, and registers skills.
"""

import importlib.util
import json
import logging

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable, Set

# Configure logging
logger = logging.getLogger("arka.skills")

@dataclass
class SkillCode:
    """Represents a python tool function within a skill."""
    name: str
    func: Callable
    description: str
    parameters: Dict[str, Any]

@dataclass
class SkillDefinition:
    """Complete definition of a loaded skill."""
    name: str
    path: Path
    description: str
    tools: List[SkillCode] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    is_active: bool = True
    error: Optional[str] = None

class DependencyManager:
    """Manages python dependencies for skills."""
    
    @staticmethod
    def get_missing_dependencies(requirements_path: Path) -> List[str]:
        """Check requirements.txt against installed packages."""
        if not requirements_path.exists():
            return []
            
        missing = []
        try:
            from importlib.metadata import distribution, PackageNotFoundError
        except ImportError:
            # Fallback for older python
            return []

        requirements = requirements_path.read_text().splitlines()
        
        for req in requirements:
            req = req.strip()
            if not req or req.startswith("#"):
                continue
            
            # Simple check: parse package name (e.g. "pandas>=1.0" -> "pandas")
            # This is a basic implementation; robust parsing would use 'packaging' library
            pkg_name = req.split(">")[0].split("<")[0].split("=")[0].split("~")[0].strip()
            
            try:
                distribution(pkg_name)
            except PackageNotFoundError:
                missing.append(req)
                
        return missing

class SkillRegistry:
    """
    Dynamic registry for ARKA skills.
    Scans folders, checks deps, loads tools.
    """
    
    def __init__(self, skills_dir: Optional[Path] = None):
        self.skills_dir = skills_dir or Path(__file__).parent
        self.registry: Dict[str, SkillDefinition] = {}
        self.repair_queue_path = Path.home() / ".arka" / "repair_queue.json"
        
        # Ensure repair queue exists
        if not self.repair_queue_path.exists():
            self.repair_queue_path.parent.mkdir(parents=True, exist_ok=True)
            self.repair_queue_path.write_text("[]")
            
    def scan_and_register(self):
        """Recursively scan skills directory and register skills."""
        logger.info(f"Scanning skills in {self.skills_dir}")
        self.registry.clear()
        
        # We look for folders that contain SKILL.md
        for skill_file in self.skills_dir.rglob("SKILL.md"):
            skill_path = skill_file.parent
            skill_name = skill_path.name
            
            # Skip hidden folders
            if skill_name.startswith((".", "__")):
                continue
                
            self._register_skill(skill_name, skill_path)
            
    def _register_skill(self, name: str, path: Path):
        """Register a single skill."""
        logger.info(f"Docs found for skill: {name}")
        
        # 1. Parse Metadata (from SKILL.md frontmatter)
        # For now, we'll just extract description simply or use defaults
        # Todo: Use python-frontmatter if available, or simple parsing
        description = f"Skill: {name}"
        skill_md = path / "SKILL.md"
        if skill_md.exists():
            content = skill_md.read_text()
            # Simple check for description line
            for line in content.splitlines():
                if line.strip().startswith("description:"):
                    description = line.replace("description:", "").strip().strip('"')
                    break
        
        skill_def = SkillDefinition(name=name, path=path, description=description)
        
        # 2. Check Dependencies
        req_file = path / "requirements.txt"
        missing_deps = DependencyManager.get_missing_dependencies(req_file)
        
        if missing_deps:
            logger.warning(f"Skill '{name}' missing dependencies: {missing_deps}")
            skill_def.is_active = False
            skill_def.error = f"Missing dependencies: {', '.join(missing_deps)}"
            skill_def.dependencies = missing_deps
            self._add_to_repair_queue(skill_def)
            self.registry[name] = skill_def
            return

        # 3. Load Tools (tools.py)
        tools_file = path / "tools.py"
        if tools_file.exists():
            try:
                tools = self._load_tools_from_module(name, tools_file)
                skill_def.tools = tools
            except Exception as e:
                logger.error(f"Failed to load tools for {name}: {e}")
                skill_def.is_active = False
                skill_def.error = f"Import error: {str(e)}"
                self._add_to_repair_queue(skill_def)
                self.registry[name] = skill_def
                return
                
        self.registry[name] = skill_def
        logger.info(f"Successfully registered skill: {name} with {len(skill_def.tools)} tools")

    def _load_tools_from_module(self, skill_name: str, file_path: Path) -> List[SkillCode]:
        """Dynamically import a module and find @arka_tool functions."""
        spec = importlib.util.spec_from_file_location(f"arka.skills.{skill_name}.tools", file_path)
        if not spec or not spec.loader:
            raise ImportError(f"Could not load spec for {file_path}")
            
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"arka.skills.{skill_name}.tools"] = module
        spec.loader.exec_module(module)
        
        found_tools = []
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if callable(attr) and hasattr(attr, "_is_arka_tool"):
                # It's an @arka_tool decorated function
                tool_info = SkillCode(
                    name=attr._tool_name,
                    func=attr,
                    description=attr._tool_description,
                    parameters=attr._tool_parameters
                )
                found_tools.append(tool_info)
                
        return found_tools

    def _add_to_repair_queue(self, skill: SkillDefinition):
        """Add broken skill to persistent repair queue."""
        try:
            current_queue = json.loads(self.repair_queue_path.read_text())
        except:
            current_queue = []
            
        # Check if already in queue
        if any(item["name"] == skill.name for item in current_queue):
            return

        entry = {
            "name": skill.name,
            "path": str(skill.path),
            "error": skill.error,
            "missing_dependencies": skill.dependencies,
            "timestamp": "now" # Todo: real timestamp
        }
        current_queue.append(entry)
        self.repair_queue_path.write_text(json.dumps(current_queue, indent=2))
        
    def get_all_tools(self) -> List[Dict]:
        """Get OpenAI-compatible tool definitions for all active skills."""
        definitions = []
        for skill in self.registry.values():
            if not skill.is_active:
                continue
                
            for tool in skill.tools:
                definitions.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters
                    }
                })
        return definitions

    def get_tool_func(self, tool_name: str) -> Optional[Callable]:
        """Find the callable for a tool name."""
        for skill in self.registry.values():
            if not skill.is_active:
                continue
            for tool in skill.tools:
                if tool.name == tool_name:
                    return tool.func
        return None

# Global Instance
_registry: Optional[SkillRegistry] = None

def get_skill_registry() -> SkillRegistry:
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
        _registry.scan_and_register()
    return _registry
