"""Main CLI application entry point."""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from ..core import GmailManager
from ..services import ContactManager, AIService
from ..utils import settings, get_logger, setup_logging
from .commands import auth, cleanup, contacts, summarize, config

# Set up logging
setup_logging(
    level=settings.log_level,
    log_file=Path.home() / ".kit_gmail" / "kit_gmail.log" if settings.debug else None
)

logger = get_logger(__name__)
console = Console()

app = typer.Typer(
    name="kit-gmail",
    help="Kit Gmail - Knowledge Integration Tool for Gmail Management",
    rich_markup_mode="rich",
)

# Add subcommands
app.add_typer(auth.app, name="auth", help="Authentication management")
app.add_typer(cleanup.app, name="cleanup", help="Mailbox cleanup operations")
app.add_typer(contacts.app, name="contacts", help="Contact management")
app.add_typer(summarize.app, name="summarize", help="AI-powered email summarization")
app.add_typer(config.app, name="config", help="Configuration management")


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode"),
) -> None:
    """Kit Gmail - Knowledge Integration Tool for Gmail Management"""
    if debug:
        setup_logging(level="DEBUG", log_file=Path.home() / ".kit_gmail" / "debug.log")
    elif verbose:
        setup_logging(level="DEBUG")


@app.command()
def status() -> None:
    """Show application status and configuration."""
    console.print("\n[bold blue]Kit Gmail Status[/bold blue]\n")
    
    # Check authentication
    try:
        from ..core.gmail_auth import GmailAuth
        auth = GmailAuth()
        auth_status = "✅ Authenticated" if auth.is_authenticated else "❌ Not authenticated"
    except Exception as e:
        auth_status = f"❌ Authentication error: {str(e)}"
    
    # Check AI services
    ai_service = AIService()
    available_providers = list(ai_service.providers.keys())
    ai_status = f"✅ {len(available_providers)} providers available: {', '.join(available_providers)}" if available_providers else "❌ No AI providers configured"
    
    # Configuration status
    config_items = [
        ("Authentication", auth_status),
        ("AI Services", ai_status),
        ("Default AI Provider", settings.default_ai_service),
        ("Database", settings.database_url),
        ("Debug Mode", "✅ Enabled" if settings.debug else "❌ Disabled"),
        ("Log Level", settings.log_level),
    ]
    
    table = Table(title="Configuration Status", show_header=True)
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="green")
    
    for item, status in config_items:
        table.add_row(item, status)
    
    console.print(table)
    
    # Quick stats if authenticated
    if "✅" in auth_status:
        try:
            gmail_manager = GmailManager()
            stats = gmail_manager.get_mailbox_stats()
            
            if 'INBOX' in stats:
                inbox_stats = stats['INBOX']
                console.print(f"\n[bold green]Mailbox Overview[/bold green]")
                console.print(f"📧 Total messages: {inbox_stats.get('messages_total', 0):,}")
                console.print(f"📬 Unread messages: {inbox_stats.get('messages_unread', 0):,}")
                console.print(f"🧵 Total threads: {inbox_stats.get('threads_total', 0):,}")
        except Exception as e:
            console.print(f"\n[yellow]Could not retrieve mailbox stats: {str(e)}[/yellow]")


