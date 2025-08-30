"""Configuration management CLI commands."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ...utils import settings, SecureConfig, generate_secret_key
from ...utils.logger import get_logger

logger = get_logger(__name__)
console = Console()

app = typer.Typer(help="Configuration management")


@app.command()
def show() -> None:
    """Show current configuration (without sensitive values)."""
    
    console.print("\n[bold blue]📋 Kit Gmail Configuration[/bold blue]\n")
    
    config_table = Table(title="Configuration Settings")
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="green")
    config_table.add_column("Source", style="yellow")
    
    # Gmail API settings
    config_table.add_row(
        "Gmail Redirect URI",
        settings.gmail_redirect_uri,
        "Config"
    )
    
    # AI Service settings
    config_table.add_row(
        "Default AI Service",
        settings.default_ai_service,
        "Config"
    )
    
    # Check if API keys are set (without revealing them)
    secure_config = SecureConfig()
    api_keys = secure_config.list_secure_keys()
    
    for key_name in ["anthropic_api_key", "openai_api_key", "xai_api_key", "gmail_client_id", "gmail_client_secret"]:
        status = "✅ Set" if key_name in api_keys else "❌ Not set"
        source = "Keyring" if key_name in api_keys else "Not configured"
        
        config_table.add_row(
            key_name.replace("_", " ").title(),
            status,
            source
        )
    
    # Application settings
    config_table.add_row("Debug Mode", "✅ Enabled" if settings.debug else "❌ Disabled", "Config")
    config_table.add_row("Log Level", settings.log_level, "Config")
    config_table.add_row("Database URL", settings.database_url, "Config")
    config_table.add_row("Max Email Batch Size", str(settings.max_email_batch_size), "Config")
    config_table.add_row("Default Summary Days", str(settings.default_summary_days), "Config")
    
    console.print(config_table)
    
    # Show configuration file locations
    config_locations = [
        ("Environment file", ".env"),
        ("Config directory", str(Path.home() / ".kit_gmail")),
        ("Credentials", str(Path.home() / ".kit_gmail" / "credentials.json")),
        ("Token", str(Path.home() / ".kit_gmail" / "token.json")),
        ("Database", str(Path.home() / ".kit_gmail" / "kit_gmail.db")),
    ]
    
    console.print(f"\n[bold yellow]📁 Configuration Locations[/bold yellow]")
    for name, path in config_locations:
        exists = "✅" if Path(path).exists() else "❌"
        console.print(f"• {name}: {path} {exists}")


@app.command()
def set(
    key: str = typer.Argument(..., help="Configuration key to set"),
    value: str = typer.Argument(..., help="Value to set (will be stored securely if it's an API key)"),
) -> None:
    """Set a configuration value."""
    
    console.print(f"\n[bold blue]Setting Configuration[/bold blue]\n")
    
    # List of sensitive keys that should be stored securely
    sensitive_keys = {
        "anthropic_api_key", "openai_api_key", "xai_api_key",
        "gmail_client_id", "gmail_client_secret", "secret_key"
    }
    
    if key.lower() in sensitive_keys:
        # Store securely in keyring
        secure_config = SecureConfig()
        if secure_config.set_secure_value(key, value):
            console.print(f"[bold green]✅ Securely stored {key}[/bold green]")
        else:
            console.print(f"[bold red]❌ Failed to store {key}[/bold red]")
    else:
        # For non-sensitive settings, show a message about environment variables
        console.print(f"[yellow]To set {key}, add it to your .env file:[/yellow]")
        console.print(f"[cyan]{key.upper()}={value}[/cyan]")
        console.print("\n[yellow]Or set it as an environment variable.[/yellow]")


@app.command()
def get(
    key: str = typer.Argument(..., help="Configuration key to retrieve"),
    show_value: bool = typer.Option(False, "--show-value", help="Show the actual value (use carefully)")
) -> None:
    """Get a configuration value."""
    
    console.print(f"\n[bold blue]Configuration Value: {key}[/bold blue]\n")
    
    # Check secure storage first
    secure_config = SecureConfig()
    secure_value = secure_config.get_secure_value(key)
    
    if secure_value:
        if show_value:
            console.print(f"[green]{key}: {secure_value}[/green]")
        else:
            console.print(f"[green]{key}: {'*' * 8} (stored securely)[/green]")
        return
    
    # Check regular settings
    if hasattr(settings, key):
        value = getattr(settings, key)
        console.print(f"[green]{key}: {value}[/green]")
    else:
        console.print(f"[red]Configuration key '{key}' not found[/red]")
        
        # Show available keys
        available_keys = [attr for attr in dir(settings) if not attr.startswith('_')]
        console.print(f"\n[yellow]Available configuration keys:[/yellow]")
        for available_key in available_keys:
            console.print(f"• {available_key}")


@app.command()
def delete(
    key: str = typer.Argument(..., help="Configuration key to delete"),
    confirm: bool = typer.Option(False, "--confirm", help="Skip confirmation prompt")
) -> None:
    """Delete a configuration value from secure storage."""
    
    if not confirm:
        confirmed = typer.confirm(f"Delete configuration key '{key}'?")
        if not confirmed:
            console.print("Operation cancelled.")
            return
    
    console.print(f"\n[bold yellow]Deleting Configuration Key: {key}[/bold yellow]\n")
    
    secure_config = SecureConfig()
    if secure_config.delete_secure_value(key):
        console.print(f"[bold green]✅ Deleted {key} from secure storage[/bold green]")
    else:
        console.print(f"[bold red]❌ Failed to delete {key} (may not exist)[/bold red]")


@app.command()
def init() -> None:
    """Initialize configuration directory and files."""
    
    console.print("\n[bold blue]🚀 Initializing Kit Gmail Configuration[/bold blue]\n")
    
    config_dir = Path.home() / ".kit_gmail"
    env_file = Path.cwd() / ".env"
    
    try:
        # Create config directory
        config_dir.mkdir(parents=True, exist_ok=True)
        console.print(f"[green]✅ Created config directory: {config_dir}[/green]")
        
        # Create .env file if it doesn't exist
        if not env_file.exists():
            env_content = """# Kit Gmail Configuration
