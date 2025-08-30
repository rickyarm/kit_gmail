"""Email summarization CLI commands."""

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...core import GmailManager
from ...services import AIService
from ...utils import get_logger

logger = get_logger(__name__)
console = Console()

app = typer.Typer(help="AI-powered email summarization")


@app.command()
def daily(
    days: int = typer.Option(1, "--days", "-d", help="Number of days to summarize"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="AI provider: anthropic, openai, xai"),
) -> None:
    """Generate a daily email summary."""
    
    async def _daily_summary():
        console.print(f"\n[bold blue]📧 Daily Email Summary - Last {days} Day(s)[/bold blue]\n")
        
        try:
            gmail_manager = GmailManager()
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                
                task = progress.add_task("Generating daily summary...", total=None)
                
                summary = await gmail_manager.generate_email_summary(
                    days=days,
                    summary_type="daily",
                    provider_name=provider
                )
            
            console.print(Panel(
                summary,
                title=f"📅 Daily Email Summary ({days} day{'s' if days > 1 else ''})",
                border_style="blue",
                width=100
            ))
            
        except Exception as e:
            console.print(f"\n[red]Error generating daily summary: {str(e)}[/red]")
            logger.error(f"Daily summary failed: {e}")
    
    asyncio.run(_daily_summary())


@app.command()
def weekly(
    weeks: int = typer.Option(1, "--weeks", "-w", help="Number of weeks to summarize"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="AI provider: anthropic, openai, xai"),
) -> None:
    """Generate a weekly email summary."""
    
    async def _weekly_summary():
        days = weeks * 7
        console.print(f"\n[bold blue]📧 Weekly Email Summary - Last {weeks} Week(s)[/bold blue]\n")
        
        try:
            gmail_manager = GmailManager()
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                
                task = progress.add_task("Generating weekly summary...", total=None)
                
                summary = await gmail_manager.generate_email_summary(
                    days=days,
                    summary_type="weekly",
                    provider_name=provider
                )
            
            console.print(Panel(
                summary,
                title=f"📅 Weekly Email Summary ({weeks} week{'s' if weeks > 1 else ''})",
                border_style="green",
                width=100
            ))
            
        except Exception as e:
            console.print(f"\n[red]Error generating weekly summary: {str(e)}[/red]")
            logger.error(f"Weekly summary failed: {e}")
    
    asyncio.run(_weekly_summary())


@app.command()
def monthly(
    months: int = typer.Option(1, "--months", "-m", help="Number of months to summarize"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="AI provider: anthropic, openai, xai"),
) -> None:
    """Generate a monthly email summary."""
    
    async def _monthly_summary():
        days = months * 30  # Approximate
        console.print(f"\n[bold blue]📧 Monthly Email Summary - Last {months} Month(s)[/bold blue]\n")
        
        try:
            gmail_manager = GmailManager()
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                
                task = progress.add_task("Generating monthly summary...", total=None)
                
                summary = await gmail_manager.generate_email_summary(
                    days=days,
                    summary_type="monthly",
                    provider_name=provider
                )
            
            console.print(Panel(
                summary,
                title=f"📅 Monthly Email Summary ({months} month{'s' if months > 1 else ''})",
                border_style="magenta",
                width=100
            ))
            
        except Exception as e:
            console.print(f"\n[red]Error generating monthly summary: {str(e)}[/red]")
            logger.error(f"Monthly summary failed: {e}")
    
    asyncio.run(_monthly_summary())