@app.command()
def quick_cleanup(
    days: int = typer.Option(30, "--days", "-d", help="Delete emails older than N days"),
    dry_run: bool = typer.Option(True, "--dry-run/--execute", help="Show what would be done without making changes"),
) -> None:
    """Perform quick mailbox cleanup."""
    
    console.print(f"\n[bold blue]Quick Cleanup[/bold blue] ({'DRY RUN' if dry_run else 'EXECUTING'})\n")
    
    if dry_run:
        console.print("[yellow]This is a dry run. No changes will be made.[/yellow]\n")
    
    try:
        gmail_manager = GmailManager()
        
        with console.status("[bold green]Analyzing mailbox..."):
            if not dry_run:
                stats = gmail_manager.cleanup_mailbox(days_old=days, delete_junk=True, archive_old=True)
            else:
                # For dry run, just get some sample data
                messages = gmail_manager.get_messages(query=f"older_than:{days}d", max_results=100)
                stats = {
                    "processed": len(messages),
                    "deleted": len(messages) // 4,  # Estimate
                    "archived": len(messages) // 2,  # Estimate
                    "organized": len(messages) - (len(messages) // 4),
                }
        
        # Show results
        result_table = Table(title="Cleanup Results")
        result_table.add_column("Action", style="cyan")
        result_table.add_column("Count", style="green")
        
        result_table.add_row("Emails Processed", str(stats["processed"]))
        result_table.add_row("Emails Deleted", str(stats["deleted"]))
        result_table.add_row("Emails Archived", str(stats["archived"]))
        result_table.add_row("Emails Organized", str(stats["organized"]))
        
        console.print(result_table)
        
        if dry_run:
            console.print(f"\n[yellow]To execute these changes, run:[/yellow]")
            console.print(f"[bold]kit-gmail quick-cleanup --days {days} --execute[/bold]")
    
    except Exception as e:
        console.print(f"\n[red]Error during cleanup: {str(e)}[/red]")
        logger.error(f"Quick cleanup failed: {e}")


@app.command()
def quick_summary(
    days: int = typer.Option(7, "--days", "-d", help="Summarize emails from the last N days"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="AI provider to use"),
) -> None:
    """Generate a quick email summary."""
    
    async def _generate_summary():
        console.print(f"\n[bold blue]Email Summary - Last {days} Days[/bold blue]\n")
        
        try:
            gmail_manager = GmailManager()
            
            with console.status("[bold green]Generating AI summary..."):
                summary = await gmail_manager.generate_email_summary(
                    days=days, 
                    summary_type="daily", 
                    provider_name=provider
                )
            
            console.print(Panel(
                summary, 
                title=f"📧 Email Summary ({days} days)",
                border_style="blue"
            ))
            
        except Exception as e:
            console.print(f"\n[red]Error generating summary: {str(e)}[/red]")
            logger.error(f"Quick summary failed: {e}")
    
    asyncio.run(_generate_summary())


@app.command()
def dashboard() -> None:
    """Show comprehensive Gmail dashboard."""
    
    console.print("\n[bold blue]📧 Kit Gmail Dashboard[/bold blue]\n")
    
    try:
        gmail_manager = GmailManager()
        contact_manager = ContactManager()
        
        # Load contacts if available
        try:
            contact_manager.load_contacts_from_db()
        except:
            pass  # No existing contacts database
        
        with console.status("[bold green]Loading dashboard data..."):
            # Get mailbox stats
            mailbox_stats = gmail_manager.get_mailbox_stats()
            
            # Get contact stats
            contact_stats = contact_manager.get_contact_stats()
        
        # Mailbox overview
        if 'INBOX' in mailbox_stats:
            inbox = mailbox_stats['INBOX']
            
            mailbox_table = Table(title="📬 Mailbox Overview", show_header=False)
            mailbox_table.add_column("Metric", style="cyan")
            mailbox_table.add_column("Value", style="green")
            
            mailbox_table.add_row("Total Messages", f"{inbox.get('messages_total', 0):,}")
            mailbox_table.add_row("Unread Messages", f"{inbox.get('messages_unread', 0):,}")
            mailbox_table.add_row("Total Threads", f"{inbox.get('threads_total', 0):,}")
            
            console.print(mailbox_table)
        
        # Contact overview
        if contact_stats.get('total_contacts', 0) > 0:
            contact_table = Table(title="👥 Contact Overview", show_header=False)
            contact_table.add_column("Metric", style="cyan")
            contact_table.add_column("Value", style="green")
            
            contact_table.add_row("Total Contacts", f"{contact_stats['total_contacts']:,}")
            contact_table.add_row("Frequent Contacts", f"{contact_stats['frequent_contacts']:,}")
            contact_table.add_row("Important Contacts", f"{contact_stats['important_contacts']:,}")
            contact_table.add_row("Spam Contacts", f"{contact_stats['spam_contacts']:,}")
            
            console.print(contact_table)
        
        # Labels overview
        important_labels = ['INBOX', 'SENT', 'DRAFT', 'SPAM', 'TRASH']
        label_table = Table(title="🏷️  Label Overview")
        label_table.add_column("Label", style="cyan")
        label_table.add_column("Messages", style="green")
        label_table.add_column("Unread", style="yellow")
        
        for label_name in important_labels:
            if label_name in mailbox_stats:
                label_data = mailbox_stats[label_name]
                label_table.add_row(
                    label_name,
                    f"{label_data.get('messages_total', 0):,}",
                    f"{label_data.get('messages_unread', 0):,}"
                )
        
        console.print(label_table)
        
        # Quick actions
        console.print("\n[bold yellow]Quick Actions:[/bold yellow]")
        console.print("• [cyan]kit-gmail quick-cleanup[/cyan] - Clean up old emails")
        console.print("• [cyan]kit-gmail quick-summary[/cyan] - Get AI summary") 
        console.print("• [cyan]kit-gmail contacts analyze[/cyan] - Analyze contacts")
        console.print("• [cyan]kit-gmail cleanup organize[/cyan] - Organize mailbox")
        
    except Exception as e:
        console.print(f"\n[red]Error loading dashboard: {str(e)}[/red]")
        logger.error(f"Dashboard failed: {e}")


if __name__ == "__main__":
    app()