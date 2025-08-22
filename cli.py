# src/ai_admin_hub/cli.py
"""
AI Admin Hub - Main CLI Application

A modern, AI-powered admin hub for n8n workflows with intelligent diagnostics.
"""
import typer
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from ai_admin_hub.commands import status, backup, workflow, config_cmd
from ai_admin_hub.config import load_config, ConfigError

console = Console()
app = typer.Typer(
    name="ai-admin",
    help="🤖 AI Admin Hub - Intelligent automation management",
    rich_markup_mode="rich",
    no_args_is_help=True,
)

# Add command groups
app.add_typer(status.app, name="status", help="📊 System status and health checks")
app.add_typer(backup.app, name="backup", help="💾 Backup operations and management")
app.add_typer(workflow.app, name="workflow", help="⚙️ Workflow management operations")
app.add_typer(config_cmd.app, name="config", help="🔧 Configuration management")


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    config_path: Optional[str] = typer.Option(None, "--config", help="Custom config file path"),
):
    """
    🤖 AI Admin Hub - Intelligent automation management
    
    Modern Python framework for managing n8n workflows with AI-powered diagnostics,
    automated backups, and intelligent troubleshooting.
    """
    try:
        # Load configuration
        config = load_config(config_path)
        
        # Set global verbose mode
        if verbose:
            console.print("[dim]Verbose mode enabled[/dim]")
            
    except ConfigError as e:
        console.print(f"[red]Configuration Error:[/red] {e}")
        console.print("[yellow]Tip:[/yellow] Run [bold]ai-admin config init[/bold] to create a configuration template")
        raise typer.Exit(1)


@app.command()
def version():
    """Show version information"""
    console.print(
        Panel(
            Text.assemble(
                ("AI Admin Hub", "bold blue"),
                "\n",
                ("Version: ", "dim"),
                ("0.1.0", "green"),
                "\n",
                ("Python Framework for AI-powered automation management", "dim"),
            ),
            title="🤖 Version Info",
            border_style="blue",
        )
    )


@app.command()
def welcome():
    """Show welcome message and quick start guide"""
    welcome_text = Text.assemble(
        ("Welcome to AI Admin Hub! 🤖", "bold blue"),
        "\n\n",
        ("Quick Start:", "bold yellow"),
        "\n",
        ("1. ", "dim"), ("ai-admin config init", "green"), (" - Initialize configuration", "dim"),
        "\n",
        ("2. ", "dim"), ("ai-admin status system", "green"), (" - Check system health", "dim"),
        "\n",
        ("3. ", "dim"), ("ai-admin backup now", "green"), (" - Create a backup", "dim"),
        "\n\n",
        ("Need help? Run ", "dim"), ("ai-admin --help", "green"), (" for all commands", "dim"),
    )
    
    console.print(
        Panel(
            welcome_text,
            title="🚀 AI Admin Hub",
            border_style="green",
            padding=(1, 2),
        )
    )


if __name__ == "__main__":
    app()


# src/ai_admin_hub/__init__.py
"""AI Admin Hub - Intelligent automation management framework"""

__version__ = "0.1.0"
__author__ = "Roland"
__description__ = "AI-powered admin hub for n8n workflows with intelligent diagnostics"


# src/ai_admin_hub/config.py
"""Configuration management with Pydantic"""

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv


class ConfigError(Exception):
    """Configuration related errors"""
    pass


class N8nConfig(BaseModel):
    """N8n API configuration"""
    api_key: str = Field(..., description="N8n API key")
    base_url: str = Field(default="http://localhost:5678", description="N8n base URL")
    workflow_id: Optional[str] = Field(None, description="Primary workflow ID")
    
    @validator('base_url')
    def validate_base_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Base URL must start with http:// or https://')
        return v.rstrip('/')


class GitHubConfig(BaseModel):
    """GitHub API configuration"""
    token: str = Field(..., description="GitHub personal access token")
    repo_url: str = Field(..., description="GitHub repository URL")
    branch: str = Field(default="main", description="Default branch")
    
    @validator('repo_url')
    def validate_repo_url(cls, v):
        if not v.startswith('https://github.com/'):
            raise ValueError('Repository URL must be a valid GitHub URL')
        return v


class AIConfig(BaseModel):
    """AI/OpenAI configuration"""
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    model: str = Field(default="gpt-4", description="OpenAI model to use")
    max_tokens: int = Field(default=1000, description="Maximum tokens per request")
    cost_limit_daily: float = Field(default=10.0, description="Daily cost limit in USD")


class AppConfig(BaseSettings):
    """Main application configuration"""
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[str] = Field(None, description="Log file path")
    
    # Backup settings
    backup_retention_days: int = Field(default=30, description="Backup retention in days")
    backup_directory: str = Field(default="./backups", description="Backup directory")
    
    # API configurations
    n8n: N8nConfig
    github: GitHubConfig
    ai: AIConfig = Field(default_factory=AIConfig)
    
    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"
        case_sensitive = False


def load_config(config_path: Optional[str] = None) -> AppConfig:
    """Load configuration from environment and .env file"""
    
    # Load .env file if it exists
    env_path = Path(config_path) if config_path else Path(".env")
    if env_path.exists():
        load_dotenv(env_path)
    
    try:
        return AppConfig(
            n8n=N8nConfig(
                api_key=os.getenv("N8N_API_KEY", ""),
                base_url=os.getenv("N8N_BASE_URL", "http://localhost:5678"),
                workflow_id=os.getenv("N8N_WORKFLOW_ID"),
            ),
            github=GitHubConfig(
                token=os.getenv("GITHUB_TOKEN", ""),
                repo_url=os.getenv("GITHUB_REPO_URL", ""),
                branch=os.getenv("GITHUB_BRANCH", "main"),
            ),
            ai=AIConfig(
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                model=os.getenv("OPENAI_MODEL", "gpt-4"),
                max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "1000")),
                cost_limit_daily=float(os.getenv("OPENAI_COST_LIMIT_DAILY", "10.0")),
            ),
        )
    except Exception as e:
        raise ConfigError(f"Failed to load configuration: {e}")


def create_env_template(path: str = ".env.template") -> None:
    """Create environment template file"""
    
    template_content = """# AI Admin Hub Configuration Template
# Copy this file to .env and fill in your values

# N8n Configuration
N8N_API_KEY=your_n8n_api_key_here
N8N_BASE_URL=http://localhost:5678
N8N_WORKFLOW_ID=your_primary_workflow_id

# GitHub Configuration  
GITHUB_TOKEN=your_github_personal_access_token
GITHUB_REPO_URL=https://github.com/username/repository
GITHUB_BRANCH=main

# AI/OpenAI Configuration (Optional)
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=1000
OPENAI_COST_LIMIT_DAILY=10.0

# Application Settings
LOG_LEVEL=INFO
BACKUP_RETENTION_DAYS=30
BACKUP_DIRECTORY=./backups
"""
    
    with open(path, 'w') as f:
        f.write(template_content)


# src/ai_admin_hub/exceptions.py
"""Custom exceptions for AI Admin Hub"""


class AIAdminHubError(Exception):
    """Base exception for AI Admin Hub"""
    pass


class ConfigError(AIAdminHubError):
    """Configuration related errors"""
    pass


class APIError(AIAdminHubError):
    """API related errors"""
    pass


class N8nAPIError(APIError):
    """N8n API specific errors"""
    pass


class GitHubAPIError(APIError):
    """GitHub API specific errors"""
    pass


class WorkflowError(AIAdminHubError):
    """Workflow related errors"""
    pass


class BackupError(AIAdminHubError):
    """Backup operation errors"""
    pass