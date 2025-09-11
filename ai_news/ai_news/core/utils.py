"""
Utility functions for AI News application.
"""
import os
from pathlib import Path


def load_env_file(env_file_path: str = None):
    """
    Load environment variables from .env file for development.
    
    Args:
        env_file_path: Path to .env file (optional)
    """
    if env_file_path is None:
        # Look for .env file in project root
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent.parent  # Navigate to project root
        env_file_path = project_root / '.env'
    
    env_file_path = Path(env_file_path)
    
    if env_file_path.exists():
        with open(env_file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())


def is_production() -> bool:
    """Check if running in production environment."""
    return os.getenv('ENVIRONMENT', 'development').lower() == 'production'


def is_development() -> bool:
    """Check if running in development environment."""
    return not is_production()


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent.parent