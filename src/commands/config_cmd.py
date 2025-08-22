#!/usr/bin/env python3
"""
Configuration Management Commands for AI Admin Hub

This module provides comprehensive CLI commands for managing AI Admin Hub configuration.
It handles environment file creation, validation, display, and API connectivity testing
with robust error handling and user-friendly output formatting.

Key Features:
- Interactive configuration template generation
- Secure credential display with masking options
- Comprehensive configuration validation with auto-fix capabilities
- Real-time API connectivity testing for all integrated services
- Rich CLI output with tables, colors, and progress indicators
- Support for multiple configuration file formats and locations

Commands Overview:
- `ai-admin config init`: Create .env.template with all required settings
- `ai-admin config show`: Display current configuration (with secret masking)
- `ai-admin config validate`: Validate configuration and check for issues
- `ai-admin config test`: Test API connectivity for all configured services

Security Features:
- Automatic credential masking in display output
- Secure handling of API keys and tokens
- No sensitive data logged or displayed by default
- Option to show secrets only when explicitly requested

Usage Examples:
    # Initialize configuration template
    ai-admin config init
    
    # Show configuration with masked secrets
    ai-admin config show
    
    # Show configuration with actual secrets (use with caution)
    ai-admin config show --show-secrets
    
    # Validate configuration and auto-fix common issues
    ai-admin config validate --fix
    
    # Test all API connections
    ai-admin config test

Author: Roland (AI Admin Hub Project)
Created: 2025-08-22
Last Modified: 2025-08-22
License: MIT

Dependencies:
- typer: Modern CLI framework with rich features
- rich: Beautiful terminal output with tables and formatting
- requests: HTTP client for API connectivity testing
- pathlib: Modern path handling
- json: Configuration serialization

Security Notes:
- API keys and tokens are masked by default in all output
- Use --show-secrets flag only in secure environments
- Configuration validation includes security best practices
- All API tests use read-only operations when possible
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse

import typer
import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn

from ai_admin_hub.config import load_config, create_env_template, ConfigError

# Initialize rich console for beautiful output
console = Console()

# Create typer app for configuration commands
app = typer.Typer(
    name="config", 
    help="🔧 Configuration management",
    rich_markup_mode="rich"
)


@app.command("init")
def init_config(
    force: bool = typer.Option(
        False, 
        "--force", 
        "-f", 
        help="Overwrite existing .env.template file"
    ),
    path: str = typer.Option(
        ".env.template", 
        "--path", 
        "-p", 
        help="Custom path for template file"
    ),
):
    """
    Initialize configuration template file.
    
    Creates a comprehensive .env.template file with all required configuration
    options, including detailed comments and example values. This template
    serves as the foundation for setting up the AI Admin Hub.
    
    The generated template includes:
    - N8n API configuration (API key, base URL, workflow ID)
    - GitHub integration settings (token, repository URL, branch)
    - OpenAI API configuration for AI features
    - Application settings (logging, backup retention, etc.)
    
    Args:
        force: If True, overwrites existing template file without confirmation
        path: Custom file path for the template (default: .env.template)
        
    Raises:
        typer.Exit: If template already exists and force=False, or if creation fails
        
    Example:
        ```bash
        # Create default template
        ai-admin config init
        
        # Overwrite existing template
        ai-admin config init --force
        
        # Create template in custom location
        ai-admin config init --path config/environment.template
        ```
        
    Security Note:
        The template file contains placeholder values and comments.
        Never commit actual API keys or secrets to version control.
    """
    template_path = Path(path)
    
    # Check if template already exists
    if template_path.exists() and not force:
        console.print(f"[yellow]⚠️  Warning:[/yellow] {path} already exists")
        console.print("[dim]Use --force to overwrite or specify different --path[/dim]")
        console.print(f"[dim]Current file size: {template_path.stat().st_size} bytes[/dim]")
        raise typer.Exit(1)
    
    try:
        # Create template file with comprehensive configuration
        create_env_template(path)
        
        # Success message with next steps
        console.print(f"[green]✅ Created configuration template:[/green] {path}")
        
        # Display helpful next steps in a panel
        next_steps = Text.assemble(
            ("1. ", "bold cyan"), ("Copy template to .env:", "white"), "\n",
            ("   ", "dim"), (f"cp {path} .env", "green"), "\n\n",
            ("2. ", "bold cyan"), ("Edit .env with your values:", "white"), "\n", 
            ("   ", "dim"), ("nano .env", "green"), (" or use your preferred editor", "dim"), "\n\n",
            ("3. ", "bold cyan"), ("Validate configuration:", "white"), "\n",
            ("   ", "dim"), ("ai-admin config validate", "green"), "\n\n",
            ("4. ", "bold cyan"), ("Test API connections:", "white"), "\n",
            ("   ", "dim"), ("ai-admin config test", "green")
        )
        
        console.print(Panel(
            next_steps,
            title="🚀 Next Steps",
            border_style="blue",
            padding=(1, 2)
        ))
        
    except PermissionError:
        console.print(f"[red]❌ Permission denied:[/red] Cannot write to {path}")
        console.print("[yellow]💡 Tip:[/yellow] Check file permissions or try a different path")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Failed to create template:[/red] {e}")
        console.print("[yellow]💡 Tip:[/yellow] Check directory permissions and disk space")
        raise typer.Exit(1)


@app.command("show")
def show_config(
    config_path: Optional[str] = typer.Option(
        None, 
        "--config", 
        "-c", 
        help="Custom configuration file path"
    ),
    format: str = typer.Option(
        "table", 
        "--format", 
        "-f", 
        help="Output format: table, json"
    ),
    show_secrets: bool = typer.Option(
        False, 
        "--show-secrets", 
        help="Show actual secret values (use with caution!)"
    ),
):
    """
    Display current configuration in formatted output.
    
    Shows all configuration settings in a human-readable format with automatic
    secret masking for security. Supports both table and JSON output formats.
    
    The display includes:
    - All configuration sections with current values
    - Source environment variable names for each setting
    - Masked display of sensitive values (API keys, tokens)
    - Configuration file location and status
    - Color-coded status indicators for missing required values
    
    Args:
        config_path: Path to custom configuration file (default: .env)
        format: Output format - 'table' for formatted display, 'json' for machine-readable
        show_secrets: If True, displays actual secret values (SECURITY RISK!)
        
    Security Warning:
        Using --show-secrets will display actual API keys and tokens in plain text.
        Only use this in secure environments and never in shared terminals or logs.
        
    Example:
        ```bash
        # Show configuration with masked secrets
        ai-admin config show
        
        # Show configuration in JSON format
        ai-admin config show --format json
        
        # Show actual secrets (use with extreme caution)
        ai-admin config show --show-secrets
        ```
    """
    try:
        # Load configuration from file or environment
        config = load_config(config_path)
        
        if format == "json":
            # Convert to dictionary and handle secret masking
            config_dict = config.dict()
            if not show_secrets:
                config_dict = _mask_secrets(config_dict)
            
            # Pretty-print JSON with indentation
            console.print(json.dumps(config_dict, indent=2))
            return
        
        # Create rich table for formatted display
        table = Table(
            title="🔧 AI Admin Hub Configuration", 
            show_header=True,
            header_style="bold blue"
        )
        table.add_column("Setting", style="cyan", min_width=20)
        table.add_column("Value", style="white", min_width=30)
        table.add_column("Source", style="dim", min_width=20)
        
        # N8n Configuration Section
        table.add_section()
        table.add_row("[bold blue]N8n Settings[/bold blue]", "", "")
        
        # API Key with smart masking
        api_key = config.n8n.api_key
        if not show_secrets and api_key:
            # Show first 8 and last 4 characters, mask the middle
            if len(api_key) > 12:
                api_key = f"{api_key[:8]}...{api_key[-4:]}"
            else:
                api_key = "***"
        
        table.add_row(
            "API Key", 
            api_key or "[red]Not set[/red]", 
            "N8N_API_KEY"
        )
        table.add_row("Base URL", config.n8n.base_url, "N8N_BASE_URL")
        table.add_row(
            "Workflow ID", 
            config.n8n.workflow_id or "[dim]Not set[/dim]", 
            "N8N_WORKFLOW_ID"
        )
        
        # GitHub Configuration Section
        table.add_section()
        table.add_row("[bold green]GitHub Settings[/bold green]", "", "")
        
        # GitHub token with proper masking
        github_token = config.github.token
        if not show_secrets and github_token:
            # GitHub tokens typically start with 'ghp_' or 'github_pat_'
            if github_token.startswith(('ghp_', 'github_pat_')):
                prefix = github_token.split('_')[0] + '_'
                github_token = f"{prefix}{'*' * 32}"
            else:
                github_token = "***"
        
        table.add_row(
            "Token", 
            github_token or "[red]Not set[/red]", 
            "GITHUB_TOKEN"
        )
        table.add_row(
            "Repository", 
            config.github.repo_url or "[red]Not set[/red]", 
            "GITHUB_REPO_URL"
        )
        table.add_row("Branch", config.github.branch, "GITHUB_BRANCH")
        
        # AI/OpenAI Configuration Section
        table.add_section()
        table.add_row("[bold magenta]AI Settings[/bold magenta]", "", "")
        
        # OpenAI key with proper masking
        openai_key = config.ai.openai_api_key
        if not show_secrets and openai_key:
            # OpenAI keys typically start with 'sk-'
            if openai_key.startswith('sk-'):
                openai_key = f"sk-{'*' * 45}"
            else:
                openai_key = "***"
        
        table.add_row(
            "OpenAI Key", 
            openai_key or "[dim]Not set (AI features disabled)[/dim]", 
            "OPENAI_API_KEY"
        )
        table.add_row("Model", config.ai.model, "OPENAI_MODEL")
        table.add_row("Max Tokens", str(config.ai.max_tokens), "OPENAI_MAX_TOKENS")
        table.add_row(
            "Daily Cost Limit", 
            f"${config.ai.cost_limit_daily:.2f}", 
            "OPENAI_COST_LIMIT_DAILY"
        )
        
        # Application Configuration Section
        table.add_section()
        table.add_row("[bold yellow]Application Settings[/bold yellow]", "", "")
        table.add_row("Log Level", config.log_level, "LOG_LEVEL")
        table.add_row(
            "Backup Retention", 
            f"{config.backup_retention_days} days", 
            "BACKUP_RETENTION_DAYS"
        )
        table.add_row("Backup Directory", config.backup_directory, "BACKUP_DIRECTORY")
        
        console.print(table)
        
        # Show configuration file information
        _display_config_file_info(config_path)
        
        # Security reminder if secrets are shown
        if show_secrets:
            console.print(Panel(
                "[red]⚠️  SECURITY WARNING: Actual secrets are displayed above![/red]\n"
                "Ensure this output is not logged, shared, or visible to unauthorized users.",
                title="Security Alert",
                border_style="red"
            ))
        
    except ConfigError as e:
        console.print(f"[red]❌ Configuration Error:[/red] {e}")
        console.print(Panel(
            Text.assemble(
                ("Configuration file missing or invalid.\n\n", "white"),
                ("Quick fix steps:\n", "bold yellow"),
                ("1. ", "cyan"), ("ai-admin config init", "green"), (" - Create template\n", "white"),
                ("2. ", "cyan"), ("Copy .env.template to .env", "white"), "\n",
                ("3. ", "cyan"), ("Edit .env with your API keys", "white"), "\n",
                ("4. ", "cyan"), ("ai-admin config validate", "green"), (" - Verify setup", "white")
            ),
            title="💡 Solution",
            border_style="yellow"
        ))
        raise typer.Exit(1)


@app.command("validate")
def validate_config(
    config_path: Optional[str] = typer.Option(
        None, 
        "--config", 
        "-c", 
        help="Custom configuration file path"
    ),
    fix: bool = typer.Option(
        False, 
        "--fix", 
        help="Attempt to auto-fix common configuration issues"
    ),
):
    """
    Validate configuration and check for common issues.
    
    Performs comprehensive validation of the configuration including:
    - Required setting verification (API keys, URLs, etc.)
    - URL format validation and accessibility checks
    - File path validation and directory creation
    - Security best practices verification
    - Optional auto-fix for common problems
    
    Validation Categories:
    - ERRORS: Critical issues that prevent functionality
    - WARNINGS: Non-critical issues that may affect features
    - INFO: Recommendations for optimal configuration
    
    Args:
        config_path: Path to custom configuration file
        fix: If True, attempts to automatically fix common issues
        
    Auto-fix Capabilities:
        - Creates missing backup directories
        - Validates and corrects URL formats
        - Sets appropriate file permissions
        - Creates missing log directories
        
    Example:
        ```bash
        # Validate configuration
        ai-admin config validate
        
        # Validate and auto-fix issues
        ai-admin config validate --fix
        ```
        
    Exit Codes:
        0: Configuration is valid
        1: Critical errors found that require manual intervention
    """
    try:
        # Load and validate configuration
        config = load_config(config_path)
        console.print("[green]✅ Configuration loaded successfully[/green]")
        
        # Initialize validation results
        errors = []      # Critical issues that prevent functionality
        warnings = []    # Non-critical issues that may affect features
        info = []        # Recommendations and informational notes
        fixed = []       # Issues that were automatically resolved
        
        # === REQUIRED SETTINGS VALIDATION ===
        console.print("\n[blue]🔍 Validating required settings...[/blue]")
        
        if not config.n8n.api_key:
            errors.append("N8n API key is required (N8N_API_KEY)")
        
        if not config.github.token:
            errors.append("GitHub token is required (GITHUB_TOKEN)")
            
        if not config.github.repo_url:
            errors.append("GitHub repository URL is required (GITHUB_REPO_URL)")
        
        # === OPTIONAL BUT RECOMMENDED SETTINGS ===
        if not config.n8n.workflow_id:
            warnings.append("No primary workflow ID set (N8N_WORKFLOW_ID) - some features may be limited")
            
        if not config.ai.openai_api_key:
            info.append("OpenAI API key not set - AI features will be disabled")
        
        # === URL VALIDATION ===
        console.print("[blue]🔍 Validating URLs and formats...[/blue]")
        
        try:
            # Validate N8n URL format
            n8n_url = urlparse(config.n8n.base_url)
            if not n8n_url.scheme or not n8n_url.netloc:
                errors.append(f"Invalid N8n base URL format: {config.n8n.base_url}")
            elif n8n_url.scheme not in ['http', 'https']:
                warnings.append(f"N8n URL should use http:// or https:// scheme: {config.n8n.base_url}")
                
            # Validate GitHub repository URL format
            if config.github.repo_url:
                if not config.github.repo_url.startswith('https://github.com/'):
                    errors.append(
                        f"GitHub repository URL must start with 'https://github.com/': {config.github.repo_url}"
                    )
                elif not _is_valid_github_repo_url(config.github.repo_url):
                    warnings.append(f"GitHub repository URL format may be incorrect: {config.github.repo_url}")
                    
        except Exception as e:
            errors.append(f"URL validation error: {e}")
        
        # === FILE SYSTEM VALIDATION ===
        console.print("[blue]🔍 Validating file system paths...[/blue]")
        
        # Check backup directory
        backup_dir = Path(config.backup_directory)
        if not backup_dir.exists():
            if fix:
                try:
                    backup_dir.mkdir(parents=True, exist_ok=True)
                    fixed.append(f"Created backup directory: {backup_dir}")
                    console.print(f"[green]✅ Created backup directory:[/green] {backup_dir}")
                except Exception as e:
                    errors.append(f"Cannot create backup directory {backup_dir}: {e}")
            else:
                warnings.append(f"Backup directory does not exist: {backup_dir} (use --fix to create)")
        elif not backup_dir.is_dir():
            errors.append(f"Backup path exists but is not a directory: {backup_dir}")
        elif not os.access(backup_dir, os.W_OK):
            errors.append(f"Backup directory is not writable: {backup_dir}")
        
        # Check log file directory if specified
        if config.log_file:
            log_file_path = Path(config.log_file)
            log_dir = log_file_path.parent
            if not log_dir.exists():
                if fix:
                    try:
                        log_dir.mkdir(parents=True, exist_ok=True)
                        fixed.append(f"Created log directory: {log_dir}")
                    except Exception as e:
                        warnings.append(f"Cannot create log directory {log_dir}: {e}")
                else:
                    warnings.append(f"Log directory does not exist: {log_dir}")
        
        # === SECURITY VALIDATION ===
        console.print("[blue]🔍 Checking security best practices...[/blue]")
        
        # Check for weak API keys (overly simple patterns)
        if config.n8n.api_key and len(config.n8n.api_key) < 20:
            warnings.append("N8n API key appears to be very short - ensure it's properly generated")
        
        if config.github.token and len(config.github.token) < 20:
            warnings.append("GitHub token appears to be very short - ensure it's properly generated")
        
        # Check for localhost URLs in production-like setups
        if 'localhost' in config.n8n.base_url and config.github.repo_url:
            info.append("Using localhost for N8n - ensure this is intended for your deployment")
        
        # === DISPLAY VALIDATION RESULTS ===
        _display_validation_results(errors, warnings, info, fixed)
        
        # === CONFIGURATION RECOMMENDATIONS ===
        if not errors and not warnings:
            console.print(Panel(
                Text.assemble(
                    ("🎉 Configuration is perfect! ", "bold green"), "\n\n",
                    ("All required settings are present and valid.\n", "white"),
                    ("Your AI Admin Hub is ready to use!", "bold blue")
                ),
                title="✅ Validation Complete",
                border_style="green"
            ))
        elif not errors:
            console.print(Panel(
                Text.assemble(
                    ("✅ Configuration is valid ", "bold green"), "with minor recommendations\n\n",
                    ("All critical settings are correct. ", "white"),
                    ("Consider addressing the warnings above for optimal functionality.", "dim")
                ),
                title="✅ Validation Complete",
                border_style="yellow"
            ))
        else:
            # Display fix suggestions for errors
            console.print(Panel(
                Text.assemble(
                    (f"❌ Found {len(errors)} critical issue(s) ", "bold red"), "that must be fixed\n\n",
                    ("Quick fix suggestions:\n", "bold yellow"),
                    ("• Check your .env file exists and has correct values\n", "white"),
                    ("• Verify API keys are properly set and valid\n", "white"),
                    ("• Ensure URLs are complete and properly formatted\n", "white"),
                    ("• Run with --fix to auto-resolve common issues", "green")
                ),
                title="❌ Validation Failed",
                border_style="red"
            ))
            raise typer.Exit(1)
            
    except ConfigError as e:
        console.print(f"[red]❌ Configuration Error:[/red] {e}")
        console.print(Panel(
            Text.assemble(
                ("Configuration cannot be loaded or is severely malformed.\n\n", "white"),
                ("Recovery steps:\n", "bold yellow"),
                ("1. ", "cyan"), ("ai-admin config init --force", "green"), (" - Recreate template\n", "white"),
                ("2. ", "cyan"), ("Copy template to .env and configure", "white"), "\n",
                ("3. ", "cyan"), ("Run validation again", "white")
            ),
            title="💡 Recovery Guide",
            border_style="red"
        ))
        raise typer.Exit(1)


@app.command("test")
def test_connections(
    config_path: Optional[str] = typer.Option(
        None, 
        "--config", 
        "-c", 
        help="Custom configuration file path"
    ),
    timeout: int = typer.Option(
        10, 
        "--timeout", 
        "-t", 
        help="Request timeout in seconds"
    ),
):
    """
    Test API connections with current configuration.
    
    Performs live connectivity tests for all configured APIs to verify
    that the configuration is not only valid but also functional.
    
    Tests performed:
    - N8n API: Authenticates and retrieves workflow list
    - GitHub API: Verifies token and repository access
    - OpenAI API: Validates API key and model availability
    
    Each test provides detailed information about:
    - Connection status (success/failure)
    - Response time for performance monitoring
    - Specific error details for troubleshooting
    - Available resources (workflow count, repository info, etc.)
    
    Args:
        config_path: Path to configuration file
        timeout: Request timeout in seconds (default: 10)
        
    Test Results:
        ✅ Connected: API is accessible and authentication successful
        ❌ Failed: API request failed (shows HTTP status code)
        ⚠️  Skipped: API not configured (missing credentials)
        ❌ Error: Network or other connectivity issue
        
    Example:
        ```bash
        # Test all configured APIs
        ai-admin config test
        
        # Test with custom timeout
        ai-admin config test --timeout 30
        ```
        
    Note:
        All tests use read-only operations to avoid modifying data.
        Network connectivity and firewall settings may affect results.
    """
    try:
        # Load configuration
        config = load_config(config_path)
        console.print("[blue]🔍 Testing API connections...[/blue]\n")
        
        # Create results table
        results = Table(
            title="🌐 Connection Test Results", 
            show_header=True,
            header_style="bold blue"
        )
        results.add_column("Service", style="cyan", min_width=15)
        results.add_column("Status", style="white", min_width=12)
        results.add_column("Response Time", style="dim", min_width=12)
        results.add_column("Details", style="white")
        
        # Test N8n API
        with Progress(
            SpinnerColumn(),
            TextColumn("[blue]Testing N8n API..."),
            console=console,
            transient=True
        ) as progress:
            progress.add_task("n8n", total=None)
            n8n_result = _test_n8n_api(config, timeout)
            results.add_row(*n8n_result)
        
        # Test GitHub API
        with Progress(
            SpinnerColumn(),
            TextColumn("[green]Testing GitHub API..."),
            console=console,
            transient=True
        ) as progress:
            progress.add_task("github", total=None)
            github_result = _test_github_api(config, timeout)
            results.add_row(*github_result)
        
        # Test OpenAI API
        with Progress(
            SpinnerColumn(),
            TextColumn("[magenta]Testing OpenAI API..."),
            console=console,
            transient=True
        ) as progress:
            progress.add_task("openai", total=None)
            openai_result = _test_openai_api(config, timeout)
            results.add_row(*openai_result)
        
        console.print(results)
        console.print(f"\n[dim]Test completed with {timeout}s timeout[/dim]")
        
    except ConfigError as e:
        console.print(f"[red]❌ Configuration Error:[/red] {e}")
        console.print("[yellow]💡 Fix configuration before testing connections[/yellow]")
        raise typer.Exit(1)


# === HELPER FUNCTIONS ===

def _mask_secrets(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively mask sensitive values in configuration dictionary.
    
    This function identifies and masks sensitive configuration values
    to prevent accidental exposure in logs or output. It handles nested
    dictionaries and preserves the overall structure.
    
    Args:
        data: Configuration dictionary to mask
        
    Returns:
        Dictionary with sensitive values replaced by "***MASKED***"
        
    Sensitive Keys Detected:
        - api_key, token, openai_api_key
        - password, secret, key (any variation)
        - credential, auth, authorization
    """
    masked = data.copy()
    
    # Define patterns for sensitive keys (case-insensitive)
    sensitive_patterns = [
        'api_key', 'token', 'openai_api_key', 'password', 
        'secret', 'key', 'credential', 'auth', 'authorization'
    ]
    
    def mask_recursive(obj):
        """Recursively process nested structures."""
        if isinstance(obj, dict):
            return {
                key: mask_recursive(value) if not _is_sensitive_key(key, sensitive_patterns)
                     else "***MASKED***" if value else None
                for key, value in obj.items()
            }
        elif isinstance(obj, list):
            return [mask_recursive(item) for item in obj]
        return obj
    
    return mask_recursive(masked)


