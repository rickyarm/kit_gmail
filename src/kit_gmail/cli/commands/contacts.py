"""Contact management CLI commands."""

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...core import GmailManager
from ...services import ContactManager
from ...utils import get_logger

logger = get_logger(__name__)
console = Console()

app = typer.Typer(help="Contact management and analysis")


@app.command()
def analyze(
    max_emails: int = typer.Option(500, "--max-emails", "-m", help="Maximum number of emails to analyze"),
    save: bool = typer.Option(True, "--save/--no-save", help="Save contact data to database"),
) -> None:
    """Analyze emails to extract and categorize contacts."""
    
    console.print(f"\n[bold blue]Contact Analysis[/bold blue]\n")
    
    try:
        gmail_manager = GmailManager()
        contact_manager = ContactManager()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            # Get recent emails
            task = progress.add_task("Fetching emails...", total=None)
            messages = gmail_manager.get_messages(query="", max_results=max_emails)
            
            progress.update(task, description=f"Processing {len(messages)} emails...")
            message_details = gmail_manager.batch_get_messages([m["id"] for m in messages])
            
            # Process emails for contacts
            processed_emails = []
            for message in message_details:
                processed_email = gmail_manager.processor.process_email(message)
                processed_emails.append(processed_email)
            
            progress.update(task, description="Analyzing contacts...")
            stats = contact_manager.analyze_emails(processed_emails)
        
        # Show results
        result_table = Table(title="Contact Analysis Results")
        result_table.add_column("Metric", style="cyan")
        result_table.add_column("Count", style="green")
        
        for key, value in stats.items():
            # Skip nested dictionaries for the main results table
            if isinstance(value, dict):
                continue
            result_table.add_row(key.replace("_", " ").title(), str(value))
        
        console.print(result_table)
        
        # Get contact stats
        contact_stats = contact_manager.get_contact_stats()
        
        if contact_stats.get('total_contacts', 0) > 0:
            console.print(f"\n[bold green]📊 Contact Statistics[/bold green]")
            console.print(f"• Total contacts: {contact_stats['total_contacts']:,}")
            console.print(f"• Frequent contacts: {contact_stats['frequent_contacts']:,}")
            console.print(f"• Important contacts: {contact_stats['important_contacts']:,}")
            console.print(f"• Spam contacts: {contact_stats['spam_contacts']:,}")
            
            # Show top domains
            top_domains = contact_stats.get('top_domains', {})
            if top_domains:
                console.print(f"\n[bold blue]🌐 Top Domains[/bold blue]")
                for domain, count in list(top_domains.items())[:5]:
                    console.print(f"• {domain}: {count:,} contacts")
        
        if save:
            console.print(f"\n[green]✅ Contact data saved to database[/green]")
    
    except Exception as e:
        console.print(f"\n[red]Error during contact analysis: {str(e)}[/red]")
        logger.error(f"Contact analysis failed: {e}")


