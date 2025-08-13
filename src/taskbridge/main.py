"""Main CLI entry point for TaskBridge."""

import logging
from pathlib import Path
from typing import Optional

import typer

from .config import config as config_manager
from .database import db
from .linear_api import linear_api
from .sync import sync_engine
from .toggl_api import toggl_api

app = typer.Typer(
    name="taskbridge",
    help="TaskBridge - Sync Linear projects with Toggl time tracking",
    add_completion=False,
)


@app.command()
def config():
    """Interactive setup of API keys."""
    config_manager.setup_interactive()


@app.command("config-obsidian")
def config_obsidian():
    """Configure Obsidian vault settings."""
    typer.echo("Obsidian Vault Configuration")
    typer.echo("=" * 30)

    current_vault_path = config_manager.get_obsidian_vault_path()
    current_vault_name = config_manager.get_obsidian_vault_name()

    if current_vault_path:
        typer.echo(f"Current vault path: {current_vault_path}")
        typer.echo(f"Current vault name: {current_vault_name}")
        if not typer.confirm("Update Obsidian configuration?"):
            return

    vault_path = typer.prompt("Enter Obsidian vault path", default="/Users/iross/obsidian/obsidian")
    vault_name = typer.prompt("Enter Obsidian vault name", default="obsidian")

    try:
        config_manager.set_obsidian_config(vault_path, vault_name)
        typer.echo("✅ Obsidian configuration saved")
        typer.echo(f"   Vault path: {vault_path}")
        typer.echo(f"   Vault name: {vault_name}")
    except ValueError as e:
        typer.echo(f"❌ Error: {e}")
        raise typer.Exit(1)


@app.command("open-note")
def open_note():
    """Open the Obsidian note for the current running task."""
    if not config_manager.get_obsidian_vault_path():
        typer.echo("❌ Obsidian vault not configured. Run 'taskbridge config-obsidian' first.")
        raise typer.Exit(1)

    if not toggl_api:
        typer.echo("❌ Toggl API not configured. Run 'taskbridge config' first.")
        raise typer.Exit(1)

    try:
        # Get the current timer
        current_timer = toggl_api.get_current_timer()
        if not current_timer:
            typer.echo("❌ No timer currently running.")
            return

        # Find the project mapping for the current timer
        project_mapping = None
        if current_timer.pid:
            project_mapping = db.get_project_by_toggl_id(str(current_timer.pid))

        if not project_mapping:
            typer.echo("❌ Current timer has no project mapping.")
            typer.echo("   Run 'taskbridge sync' to create project mappings.")
            return

        project_name = project_mapping.linear_name
        task_title = current_timer.description

        # Sanitize the task title to match note filename
        safe_title = "".join(
            c for c in task_title if c.isalnum() or c in (' ', '-', '_')
        ).rstrip()
        note_filename = f"{safe_title}.md"

        # Check if the note exists, create if needed
        vault_path = config_manager.get_obsidian_vault_path()
        note_path = Path(vault_path) / "10 Projects" / project_name / note_filename

        if not note_path.exists():
            typer.echo("📝 Creating project directory and note...")
            try:
                created_note = config_manager.create_task_note(
                    project_name=project_name,
                    task_title=task_title,
                    status="in-progress"
                )
                typer.echo(f"✅ Created note: {created_note.name}")
            except Exception as e:
                typer.echo(f"❌ Failed to create note: {e}")
                return

        # Try to open the note
        if config_manager.open_obsidian_note(project_name, note_filename):
            typer.echo(f"📖 Opened note for: {task_title}")
            typer.echo(f"   Project: {project_name}")
        else:
            # Fallback: show the URL
            url = config_manager.generate_obsidian_url(project_name, note_filename)
            typer.echo("⚠️  Could not open note automatically")
            typer.echo(f"📖 Obsidian URL: {url}")

    except Exception as e:
        typer.echo(f"❌ Error opening note: {e}")
        raise typer.Exit(1)


@app.command()
def sync(
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be done without making changes"),
    preview_only: bool = typer.Option(False, "--preview", "-p", help="Show preview only without confirmation prompt")
):
    """Preview and sync projects between systems."""
    if not sync_engine:
        typer.echo("❌ APIs not configured. Run 'taskbridge config' first.")
        raise typer.Exit(1)

    if preview_only:
        sync_engine.preview_sync()
    else:
        sync_engine.execute_sync(dry_run=dry_run)