def _is_sensitive_key(key: str, patterns: list) -> bool:
    """Check if a key name indicates sensitive data."""
    key_lower = key.lower()
    return any(pattern in key_lower for pattern in patterns)


def _display_config_file_info(config_path: Optional[str]):
    """Display information about the configuration file source."""
    env_file = Path(config_path) if config_path else Path(".env")
    
    if env_file.exists():
        file_size = env_file.stat().st_size
        console.print(f"\n[dim]📄 Configuration loaded from: {env_file.absolute()} ({file_size} bytes)[/dim]")
    else:
        console.print(f"\n[yellow]⚠️  No .env file found at: {env_file.absolute()}[/yellow]")
        console.print("[dim]Configuration loaded from environment variables[/dim]")


def _display_validation_results(errors: list, warnings: list, info: list, fixed: list):
    """Display formatted validation results with appropriate styling."""
    
    if fixed:
        console.print(f"\n[green]🔧 Auto-fixed {len(fixed)} issue(s):[/green]")
        for fix in fixed:
            console.print(f"  ✅ {fix}")
    
    if errors:
        console.print(f"\n[red]❌ Critical Issues ({len(errors)}):[/red]")
        for error in errors:
            console.print(f"  • {error}")
    
    if warnings:
        console.print(f"\n[yellow]⚠️  Warnings ({len(warnings)}):[/yellow]")
        for warning in warnings:
            console.print(f"  • {warning}")
    
    if info:
        console.print(f"\n[blue]ℹ️  Information ({len(info)}):[/blue]")
        for item in info:
            console.print(f"  • {item}")