@app.command()
def custom(
    days: int = typer.Argument(..., help="Number of days to analyze"),
    summary_type: str = typer.Option("custom", "--type", "-t", help="Summary type description"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="AI provider: anthropic, openai, xai"),
    save: Optional[str] = typer.Option(None, "--save", "-s", help="Save summary to file"),
) -> None:
    """Generate a custom email summary for specific time period."""
    
    async def _custom_summary():
        console.print(f"\n[bold blue]📧 Custom Email Summary - Last {days} Days[/bold blue]\n")
        
        try:
            gmail_manager = GmailManager()
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                
                task = progress.add_task("Generating custom summary...", total=None)
                
                summary = await gmail_manager.generate_email_summary(
                    days=days,
                    summary_type=summary_type,
                    provider_name=provider
                )
            
            console.print(Panel(
                summary,
                title=f"📅 {summary_type.title()} Email Summary ({days} days)",
                border_style="cyan",
                width=100
            ))
            
            # Save to file if requested
            if save:
                from pathlib import Path
                from datetime import datetime
                
                output_path = Path(save)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(f"# {summary_type.title()} Email Summary ({days} days)\n")
                    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Provider: {provider or 'default'}\n\n")
                    f.write(summary)
                
                console.print(f"\n[bold green]✅ Summary saved to {output_path}[/bold green]")
            
        except Exception as e:
            console.print(f"\n[red]Error generating custom summary: {str(e)}[/red]")
            logger.error(f"Custom summary failed: {e}")
    
    asyncio.run(_custom_summary())


@app.command()
def insights(
    insight_type: str = typer.Option("patterns", "--type", "-t", help="Insight type: patterns, cleanup, security"),
    days: int = typer.Option(30, "--days", "-d", help="Number of days to analyze"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="AI provider: anthropic, openai, xai"),
) -> None:
    """Generate AI insights about email patterns and management."""
    
    async def _insights():
        console.print(f"\n[bold blue]🔍 Email Insights - {insight_type.title()}[/bold blue]\n")
        
        try:
            gmail_manager = GmailManager()
            ai_service = AIService()
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                
                task = progress.add_task("Analyzing email patterns...", total=None)
                
                # Get recent emails
                messages = gmail_manager.get_messages(query=f"newer_than:{days}d", max_results=200)
                message_details = gmail_manager.batch_get_messages([m["id"] for m in messages])
                
                # Process emails
                processed_emails = []
                for message in message_details:
                    processed_email = gmail_manager.processor.process_email(message)
                    processed_emails.append(processed_email)
                
                progress.update(task, description="Generating insights...")
                
                insights_data = await ai_service.get_email_insights(
                    processed_emails,
                    insight_type=insight_type,
                    provider_name=provider
                )
            
            insights_text = insights_data.get('insights', 'No insights generated')
            
            console.print(Panel(
                insights_text,
                title=f"🔍 {insight_type.title()} Insights ({insights_data.get('email_count', 0)} emails)",
                border_style="yellow",
                width=100
            ))
            
            if 'error' in insights_data:
                console.print(f"\n[yellow]Warning: {insights_data['error']}[/yellow]")
            
        except Exception as e:
            console.print(f"\n[red]Error generating insights: {str(e)}[/red]")
            logger.error(f"Insights generation failed: {e}")
    
    asyncio.run(_insights())