@app.command()
def search(query: str):
    """Search Linear issues."""
    if not linear_api:
        typer.echo("❌ Linear API not configured. Run 'taskbridge config' first.")
        raise typer.Exit(1)

    try:
        typer.echo(f"Searching Linear for: {query}")
        issues = linear_api.get_issues(query=query)

        if not issues:
            typer.echo("No issues found.")
            return

        # Get project information for name lookups
        projects = {project.id: project.name for project in linear_api.get_projects()}

        typer.echo(f"\nFound {len(issues)} issue(s):")
        typer.echo("-" * 50)

        for issue in issues:
            typer.echo(f"ID: {issue.id}")
            typer.echo(f"  Title: {issue.title}")
            if issue.description:
                typer.echo(f"  Description: {issue.description}")

            # Show project ID and name
            if issue.project_id:
                project_name = projects.get(issue.project_id, "Unknown")
                typer.echo(f"  Project: {project_name} (ID: {issue.project_id})")
            else:
                typer.echo("  Project: None")

            typer.echo(f"  Priority: {issue.priority}")
            if issue.estimate:
                typer.echo(f"  Estimate: {issue.estimate}")
            typer.echo()

    except Exception as e:
        typer.echo(f"❌ Error searching issues: {e}")
        raise typer.Exit(1)


@app.command()
def start(
    issue_id: Optional[str] = None,
    debug: bool = typer.Option(False, "--debug", "-d", help="Enable debug logging"),
    note: bool = typer.Option(False, "--note", "-n", help="Create/open Obsidian note")
):
    """Start Toggl timer for a Linear issue."""
    if debug:
        logging.basicConfig(level=logging.DEBUG)

    if not linear_api or not toggl_api:
        typer.echo("❌ APIs not configured. Run 'taskbridge config' first.")
        raise typer.Exit(1)

    try:
        # If no issue ID provided, show interactive search
        if not issue_id:
            typer.echo("Interactive issue search:")
            search_query = typer.prompt("Enter search term (or press Enter for recent active issues)", default="")

            if search_query.strip():
                typer.echo(f"Searching for: {search_query}")
                issues = linear_api.get_issues(query=search_query, limit=10)
            else:
                typer.echo("Fetching recent active issues...")
                issues = linear_api.get_recent_issues(limit=10)

            if not issues:
                typer.echo("No issues found.")
                return

            # Get project information for name lookups
            projects = {project.id: project.name for project in linear_api.get_projects()}

            # Show issues for selection with more details
            typer.echo(f"\nFound {len(issues)} issue(s):")
            typer.echo("-" * 60)
            for i, issue in enumerate(issues, 1):
                project_info = ""
                if issue.project_id:
                    project_name = projects.get(issue.project_id, "Unknown")
                    # Truncate long project names for display
                    if len(project_name) > 25:
                        project_name = project_name[:22] + "..."
                    project_info = f" [Project: {project_name}]"

                # Truncate long titles
                title = issue.title
                if len(title) > 45:  # Reduced to make room for project name
                    title = title[:42] + "..."

                typer.echo(f"{i:2d}. {title}{project_info}")

                # Show a bit of context
                if issue.priority and issue.priority > 0:
                    priority_labels = {1: "Low", 2: "Medium", 3: "High", 4: "Urgent"}
                    priority_str = priority_labels.get(issue.priority, f"P{issue.priority}")
                    typer.echo(f"     Priority: {priority_str}")

            typer.echo("-" * 60)

            try:
                choice = typer.prompt("Select issue number (or 0 to cancel)", type=int)
                if choice == 0:
                    typer.echo("Cancelled.")
                    return
                if choice < 1 or choice > len(issues):
                    typer.echo("Invalid selection.")
                    return
                selected_issue = issues[choice - 1]
            except (ValueError, typer.Abort):
                typer.echo("Cancelled.")
                return
        else:
            # Find the specific issue
            typer.echo(f"Looking up issue: {issue_id}")
            # For now, we'll search by the issue ID - this could be improved
            issues = linear_api.get_issues(query=issue_id)
            selected_issue = None
            for issue in issues:
                if issue.id == issue_id:
                    selected_issue = issue
                    break

            if not selected_issue:
                typer.echo(f"❌ Issue {issue_id} not found.")
                return

        # Now we have selected_issue, start the timer
        _start_timer_for_issue(selected_issue, create_note=note)

    except Exception as e:
        typer.echo(f"❌ Error starting timer: {e}")
        raise typer.Exit(1)