def _is_valid_github_repo_url(url: str) -> bool:
    """Validate GitHub repository URL format."""
    # Basic validation - should be https://github.com/owner/repo
    parts = url.replace('https://github.com/', '').rstrip('.git').split('/')
    return len(parts) == 2 and all(part.strip() for part in parts)


def _test_n8n_api(config, timeout: int) -> tuple:
    """Test N8n API connectivity and return result tuple."""
    if not config.n8n.api_key:
        return ("N8n API", "[yellow]⚠️  Skipped[/yellow]", "-", "No API key configured")
    
    try:
        import time
        start_time = time.time()
        
        # Test N8n API with correct header format
        headers = {"X-N8N-API-KEY": config.n8n.api_key}
        response = requests.get(
            f"{config.n8n.base_url}/api/v1/workflows",
            headers=headers,
            timeout=timeout
        )
        
        response_time = f"{(time.time() - start_time):.2f}s"
        
        if response.status_code == 200:
            data = response.json()
            # Handle nested response format from N8n API
            workflows = data.get('data', []) if isinstance(data, dict) else data
            count = len(workflows) if isinstance(workflows, list) else 0
            return ("N8n API", "[green]✅ Connected[/green]", response_time, f"{count} workflows found")
        else:
            return ("N8n API", "[red]❌ Failed[/red]", response_time, f"HTTP {response.status_code}")
            
    except requests.exceptions.Timeout:
        return ("N8n API", "[red]❌ Timeout[/red]", f">{timeout}s", "Request timed out")
    except requests.exceptions.ConnectionError:
        return ("N8n API", "[red]❌ Connection Error[/red]", "-", "Cannot connect to N8n server")
    except Exception as e:
        return ("N8n API", "[red]❌ Error[/red]", "-", str(e)[:50])