@app.command()
def analyze_batch(
    max_emails: int = typer.Option(50, "--max-emails", "-m", help="Maximum number of emails to analyze"),
    provider: Optional[str] = typer.Option(None, "--provider", "-p", help="AI provider: anthropic, openai, xai"),
    save: Optional[str] = typer.Option(None, "--save", "-s", help="Save analysis to JSON file"),
) -> None:
    """Analyze individual emails using AI for detailed insights."""
    
    async def _batch_analysis():
        console.print(f"\n[bold blue]🔍 Batch Email Analysis[/bold blue]\n")
        
        try:
            gmail_manager = GmailManager()
            ai_service = AIService()
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                
                task = progress.add_task("Fetching emails for analysis...", total=None)
                
                # Get recent emails
                messages = gmail_manager.get_messages(query="", max_results=max_emails)
                message_details = gmail_manager.batch_get_messages([m["id"] for m in messages])
                
                # Process emails
                processed_emails = []
                for message in message_details:
                    processed_email = gmail_manager.processor.process_email(message)
                    processed_emails.append(processed_email)
                
                progress.update(task, description=f"Analyzing {len(processed_emails)} emails...")
                
                # Analyze with AI
                analysis_results = await ai_service.analyze_batch_emails(
                    processed_emails,
                    provider_name=provider
                )
            
            # Show results summary
            successful_analyses = [r for r in analysis_results if 'error' not in r]
            failed_analyses = [r for r in analysis_results if 'error' in r]
            
            console.print(f"[bold green]✅ Successfully analyzed: {len(successful_analyses)} emails[/bold green]")
            if failed_analyses:
                console.print(f"[bold red]❌ Failed to analyze: {len(failed_analyses)} emails[/bold red]")
            
            # Show sample insights
            if successful_analyses:
                console.print(f"\n[bold blue]📊 Sample Insights[/bold blue]")
                
                # Count categories
                categories = {}
                sentiments = {}
                priorities = {}
                
                for analysis in successful_analyses[:10]:  # Show first 10
                    if 'category' in analysis:
                        cat = analysis['category']
                        categories[cat] = categories.get(cat, 0) + 1
                    
                    if 'sentiment' in analysis:
                        sent = analysis['sentiment']
                        sentiments[sent] = sentiments.get(sent, 0) + 1
                    
                    if 'priority' in analysis:
                        prio = analysis['priority']
                        priorities[prio] = priorities.get(prio, 0) + 1
                
                if categories:
                    console.print(f"📂 Categories: {dict(categories)}")
                if sentiments:
                    console.print(f"😊 Sentiments: {dict(sentiments)}")
                if priorities:
                    console.print(f"⚡ Priorities: {dict(priorities)}")
            
            # Save to file if requested
            if save:
                import json
                from pathlib import Path
                from datetime import datetime
                
                output_path = Path(save)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                save_data = {
                    "generated_at": datetime.now().isoformat(),
                    "provider": provider or "default",
                    "total_emails": len(processed_emails),
                    "successful_analyses": len(successful_analyses),
                    "failed_analyses": len(failed_analyses),
                    "results": analysis_results
                }
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, indent=2, ensure_ascii=False)
                
                console.print(f"\n[bold green]✅ Analysis saved to {output_path}[/bold green]")
            
        except Exception as e:
            console.print(f"\n[red]Error during batch analysis: {str(e)}[/red]")
            logger.error(f"Batch analysis failed: {e}")
    
    asyncio.run(_batch_analysis())


@app.command()
def providers() -> None:
    """List available AI providers and their status."""
    
    console.print(f"\n[bold blue]🤖 AI Providers Status[/bold blue]\n")
    
    try:
        ai_service = AIService()
        
        if not ai_service.providers:
            console.print("[red]❌ No AI providers configured![/red]")
            console.print("\n[yellow]To configure AI providers, set these environment variables:[/yellow]")
            console.print("• ANTHROPIC_API_KEY - for Claude AI")
            console.print("• OPENAI_API_KEY - for GPT models")
            console.print("• XAI_API_KEY - for Grok models")
            console.print("\nOr use 'kit-gmail config set' to configure them securely.")
            return
        
        from rich.table import Table
        
        table = Table(title="Available AI Providers")
        table.add_column("Provider", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Model Info", style="yellow")
        
        provider_info = {
            "anthropic": ("Claude (Sonnet/Haiku)", "Anthropic"),
            "openai": ("GPT-4o-mini", "OpenAI"),
            "xai": ("Grok-beta", "xAI")
        }
        
        for provider_name in ai_service.providers.keys():
            info = provider_info.get(provider_name, ("Unknown", "Unknown"))
            status = "✅ Available"
            
            table.add_row(
                provider_name.title(),
                status,
                info[0]
            )
        
        console.print(table)
        
        from ...utils import settings
        console.print(f"\n[bold]Default provider:[/bold] {settings.default_ai_service}")
        console.print("\n[yellow]Use --provider flag to specify a different provider for commands.[/yellow]")
    
    except Exception as e:
        console.print(f"\n[red]Error checking providers: {str(e)}[/red]")
        logger.error(f"Provider check failed: {e}")