def _start_timer_for_issue(issue, create_note: bool = False):
    """Helper function to start a Toggl timer for a Linear issue."""
    typer.echo(f"Starting timer for: {issue.title}")

    # Check if there's already a running timer
    current_timer = toggl_api.get_current_timer()
    if current_timer:
        typer.echo("⏹️  Stopping current timer...")
        stopped_timer = toggl_api.stop_timer()
        if stopped_timer:
            typer.echo(f"   Stopped: {stopped_timer.description}")

    # Find the project mapping if the issue belongs to a project
    toggl_project_id = None
    project_name = None
    client_name = ""

    if issue.project_id:
        typer.echo(f"🔍 Looking for project mapping for Linear project: {issue.project_id}")
        project_mapping = db.get_project_by_linear_id(issue.project_id)
        if project_mapping:
            toggl_project_id = int(project_mapping.toggl_project_id)
            project_name = project_mapping.linear_name
            typer.echo(f"📁 Using mapped Toggl project: {project_name} (ID: {toggl_project_id})")

            # Try to extract client name from project labels or name
            if hasattr(issue, 'labels') and issue.labels:
                client_labels = [label for label in issue.labels if label.startswith('#client/')]
                if client_labels:
                    client_name = client_labels[0].replace('#client/', '')
        else:
            typer.echo(f"⚠️  No project mapping found for Linear project {issue.project_id}")
            typer.echo("   Timer will be created without a project.")
            typer.echo("   Run 'taskbridge sync' to create project mappings.")
    else:
        typer.echo("📝 Issue has no project assignment")

    # Handle Obsidian note creation and opening if requested and configured
    if create_note and config_manager.get_obsidian_vault_path() and project_name:
        typer.echo("📝 Creating Obsidian note...")
        try:
            note_path = config_manager.create_task_note(
                project_name=project_name,
                task_title=issue.title,
                client=client_name,
                status="in-progress",
                tags=getattr(issue, 'labels', [])
            )
            typer.echo(f"   Created note: {note_path.name}")

            # Try to open the note in Obsidian
            if config_manager.open_obsidian_note(project_name, note_path.name):
                typer.echo("   📖 Opened note in Obsidian")
            else:
                # Fallback: show the URL
                url = config_manager.generate_obsidian_url(project_name, note_path.name)
                typer.echo(f"   📖 Obsidian URL: {url}")
        except Exception as e:
            typer.echo(f"   ⚠️  Failed to create/open Obsidian note: {e}")

    # Create the timer description (clean format without IDs)
    description = issue.title

    # Start the timer
    typer.echo("⏱️  Starting Toggl timer...")
    started_timer = toggl_api.start_timer(
        project_id=toggl_project_id,
        description=description
    )

    if started_timer:
        typer.echo(f"✅ Timer started: {started_timer.description}")
        if toggl_project_id:
            typer.echo(f"   Project: {toggl_project_id}")
        typer.echo(f"   Started at: {started_timer.start}")
    else:
        typer.echo("❌ Failed to start timer")