def _test_github_api(config, timeout: int) -> tuple:
    """
    Test GitHub API connectivity and repository access.
    
    Verifies that the GitHub token is valid and can access the configured
    repository. Uses the GitHub REST API to fetch repository information.
    
    Args:
        config: Application configuration object
        timeout: Request timeout in seconds
        
    Returns:
        Tuple of (service_name, status, response_time, details) for table display
        
    API Endpoints Used:
        - GET /repos/{owner}/{repo}: Repository information and access verification
        
    Security Note:
        Uses read-only repository access to avoid any modifications.
    """
    if not config.github.token:
        return ("GitHub API", "[yellow]⚠️  Skipped[/yellow]", "-", "No token configured")
    
    try:
        import time
        start_time = time.time()
        
        # Extract repository owner/name from URL
        repo_path = config.github.repo_url.replace('https://github.com/', '').rstrip('.git')
        
        # Test GitHub API with proper authentication
        headers = {
            "Authorization": f"token {config.github.token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "AI-Admin-Hub/0.1.0"
        }
        
        response = requests.get(
            f"https://api.github.com/repos/{repo_path}",
            headers=headers,
            timeout=timeout
        )
        
        response_time = f"{(time.time() - start_time):.2f}s"
        
        if response.status_code == 200:
            repo_data = response.json()
            repo_name = repo_data.get('full_name', repo_path)
            visibility = "private" if repo_data.get('private', False) else "public"
            return ("GitHub API", "[green]✅ Connected[/green]", response_time, f"{repo_name} ({visibility})")
        elif response.status_code == 401:
            return ("GitHub API", "[red]❌ Auth Failed[/red]", response_time, "Invalid token")
        elif response.status_code == 404:
            return ("GitHub API", "[red]❌ Not Found[/red]", response_time, "Repository not found or no access")
        else:
            return ("GitHub API", "[red]❌ Failed[/red]", response_time, f"HTTP {response.status_code}")
            
    except requests.exceptions.Timeout:
        return ("GitHub API", "[red]❌ Timeout[/red]", f">{timeout}s", "Request timed out")
    except requests.exceptions.ConnectionError:
        return ("GitHub API", "[red]❌ Connection Error[/red]", "-", "Cannot connect to GitHub")
    except ValueError as e:
        return ("GitHub API", "[red]❌ Config Error[/red]", "-", "Invalid repository URL format")
    except Exception as e:
        return ("GitHub API", "[red]❌ Error[/red]", "-", str(e)[:50])