# Gmail API Configuration
GMAIL_CLIENT_ID=your_gmail_client_id_here
GMAIL_CLIENT_SECRET=your_gmail_client_secret_here
GMAIL_REDIRECT_URI=http://localhost:8080

# AI Service Configuration
# ANTHROPIC_API_KEY=your_anthropic_api_key_here
# OPENAI_API_KEY=your_openai_api_key_here
# XAI_API_KEY=your_xai_api_key_here

# Default AI Service (anthropic, openai, or xai)
DEFAULT_AI_SERVICE=anthropic

# Database Configuration
DATABASE_URL=sqlite:///kit_gmail.db

# Application Settings
DEBUG=false
LOG_LEVEL=INFO
MAX_EMAIL_BATCH_SIZE=100
DEFAULT_SUMMARY_DAYS=7

# Email Processing Settings
RECEIPT_KEYWORDS=receipt,invoice,order,purchase,payment
JUNK_KEYWORDS=unsubscribe,promotion,deal,offer,sale
CRITICAL_SENDERS=bank,insurance,government,tax
"""
            with open(env_file, 'w') as f:
                f.write(env_content)
            console.print(f"[green]✅ Created .env file: {env_file}[/green]")
        else:
            console.print(f"[yellow]📝 .env file already exists: {env_file}[/yellow]")
        
        # Generate secret key if not exists
        secure_config = SecureConfig()
        if not secure_config.get_secure_value("secret_key"):
            secret_key = generate_secret_key()
            secure_config.set_secure_value("secret_key", secret_key)
            console.print("[green]✅ Generated and stored secret key[/green]")
        
        console.print(f"\n[bold green]🎉 Configuration initialized successfully![/bold green]")
        console.print(f"\n[yellow]Next steps:[/yellow]")
        console.print("1. Edit .env file with your API keys")
        console.print("2. Set up Gmail API credentials: kit-gmail auth setup <credentials.json>")
        console.print("3. Configure AI service: kit-gmail config set anthropic_api_key <your-key>")
        console.print("4. Run: kit-gmail status to verify setup")
    
    except Exception as e:
        console.print(f"[red]❌ Failed to initialize configuration: {str(e)}[/red]")
        logger.error(f"Config initialization failed: {e}")


@app.command()
def reset() -> None:
    """Reset all configuration (WARNING: This will delete all stored data)."""
    
    console.print("\n[bold red]⚠️  CONFIGURATION RESET[/bold red]\n")
    console.print("[red]This will delete ALL configuration data including:[/red]")
    console.print("• API keys stored in keyring")
    console.print("• Gmail authentication tokens")
    console.print("• Contact database")
    console.print("• Configuration files")
    
    confirmed = typer.confirm("\nAre you sure you want to reset all configuration?")
    if not confirmed:
        console.print("Operation cancelled.")
        return
    
    double_confirm = typer.confirm("This action cannot be undone. Proceed with reset?")
    if not double_confirm:
        console.print("Operation cancelled.")
        return
    
    try:
        config_dir = Path.home() / ".kit_gmail"
        
        # Delete secure values
        secure_config = SecureConfig()
        secure_keys = secure_config.list_secure_keys()
        
        for key in secure_keys:
            secure_config.delete_secure_value(key)
            console.print(f"[yellow]🗑️  Deleted secure key: {key}[/yellow]")
        
        # Delete configuration directory
        if config_dir.exists():
            import shutil
            shutil.rmtree(config_dir)
            console.print(f"[yellow]🗑️  Deleted config directory: {config_dir}[/yellow]")
        
        console.print(f"\n[bold green]✅ Configuration reset complete![/bold green]")
        console.print("Run 'kit-gmail config init' to reinitialize.")
    
    except Exception as e:
        console.print(f"[red]❌ Failed to reset configuration: {str(e)}[/red]")
        logger.error(f"Config reset failed: {e}")


@app.command()
def backup(
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Backup file path")
) -> None:
    """Backup configuration (excluding sensitive data)."""
    
    console.print("\n[bold blue]💾 Configuration Backup[/bold blue]\n")
    
    try:
        import json
        from datetime import datetime
        
        output_path = output or f"kit_gmail_config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Collect non-sensitive configuration
        backup_data = {
            "backup_created": datetime.now().isoformat(),
            "version": "0.1.0",
            "settings": {
                "gmail_redirect_uri": settings.gmail_redirect_uri,
                "default_ai_service": settings.default_ai_service,
                "database_url": settings.database_url,
                "debug": settings.debug,
                "log_level": settings.log_level,
                "max_email_batch_size": settings.max_email_batch_size,
                "default_summary_days": settings.default_summary_days,
                "receipt_keywords": settings.receipt_keywords,
                "junk_keywords": settings.junk_keywords,
                "critical_senders": settings.critical_senders,
            },
            "api_keys_configured": {
                "anthropic": bool(settings.anthropic_api_key),
                "openai": bool(settings.openai_api_key),
                "xai": bool(settings.xai_api_key),
            },
            "note": "This backup does not include sensitive data like API keys."
        }
        
        with open(output_path, 'w') as f:
            json.dump(backup_data, f, indent=2)
        
        console.print(f"[bold green]✅ Configuration backed up to: {output_path}[/bold green]")
        console.print("\n[yellow]Note: Sensitive data (API keys) are not included in backup.[/yellow]")
    
    except Exception as e:
        console.print(f"[red]❌ Failed to backup configuration: {str(e)}[/red]")
        logger.error(f"Config backup failed: {e}")


@app.command()
def validate() -> None:
    """Validate current configuration."""
    
    console.print("\n[bold blue]✅ Configuration Validation[/bold blue]\n")
    
    issues = []
    warnings = []
    
    try:
        # Check API keys
        secure_config = SecureConfig()
        api_keys = secure_config.list_secure_keys()
        
        if not any(key.endswith("_api_key") for key in api_keys):
            issues.append("No AI service API keys configured")
        
        # Check Gmail credentials
        gmail_creds = Path.home() / ".kit_gmail" / "credentials.json"
        if not gmail_creds.exists():
            issues.append("Gmail API credentials not found")
        
        # Check database
        if settings.database_url.startswith("sqlite:"):
            db_path = settings.database_url.replace("sqlite:///", "")
            if not Path(db_path).exists():
                warnings.append(f"Database file does not exist: {db_path}")
        
        # Check log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if settings.log_level not in valid_log_levels:
            issues.append(f"Invalid log level: {settings.log_level}")
        
        # Show results
        if not issues and not warnings:
            console.print("[bold green]🎉 Configuration is valid![/bold green]")
        else:
            if issues:
                console.print("[bold red]❌ Configuration Issues:[/bold red]")
                for issue in issues:
                    console.print(f"  • {issue}")
            
            if warnings:
                console.print(f"\n[bold yellow]⚠️  Configuration Warnings:[/bold yellow]")
                for warning in warnings:
                    console.print(f"  • {warning}")
        
        # Show recommendations
        console.print(f"\n[bold blue]💡 Recommendations:[/bold blue]")
        console.print("• Keep API keys in secure storage using 'kit-gmail config set'")
        console.print("• Regularly backup your configuration (excluding sensitive data)")
        console.print("• Monitor log files for errors or warnings")
        console.print("• Update Gmail API credentials if they expire")
    
    except Exception as e:
        console.print(f"[red]❌ Validation failed: {str(e)}[/red]")
        logger.error(f"Config validation failed: {e}")