@app.command()
def status():
    """Show current running timer."""
    if not toggl_api:
        typer.echo("❌ Toggl API not configured. Run 'taskbridge config' first.")
        raise typer.Exit(1)

    try:
        current_timer = toggl_api.get_current_timer()

        if not current_timer:
            typer.echo("No timer currently running.")
            return

        typer.echo("Current Timer:")
        typer.echo("-" * 20)
        typer.echo(f"Description: {current_timer.description}")
        typer.echo(f"Project ID: {current_timer.pid}")
        typer.echo(f"Started: {current_timer.start}")

        if current_timer.duration < 0:
            # For running timers, calculate elapsed time from start time
            from datetime import datetime, timezone

            import dateutil.parser

            try:
                # Parse the start time (should be in ISO format with timezone)
                start_time = dateutil.parser.parse(current_timer.start)

                # Convert to UTC if not already
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=timezone.utc)
                else:
                    start_time = start_time.astimezone(timezone.utc)

                # Get current UTC time
                now_utc = datetime.now(timezone.utc)

                # Calculate elapsed time
                elapsed_delta = now_utc - start_time
                elapsed_seconds = int(elapsed_delta.total_seconds())

                hours = elapsed_seconds // 3600
                minutes = (elapsed_seconds % 3600) // 60
                seconds = elapsed_seconds % 60
                typer.echo(f"Elapsed: {hours:02d}:{minutes:02d}:{seconds:02d}")
            except Exception as e:
                # Fallback to the old method if parsing fails
                typer.echo(f"Elapsed: [Error calculating time: {e}]")

    except Exception as e:
        typer.echo(f"❌ Error getting timer status: {e}")
        raise typer.Exit(1)


@app.command()
def stop():
    """Stop current timer."""
    if not toggl_api:
        typer.echo("❌ Toggl API not configured. Run 'taskbridge config' first.")
        raise typer.Exit(1)

    try:
        stopped_timer = toggl_api.stop_timer()

        if not stopped_timer:
            typer.echo("No timer was running.")
        else:
            typer.echo(f"✅ Stopped timer: {stopped_timer.description}")

    except Exception as e:
        typer.echo(f"❌ Error stopping timer: {e}")
        raise typer.Exit(1)


@app.command("list-projects")
def list_projects():
    """Show current project mappings."""
    projects = db.get_all_projects()

    if not projects:
        typer.echo("No project mappings found.")
        typer.echo("Run 'taskbridge sync' to create mappings.")
        return

    # Pre-fetch Toggl data for efficiency
    toggl_clients = {}
    toggl_projects = {}

    if toggl_api:
        try:
            # Get all clients
            for client in toggl_api.get_clients():
                toggl_clients[client.id] = client

            # Get all projects
            for tp in toggl_api.get_projects():
                toggl_projects[tp.id] = tp
        except Exception as e:
            typer.echo(f"⚠️ Warning: Could not fetch Toggl data: {e}")

    typer.echo("Project Mappings:")
    typer.echo("=" * 80)

    for project in projects:
        typer.echo(f"ID: {project.id}")
        typer.echo(f"  📝 Linear: {project.linear_name}")
        typer.echo(f"      ID: {project.linear_id}")

        # Show Toggl client and project names
        toggl_client_name = "Unknown"
        toggl_project_name = "Unknown"
        project_status = "❓ Status Unknown"

        if toggl_api:
            try:
                # Get client name
                client_id = int(project.toggl_client_id)
                if client_id in toggl_clients:
                    toggl_client_name = toggl_clients[client_id].name

                # Get project name and status
                project_id = int(project.toggl_project_id)
                if project_id in toggl_projects:
                    toggl_project = toggl_projects[project_id]
                    toggl_project_name = toggl_project.name

                    if not toggl_project.active:
                        project_status = "⚠️  ARCHIVED"
                    else:
                        project_status = "✅ Active"
                else:
                    project_status = "❌ NOT FOUND"

            except Exception as e:
                project_status = f"❓ Error: {e}"

        typer.echo(f"  🎯 Toggl: {toggl_client_name} → {toggl_project_name}")
        typer.echo(f"      Client ID: {project.toggl_client_id} | Project ID: {project.toggl_project_id}")
        typer.echo(f"      Status: {project_status}")
        typer.echo(f"  📅 Created: {project.created_at}")
        typer.echo("-" * 80)