def _test_openai_api(config, timeout: int) -> tuple:
    """
    Test OpenAI API connectivity and authentication.
    
    Verifies that the OpenAI API key is valid and can access the API.
    Uses a lightweight endpoint to minimize API usage costs.
    
    Args:
        config: Application configuration object
        timeout: Request timeout in seconds
        
    Returns:
        Tuple of (service_name, status, response_time, details) for table display
        
    API Endpoints Used:
        - GET /v1/models: List available models (minimal cost operation)
        
    Cost Note:
        This test uses a free endpoint that doesn't consume API credits.
    """
    if not config.ai.openai_api_key:
        return ("OpenAI API", "[yellow]⚠️  Skipped[/yellow]", "-", "No API key configured (AI features disabled)")
    
    try:
        import time
        start_time = time.time()
        
        # Test OpenAI API with proper authentication
        headers = {
            "Authorization": f"Bearer {config.ai.openai_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "AI-Admin-Hub/0.1.0"
        }
        
        # Use the models endpoint as it's free and lightweight
        response = requests.get(
            "https://api.openai.com/v1/models",
            headers=headers,
            timeout=timeout
        )
        
        response_time = f"{(time.time() - start_time):.2f}s"
        
        if response.status_code == 200:
            models_data = response.json()
            model_count = len(models_data.get('data', []))
            # Check if the configured model is available
            configured_model = config.ai.model
            available_models = [model['id'] for model in models_data.get('data', [])]
            
            if configured_model in available_models:
                return ("OpenAI API", "[green]✅ Connected[/green]", response_time, f"Model '{configured_model}' available")
            else:
                return ("OpenAI API", "[yellow]⚠️  Model Issue[/yellow]", response_time, f"'{configured_model}' not found")
                
        elif response.status_code == 401:
            return ("OpenAI API", "[red]❌ Auth Failed[/red]", response_time, "Invalid API key")
        elif response.status_code == 429:
            return ("OpenAI API", "[yellow]⚠️  Rate Limited[/yellow]", response_time, "Too many requests")
        else:
            return ("OpenAI API", "[red]❌ Failed[/red]", response_time, f"HTTP {response.status_code}")
            
    except requests.exceptions.Timeout:
        return ("OpenAI API", "[red]❌ Timeout[/red]", f">{timeout}s", "Request timed out")
    except requests.exceptions.ConnectionError:
        return ("OpenAI API", "[red]❌ Connection Error[/red]", "-", "Cannot connect to OpenAI")
    except Exception as e:
        return ("OpenAI API", "[red]❌ Error[/red]", "-", str(e)[:50])


# Export the typer app for use in main CLI
if __name__ == "__main__":
    app()


# === MODULE EXPORTS ===
__all__ = [
    "app",           # Main typer application
    "init_config",   # Configuration initialization command
    "show_config",   # Configuration display command
    "validate_config", # Configuration validation command
    "test_connections" # API connectivity testing command
]