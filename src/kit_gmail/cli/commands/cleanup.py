"""Mailbox cleanup CLI commands."""

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

from ...core import GmailManager
from ...utils import get_logger

logger = get_logger(__name__)
console = Console()

app = typer.Typer(help="Mailbox cleanup operations")


@app.command()
def organize(
    dry_run: bool = typer.Option(True, "--dry-run/--execute", help="Show what would be done without making changes"),
    batch_size: int = typer.Option(100, "--batch-size", "-b", help="Number of emails to process at once"),
) -> None:
    """Organize emails by applying labels and categorization."""
    
    console.print(f"\n[bold blue]Email Organization[/bold blue] ({'DRY RUN' if dry_run else 'EXECUTING'})\n")
    
    if dry_run:
        console.print("[yellow]This is a dry run. No changes will be made.[/yellow]\n")
    
    try:
        gmail_manager = GmailManager()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            task = progress.add_task("Organizing emails...", total=None)
            
            # Get recent emails for organization
            messages = gmail_manager.get_messages(query="", max_results=batch_size)
            progress.update(task, description=f"Processing {len(messages)} emails...")
            
            message_details = gmail_manager.batch_get_messages([m["id"] for m in messages])
            
            organized_count = 0
            categories = {"receipts": 0, "mailing_lists": 0, "critical": 0, "junk": 0}
            
            for message in message_details:
                processed_email = gmail_manager.processor.process_email(message)
                
                if not dry_run:
                    gmail_manager.organize_message(message, processed_email)
                
                # Count categories
                if processed_email.is_receipt:
                    categories["receipts"] += 1
                if processed_email.is_mailing_list:
                    categories["mailing_lists"] += 1
                if processed_email.is_critical:
                    categories["critical"] += 1
                if processed_email.is_junk:
                    categories["junk"] += 1
                
                organized_count += 1
        
        # Show results
        result_table = Table(title="Organization Results")
        result_table.add_column("Category", style="cyan")
        result_table.add_column("Count", style="green")
        
        result_table.add_row("Total Processed", str(organized_count))
        result_table.add_row("Receipts", str(categories["receipts"]))
        result_table.add_row("Mailing Lists", str(categories["mailing_lists"]))
        result_table.add_row("Critical Emails", str(categories["critical"]))
        result_table.add_row("Junk Emails", str(categories["junk"]))
        
        console.print(result_table)
        
        if dry_run:
            console.print(f"\n[yellow]To apply these changes, run:[/yellow]")
            console.print(f"[bold]kit-gmail cleanup organize --execute --batch-size {batch_size}[/bold]")
    
    except Exception as e:
        console.print(f"\n[red]Error during organization: {str(e)}[/red]")
        logger.error(f"Email organization failed: {e}")


@app.command()
def delete_old(
    days: int = typer.Option(90, "--days", "-d", help="Delete emails older than N days"),
    confirm: bool = typer.Option(False, "--confirm", help="Skip confirmation prompt"),
    dry_run: bool = typer.Option(True, "--dry-run/--execute", help="Show what would be deleted without making changes"),
) -> None:
    """Delete old emails beyond specified days."""
    
    console.print(f"\n[bold red]Delete Old Emails[/bold red] ({'DRY RUN' if dry_run else 'EXECUTING'})\n")
    
    if not dry_run and not confirm:
        confirmed = typer.confirm(
            f"This will permanently delete emails older than {days} days. Continue?"
        )
        if not confirmed:
            console.print("Operation cancelled.")
            return
    
    if dry_run:
        console.print("[yellow]This is a dry run. No emails will be deleted.[/yellow]\n")
    
    try:
        gmail_manager = GmailManager()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            task = progress.add_task("Finding old emails...", total=None)
            
            # Get old emails
            query = f"older_than:{days}d"
            old_messages = gmail_manager.get_messages(query=query, max_results=1000)
            
            progress.update(task, description=f"Analyzing {len(old_messages)} old emails...")
            
            if not old_messages:
                console.print("[green]No old emails found to delete.[/green]")
                return
            
            message_details = gmail_manager.batch_get_messages([m["id"] for m in old_messages])
            
            delete_count = 0
            categories = {"junk": 0, "old_promotional": 0, "other": 0}
            
            for message in message_details:
                processed_email = gmail_manager.processor.process_email(message)
                
                # Only delete non-critical emails
                should_delete = (
                    processed_email.is_junk or 
                    processed_email.is_promotional or
                    (not processed_email.is_critical and not processed_email.is_receipt)
                )
                
                if should_delete:
                    if not dry_run:
                        gmail_manager.delete_message(message["id"])
                    
                    delete_count += 1
                    
                    if processed_email.is_junk:
                        categories["junk"] += 1
                    elif processed_email.is_promotional:
                        categories["old_promotional"] += 1
                    else:
                        categories["other"] += 1
        
        # Show results
        result_table = Table(title="Deletion Results")
        result_table.add_column("Category", style="cyan")
        result_table.add_column("Count", style="red")
        
        result_table.add_row("Total Emails Found", str(len(message_details)))
        result_table.add_row("Emails to Delete", str(delete_count))
        result_table.add_row("Junk Emails", str(categories["junk"]))
        result_table.add_row("Old Promotional", str(categories["old_promotional"]))
        result_table.add_row("Other Old Emails", str(categories["other"]))
        
        console.print(result_table)
        
        if dry_run and delete_count > 0:
            console.print(f"\n[yellow]To delete these emails, run:[/yellow]")
            console.print(f"[bold]kit-gmail cleanup delete-old --days {days} --execute[/bold]")
    
    except Exception as e:
        console.print(f"\n[red]Error during deletion: {str(e)}[/red]")
        logger.error(f"Email deletion failed: {e}")