@app.command("list-linear-projects")
def list_linear_projects():
    """Show all Linear projects with their labels."""
    if not linear_api:
        typer.echo("❌ Linear API not configured. Run 'taskbridge config' first.")
        raise typer.Exit(1)

    try:
        typer.echo("Fetching Linear projects...")
        projects = linear_api.get_projects()

        if not projects:
            typer.echo("No Linear projects found.")
            return

        typer.echo(f"\nFound {len(projects)} Linear project(s):")
        typer.echo("=" * 60)

        for project in projects:
            typer.echo(f"Project: {project.name}")
            typer.echo(f"  ID: {project.id}")
            if project.description:
                typer.echo(f"  Description: {project.description}")
            typer.echo(f"  State: {project.state}")
            typer.echo(f"  Progress: {project.progress:.1%}")
            if project.labels:
                typer.echo(f"  Labels: {', '.join(project.labels)}")
                # Highlight client labels
                client_labels = [label for label in project.labels if label.startswith('#client/')]
                if client_labels:
                    typer.echo(f"  Client Labels: {', '.join(client_labels)} ✓")
            else:
                typer.echo("  Labels: None")
            typer.echo(f"  URL: {project.url}")
            typer.echo()

    except Exception as e:
        typer.echo(f"❌ Error fetching Linear projects: {e}")
        raise typer.Exit(1)


@app.command("list-issues")
def list_issues(
    project_id: Optional[str] = typer.Option(None, "--project", "-p", help="Filter by project ID"),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum number of issues to show")
):
    """Show Linear issues (optionally filtered by project)."""
    if not linear_api:
        typer.echo("❌ Linear API not configured. Run 'taskbridge config' first.")
        raise typer.Exit(1)

    try:
        if project_id:
            typer.echo(f"Fetching Linear issues for project {project_id}...")
        else:
            typer.echo(f"Fetching Linear issues (limit: {limit})...")

        issues = linear_api.get_issues(project_id=project_id)

        # Limit results if needed
        if len(issues) > limit:
            issues = issues[:limit]
            typer.echo(f"Showing first {limit} of {len(issues)} issues")

        if not issues:
            typer.echo("No Linear issues found.")
            return

        typer.echo(f"\nFound {len(issues)} issue(s):")
        typer.echo("=" * 60)

        for issue in issues:
            typer.echo(f"Issue: {issue.title}")
            typer.echo(f"  ID: {issue.id}")
            if issue.description:
                # Truncate long descriptions
                desc = issue.description[:100] + "..." if len(issue.description) > 100 else issue.description
                typer.echo(f"  Description: {desc}")
            if issue.project_id:
                typer.echo(f"  Project ID: {issue.project_id}")
            typer.echo(f"  Priority: {issue.priority}")
            if issue.estimate:
                typer.echo(f"  Estimate: {issue.estimate}")
            if issue.labels:
                typer.echo(f"  Labels: {', '.join(issue.labels)}")
            typer.echo(f"  URL: {issue.url}")
            typer.echo()

    except Exception as e:
        typer.echo(f"❌ Error fetching Linear issues: {e}")
        raise typer.Exit(1)


@app.command("unarchive-projects")
def unarchive_projects():
    """Unarchive all mapped Toggl projects."""
    if not toggl_api:
        typer.echo("❌ Toggl API not configured. Run 'taskbridge config' first.")
        raise typer.Exit(1)

    projects = db.get_all_projects()
    if not projects:
        typer.echo("No project mappings found.")
        return

    typer.echo("Checking and unarchiving Toggl projects...")

    # Get current Toggl projects
    toggl_projects = {tp.id: tp for tp in toggl_api.get_projects()}

    for project in projects:
        try:
            project_id = int(project.toggl_project_id)

            if project_id in toggl_projects:
                toggl_project = toggl_projects[project_id]

                if not toggl_project.active:
                    typer.echo(f"🔄 Unarchiving: {toggl_project.name}")

                    # Update project to set active=True
                    data = {'active': True}
                    toggl_api._make_request('PUT', f'/workspaces/{toggl_api.workspace_id}/projects/{project_id}', json=data)
                    typer.echo(f"  ✅ Unarchived: {toggl_project.name}")
                else:
                    typer.echo(f"  ✅ Already active: {toggl_project.name}")
            else:
                typer.echo(f"  ❌ Project {project_id} not found in Toggl")

        except Exception as e:
            typer.echo(f"  ❌ Error with project {project.toggl_project_id}: {e}")

    typer.echo("\n✅ Unarchive process completed!")
    typer.echo("Run 'taskbridge list-projects' to verify status.")


if __name__ == "__main__":
    app()
