"""
ARKA Configuration Loader
Loads and manages configuration from YAML files and environment variables.
"""

import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ModelConfig:
    """Model configuration for each agent (OpenAI only)."""
    default: str = "gpt-4o"
    planner: str = "gpt-4o"
    coder: str = "gpt-5.2-codex"      # Best for coding
    tester: str = "gpt-4o-mini"
    debugger: str = "gpt-5.2-codex"   # Strong for debugging
    memory_manager: str = "gpt-4o-mini"


@dataclass
class BudgetConfig:
    """Budget and cost control settings."""
    daily_limit: float = 10.00
    session_limit: float = 3.00
    warning_threshold: float = 0.80


@dataclass
class TokenConfig:
    """Token limits per model."""
    context_limits: Dict[str, int] = field(default_factory=lambda: {
        "gpt-4o": 128000,
        "gpt-4o-mini": 128000,
        "gpt-5.2-codex": 128000,
        "o1-preview": 128000,
        "o1-mini": 128000,
    })


@dataclass
class OpenAIConfig:
    """OpenAI API configuration."""
    api_key: str = ""
    available_models: List[str] = field(default_factory=lambda: [
        "gpt-4o", "gpt-4o-mini", "gpt-5.2-codex", "o1-preview", "o1-mini"
    ])


@dataclass
class ResourceConfig:
    """System resource monitoring settings."""
    cpu_pause_threshold: int = 90
    ram_pause_threshold: int = 85
    check_interval: int = 5


@dataclass
class Config:
    """Main configuration container."""
    models: ModelConfig = field(default_factory=ModelConfig)
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    tokens: TokenConfig = field(default_factory=TokenConfig)
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    resources: ResourceConfig = field(default_factory=ResourceConfig)


def load_config(config_path: Optional[str] = None) -> Config:
    """
    Load configuration from YAML file.
    
    Priority:
    1. Explicit path passed as argument
    2. ~/.arka/config.yaml
    3. ./config/config.yaml
    4. Default values
    """
    config = Config()
    
    # Determine config file path
    if config_path:
        paths = [Path(config_path)]
    else:
        paths = [
            Path.home() / ".arka" / "config.yaml",
            Path(__file__).parent.parent / "config" / "config.yaml",
        ]
    
    # Load first available config file
    for path in paths:
        if path.exists():
            with open(path, 'r') as f:
                data = yaml.safe_load(f) or {}
            
            # Parse models
            if 'models' in data:
                config.models = ModelConfig(**{
                    k: v for k, v in data['models'].items() 
                    if k in ModelConfig.__dataclass_fields__
                })
            
            # Parse budget
            if 'budget' in data:
                config.budget = BudgetConfig(**data['budget'])
            
            # Parse OpenAI
            if 'openai' in data:
                api_key = data['openai'].get('api_key', '')
                # Resolve environment variable
                if api_key.startswith('${') and api_key.endswith('}'):
                    env_var = api_key[2:-1]
                    api_key = os.environ.get(env_var, '')
                config.openai = OpenAIConfig(
                    api_key=api_key,
                    available_models=data['openai'].get('available_models', 
                                                        config.openai.available_models)
                )
            
            # Parse resources
            if 'resources' in data:
                config.resources = ResourceConfig(**data['resources'])
            
            break
    
    # Override with environment variables
    if os.environ.get('OPENAI_API_KEY'):
        config.openai.api_key = os.environ['OPENAI_API_KEY']
    
    return config


# Global config instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or create global config instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def reload_config(config_path: Optional[str] = None) -> Config:
    """Reload configuration from file."""
    global _config
    _config = load_config(config_path)
    return _config
