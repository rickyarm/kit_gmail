"""Authentication management CLI commands."""

from pathlib import Path
import typer
from rich.console import Console
from rich import print as rprint

from ...core.gmail_auth import GmailAuth
from ...utils import get_logger

logger = get_logger(__name__)
console = Console()

app = typer.Typer(help="Gmail authentication management")


@app.command()
def setup(
    credentials_file: str = typer.Argument(..., help="Path to Gmail API credentials JSON file")
) -> None:
    """Set up Gmail API authentication."""
    
    console.print("\n[bold blue]Setting up Gmail Authentication[/bold blue]\n")
    
    try:
        auth = GmailAuth()
        
        # Copy credentials file
        console.print("📋 Copying credentials file...")
        auth.setup_credentials(credentials_file)
        
        # Run authentication flow
        console.print("🔐 Starting OAuth2 authentication flow...")
        console.print("[yellow]Your browser will open for authentication.[/yellow]")
        
        creds = auth.authenticate()
        
        if creds and creds.valid:
            console.print("\n[bold green]✅ Authentication successful![/bold green]")
            console.print("You can now use Kit Gmail to manage your mailbox.")
        else:
            console.print("\n[bold red]❌ Authentication failed![/bold red]")
            
    except FileNotFoundError as e:
        console.print(f"\n[red]Error: {e}[/red]")
        console.print("\n[yellow]How to get credentials:[/yellow]")
        console.print("1. Go to https://console.cloud.google.com/")
        console.print("2. Create a new project or select existing")
        console.print("3. Enable Gmail API")
        console.print("4. Create OAuth2 credentials")
        console.print("5. Download the JSON file")
        
    except Exception as e:
        console.print(f"\n[red]Setup failed: {str(e)}[/red]")
        logger.error(f"Authentication setup failed: {e}")


@app.command()
def status() -> None:
    """Check authentication status."""
    
    try:
        auth = GmailAuth()
        
        if auth.is_authenticated:
            console.print("\n[bold green]✅ Authenticated[/bold green]")
            console.print("Gmail API access is working correctly.")
            
            # Test API access
            try:
                service = auth.get_gmail_service()
                profile = service.users().getProfile(userId='me').execute()
                console.print(f"📧 Email: {profile.get('emailAddress', 'Unknown')}")
                console.print(f"📊 Total messages: {profile.get('messagesTotal', 0):,}")
                console.print(f"🧵 Total threads: {profile.get('threadsTotal', 0):,}")
            except Exception as e:
                console.print(f"[yellow]Warning: Could not fetch profile info: {e}[/yellow]")
                
        else:
            console.print("\n[bold red]❌ Not authenticated[/bold red]")
            console.print("Run 'kit-gmail auth setup <credentials-file>' to authenticate.")
            
    except Exception as e:
        console.print(f"\n[red]Error checking status: {str(e)}[/red]")
        logger.error(f"Auth status check failed: {e}")


@app.command()
def refresh() -> None:
    """Refresh authentication tokens."""
    
    console.print("\n[bold blue]Refreshing Authentication[/bold blue]\n")
    
    try:
        auth = GmailAuth()
        
        if not auth.is_authenticated:
            console.print("[red]Not currently authenticated. Run 'kit-gmail auth setup' first.[/red]")
            return
        
        console.print("🔄 Refreshing tokens...")
        creds = auth.authenticate()  # This will refresh if needed
        
        if creds and creds.valid:
            console.print("\n[bold green]✅ Authentication refreshed![/bold green]")
        else:
            console.print("\n[bold red]❌ Refresh failed![/bold red]")
            console.print("You may need to re-authenticate with 'kit-gmail auth setup'.")
            
    except Exception as e:
        console.print(f"\n[red]Refresh failed: {str(e)}[/red]")
        logger.error(f"Auth refresh failed: {e}")


@app.command()
def revoke() -> None:
    """Revoke authentication and delete stored credentials."""
    
    confirm = typer.confirm(
        "This will revoke access and delete all stored credentials. Continue?"
    )
    
    if not confirm:
        console.print("Operation cancelled.")
        return
    
    console.print("\n[bold yellow]Revoking Authentication[/bold yellow]\n")
    
    try:
        auth = GmailAuth()
        
        console.print("🗑️  Revoking credentials...")
        auth.revoke_credentials()
        
        console.print("\n[bold green]✅ Authentication revoked![/bold green]")
        console.print("All stored credentials have been deleted.")
        console.print("Run 'kit-gmail auth setup' to re-authenticate.")
        
    except Exception as e:
        console.print(f"\n[red]Revoke failed: {str(e)}[/red]")
        logger.error(f"Auth revoke failed: {e}")