@app.command()
def list(
    category: str = typer.Option("all", "--category", "-c", help="Category: all, frequent, important, spam"),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum number of contacts to show"),
) -> None:
    """List contacts by category."""
    
    console.print(f"\n[bold blue]Contact List - {category.title()}[/bold blue]\n")
    
    try:
        contact_manager = ContactManager()
        contact_manager.load_contacts_from_db()
        
        if category == "frequent":
            contacts = contact_manager.get_frequent_contacts(limit)
        elif category == "important":
            contacts = contact_manager.get_important_contacts()[:limit]
        elif category == "spam":
            contacts = contact_manager.get_spam_contacts()[:limit]
        else:
            contacts = list(contact_manager.contacts.values())[:limit]
        
        if not contacts:
            console.print(f"[yellow]No {category} contacts found.[/yellow]")
            console.print("Run 'kit-gmail contacts analyze' first to analyze your emails.")
            return
        
        # Create table
        table = Table()
        table.add_column("Email", style="cyan", width=30)
        table.add_column("Name", style="green", width=20)
        table.add_column("Emails", style="yellow", justify="right")
        table.add_column("Type", style="magenta")
        table.add_column("Score", style="blue", justify="right")
        
        for contact in contacts:
            contact_type = []
            if contact.is_frequent:
                contact_type.append("Frequent")
            if contact.is_important:
                contact_type.append("Important")
            if contact.is_spam:
                contact_type.append("Spam")
            if contact.is_automated:
                contact_type.append("Automated")
            
            table.add_row(
                contact.email[:30] + "..." if len(contact.email) > 30 else contact.email,
                contact.name[:20] + "..." if contact.name and len(contact.name) > 20 else contact.name or "—",
                str(contact.email_count),
                ", ".join(contact_type) or "Regular",
                f"{contact.confidence_score:.2f}"
            )
        
        console.print(table)
        
        if len(contacts) == limit:
            console.print(f"\n[yellow]Showing first {limit} contacts. Use --limit to see more.[/yellow]")
    
    except Exception as e:
        console.print(f"\n[red]Error listing contacts: {str(e)}[/red]")
        logger.error(f"Contact listing failed: {e}")


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query (email or name)"),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum number of results"),
) -> None:
    """Search contacts by email or name."""
    
    console.print(f"\n[bold blue]Contact Search: '{query}'[/bold blue]\n")
    
    try:
        contact_manager = ContactManager()
        contact_manager.load_contacts_from_db()
        
        matches = contact_manager.find_contacts(query)[:limit]
        
        if not matches:
            console.print(f"[yellow]No contacts found matching '{query}'.[/yellow]")
            return
        
        for contact in matches:
            # Create detailed contact info
            info_lines = [
                f"📧 {contact.email}",
                f"👤 {contact.name or 'No name'}",
                f"📊 {contact.email_count} emails ({contact.sent_count} sent, {contact.received_count} received)",
            ]
            
            if contact.first_seen:
                info_lines.append(f"📅 First seen: {contact.first_seen.strftime('%Y-%m-%d')}")
            if contact.last_seen:
                info_lines.append(f"🕐 Last seen: {contact.last_seen.strftime('%Y-%m-%d')}")
            
            # Add classifications
            classifications = []
            if contact.is_frequent:
                classifications.append("Frequent")
            if contact.is_important:
                classifications.append("Important")
            if contact.is_spam:
                classifications.append("Spam")
            if contact.is_automated:
                classifications.append("Automated")
            
            if classifications:
                info_lines.append(f"🏷️  {', '.join(classifications)}")
            
            if contact.domains:
                info_lines.append(f"🌐 Domains: {', '.join(list(contact.domains)[:3])}")
            
            console.print(Panel(
                "\n".join(info_lines),
                title=f"Contact Match (Score: {contact.confidence_score:.2f})",
                border_style="blue"
            ))
    
    except Exception as e:
        console.print(f"\n[red]Error searching contacts: {str(e)}[/red]")
        logger.error(f"Contact search failed: {e}")


@app.command()
def suggestions() -> None:
    """Get contact management suggestions."""
    
    console.print(f"\n[bold blue]Contact Management Suggestions[/bold blue]\n")
    
    try:
        contact_manager = ContactManager()
        contact_manager.load_contacts_from_db()
        
        if not contact_manager.contacts:
            console.print("[yellow]No contacts found. Run 'kit-gmail contacts analyze' first.[/yellow]")
            return
        
        suggestions = contact_manager.get_contact_suggestions()
        
        # Show suggestions in panels
        for suggestion_type, contacts in suggestions.items():
            if contacts:
                title = suggestion_type.replace("_", " ").title()
                contact_list = "\n".join(f"• {contact}" for contact in contacts[:10])
                
                if len(contacts) > 10:
                    contact_list += f"\n... and {len(contacts) - 10} more"
                
                console.print(Panel(
                    contact_list,
                    title=f"📋 {title} ({len(contacts)})",
                    border_style="yellow"
                ))
        
        # If no suggestions
        if not any(suggestions.values()):
            console.print("[green]✅ No contact management actions recommended at this time.[/green]")
    
    except Exception as e:
        console.print(f"\n[red]Error getting suggestions: {str(e)}[/red]")
        logger.error(f"Contact suggestions failed: {e}")