@app.command()
def remove_duplicates(
    dry_run: bool = typer.Option(True, "--dry-run/--execute", help="Show what would be deleted without making changes"),
) -> None:
    """Find and remove duplicate emails."""
    
    console.print(f"\n[bold blue]Remove Duplicate Emails[/bold blue] ({'DRY RUN' if dry_run else 'EXECUTING'})\n")
    
    if dry_run:
        console.print("[yellow]This is a dry run. No emails will be deleted.[/yellow]\n")
    
    try:
        gmail_manager = GmailManager()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            task = progress.add_task("Finding duplicate emails...", total=None)
            
            # Get recent emails to check for duplicates
            messages = gmail_manager.get_messages(query="", max_results=500)
            message_details = gmail_manager.batch_get_messages([m["id"] for m in messages])
            
            progress.update(task, description="Analyzing for duplicates...")
            
            # Group by subject and sender
            email_groups = {}
            for message in message_details:
                processed_email = gmail_manager.processor.process_email(message)
                
                # Create a key for grouping
                key = (
                    processed_email.subject.strip().lower(),
                    processed_email.sender.lower(),
                    processed_email.date.date()  # Same day
                )
                
                if key not in email_groups:
                    email_groups[key] = []
                email_groups[key].append((message, processed_email))
            
            # Find duplicates
            duplicates = []
            for key, group in email_groups.items():
                if len(group) > 1:
                    # Keep the first one, mark others as duplicates
                    duplicates.extend(group[1:])
            
            delete_count = len(duplicates)
            
            if not dry_run and delete_count > 0:
                for message, _ in duplicates:
                    gmail_manager.delete_message(message["id"])
        
        # Show results
        console.print(f"[bold]Found {len(email_groups)} unique email groups[/bold]")
        console.print(f"[bold]Identified {delete_count} duplicate emails[/bold]")
        
        if delete_count > 0:
            if dry_run:
                console.print(f"\n[yellow]To delete duplicates, run:[/yellow]")
                console.print("[bold]kit-gmail cleanup remove-duplicates --execute[/bold]")
            else:
                console.print(f"\n[bold green]✅ Deleted {delete_count} duplicate emails[/bold green]")
        else:
            console.print("\n[green]No duplicate emails found.[/green]")
    
    except Exception as e:
        console.print(f"\n[red]Error during duplicate removal: {str(e)}[/red]")
        logger.error(f"Duplicate removal failed: {e}")


@app.command()
def archive_old(
    days: int = typer.Option(60, "--days", "-d", help="Archive emails older than N days"),
    keep_important: bool = typer.Option(True, "--keep-important/--archive-all", help="Keep important emails in inbox"),
    dry_run: bool = typer.Option(True, "--dry-run/--execute", help="Show what would be archived without making changes"),
) -> None:
    """Archive old emails to reduce inbox clutter."""
    
    console.print(f"\n[bold blue]Archive Old Emails[/bold blue] ({'DRY RUN' if dry_run else 'EXECUTING'})\n")
    
    if dry_run:
        console.print("[yellow]This is a dry run. No emails will be archived.[/yellow]\n")
    
    try:
        gmail_manager = GmailManager()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            task = progress.add_task("Finding emails to archive...", total=None)
            
            # Get old emails in inbox
            query = f"in:inbox older_than:{days}d"
            old_messages = gmail_manager.get_messages(query=query, max_results=1000)
            
            if not old_messages:
                console.print("[green]No old emails found in inbox to archive.[/green]")
                return
            
            progress.update(task, description=f"Processing {len(old_messages)} emails...")
            
            message_details = gmail_manager.batch_get_messages([m["id"] for m in old_messages])
            
            archive_count = 0
            kept_important = 0
            
            for message in message_details:
                processed_email = gmail_manager.processor.process_email(message)
                
                should_archive = True
                if keep_important and processed_email.is_critical:
                    should_archive = False
                    kept_important += 1
                
                if should_archive:
                    if not dry_run:
                        gmail_manager.archive_message(message["id"])
                    archive_count += 1
        
        # Show results
        result_table = Table(title="Archive Results")
        result_table.add_column("Category", style="cyan")
        result_table.add_column("Count", style="green")
        
        result_table.add_row("Total Old Emails", str(len(message_details)))
        result_table.add_row("Emails Archived", str(archive_count))
        if keep_important:
            result_table.add_row("Important Emails Kept", str(kept_important))
        
        console.print(result_table)
        
        if dry_run and archive_count > 0:
            console.print(f"\n[yellow]To archive these emails, run:[/yellow]")
            keep_flag = "--keep-important" if keep_important else "--archive-all"
            console.print(f"[bold]kit-gmail cleanup archive-old --days {days} {keep_flag} --execute[/bold]")
    
    except Exception as e:
        console.print(f"\n[red]Error during archiving: {str(e)}[/red]")
        logger.error(f"Email archiving failed: {e}")