@app.command()
def stats() -> None:
    """Show detailed contact statistics."""
    
    console.print(f"\n[bold blue]📊 Contact Statistics[/bold blue]\n")
    
    try:
        contact_manager = ContactManager()
        contact_manager.load_contacts_from_db()
        
        stats = contact_manager.get_contact_stats()
        
        if stats.get('total_contacts', 0) == 0:
            console.print("[yellow]No contacts found. Run 'kit-gmail contacts analyze' first.[/yellow]")
            return
        
        # Overall stats
        overall_table = Table(title="📈 Overall Statistics", show_header=False)
        overall_table.add_column("Metric", style="cyan")
        overall_table.add_column("Value", style="green")
        
        overall_table.add_row("Total Contacts", f"{stats['total_contacts']:,}")
        overall_table.add_row("Total Emails", f"{stats['total_emails']:,}")
        overall_table.add_row("Avg Emails per Contact", str(stats['avg_emails_per_contact']))
        
        console.print(overall_table)
        
        # Classification breakdown
        class_table = Table(title="🏷️  Contact Classifications")
        class_table.add_column("Type", style="cyan")
        class_table.add_column("Count", style="green")
        class_table.add_column("Percentage", style="yellow")
        
        class_table.add_row("Frequent", str(stats['frequent_contacts']), stats['classification_coverage']['frequent'])
        class_table.add_row("Important", str(stats['important_contacts']), stats['classification_coverage']['important'])
        class_table.add_row("Spam", str(stats['spam_contacts']), stats['classification_coverage']['spam'])
        class_table.add_row("Automated", str(stats['automated_contacts']), f"{stats['automated_contacts']/stats['total_contacts']*100:.1f}%")
        
        console.print(class_table)
        
        # Top domains
        if stats.get('top_domains'):
            domain_table = Table(title="🌐 Top Email Domains")
            domain_table.add_column("Domain", style="cyan")
            domain_table.add_column("Contacts", style="green")
            
            for domain, count in list(stats['top_domains'].items())[:10]:
                domain_table.add_row(domain, str(count))
            
            console.print(domain_table)
    
    except Exception as e:
        console.print(f"\n[red]Error showing stats: {str(e)}[/red]")
        logger.error(f"Contact stats failed: {e}")


@app.command()
def export(
    format: str = typer.Option("csv", "--format", "-f", help="Export format: csv, json"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
) -> None:
    """Export contacts to file."""
    
    console.print(f"\n[bold blue]Export Contacts ({format.upper()})[/bold blue]\n")
    
    try:
        contact_manager = ContactManager()
        contact_manager.load_contacts_from_db()
        
        if not contact_manager.contacts:
            console.print("[yellow]No contacts found. Run 'kit-gmail contacts analyze' first.[/yellow]")
            return
        
        from pathlib import Path
        import json
        import csv
        
        output_path = output or f"contacts.{format}"
        
        if format.lower() == "json":
            # Export to JSON
            export_data = []
            for contact in contact_manager.contacts.values():
                export_data.append({
                    "email": contact.email,
                    "name": contact.name,
                    "first_seen": contact.first_seen.isoformat() if contact.first_seen else None,
                    "last_seen": contact.last_seen.isoformat() if contact.last_seen else None,
                    "email_count": contact.email_count,
                    "sent_count": contact.sent_count,
                    "received_count": contact.received_count,
                    "is_frequent": contact.is_frequent,
                    "is_important": contact.is_important,
                    "is_spam": contact.is_spam,
                    "is_automated": contact.is_automated,
                    "domains": list(contact.domains),
                    "confidence_score": contact.confidence_score,
                })
            
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2)
        
        elif format.lower() == "csv":
            # Export to CSV
            with open(output_path, 'w', newline='') as f:
                writer = csv.writer(f)
                
                # Header
                writer.writerow([
                    "Email", "Name", "First Seen", "Last Seen", "Email Count",
                    "Sent Count", "Received Count", "Is Frequent", "Is Important",
                    "Is Spam", "Is Automated", "Domains", "Confidence Score"
                ])
                
                # Data
                for contact in contact_manager.contacts.values():
                    writer.writerow([
                        contact.email,
                        contact.name or "",
                        contact.first_seen.isoformat() if contact.first_seen else "",
                        contact.last_seen.isoformat() if contact.last_seen else "",
                        contact.email_count,
                        contact.sent_count,
                        contact.received_count,
                        contact.is_frequent,
                        contact.is_important,
                        contact.is_spam,
                        contact.is_automated,
                        "; ".join(contact.domains),
                        contact.confidence_score,
                    ])
        
        else:
            console.print(f"[red]Unsupported format: {format}. Use 'csv' or 'json'.[/red]")
            return
        
        console.print(f"[bold green]✅ Exported {len(contact_manager.contacts)} contacts to {output_path}[/bold green]")
    
    except Exception as e:
        console.print(f"\n[red]Error exporting contacts: {str(e)}[/red]")
        logger.error(f"Contact export failed: {e}")