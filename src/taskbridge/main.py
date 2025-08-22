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
from .taskwarrior_provider import TaskwarriorProvider

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


@app.command("config-taskwarrior")
def config_taskwarrior():
    """Configure Taskwarrior integration settings."""
    typer.echo("Taskwarrior Configuration")
    typer.echo("=" * 25)

    current_cmd = config_manager.get_taskwarrior_cmd()
    current_enabled = config_manager.get_taskwarrior_enabled()

    typer.echo(f"Current command path: {current_cmd}")
    typer.echo(f"Current status: {'Enabled' if current_enabled else 'Disabled'}")

    if typer.confirm("Update Taskwarrior configuration?"):
        # Test if Taskwarrior is available
        try:
            provider = TaskwarriorProvider(current_cmd)
            typer.echo("✅ Taskwarrior is available and working")
            
            if typer.confirm("Enable Taskwarrior integration?", default=current_enabled):
                config_manager.set_taskwarrior_enabled(True)
                typer.echo("✅ Taskwarrior integration enabled")
            else:
                config_manager.set_taskwarrior_enabled(False)
                typer.echo("ℹ️  Taskwarrior integration disabled")
                
        except Exception as e:
            typer.echo(f"❌ Taskwarrior not available: {e}")
            
            # Ask for custom path
            if typer.confirm("Specify custom Taskwarrior command path?"):
                custom_cmd = typer.prompt("Enter Taskwarrior command path", default="task")
                try:
                    test_provider = TaskwarriorProvider(custom_cmd)
                    config_manager.set_taskwarrior_cmd(custom_cmd)
                    config_manager.set_taskwarrior_enabled(True)
                    typer.echo(f"✅ Taskwarrior configured with custom path: {custom_cmd}")
                except Exception as e2:
                    typer.echo(f"❌ Custom path also failed: {e2}")
                    typer.echo("❌ Taskwarrior integration remains disabled")


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
def search(
    query: str,
    include_done: bool = typer.Option(False, "--include-done", help="Include completed/canceled issues")
):
    """Search Linear issues."""
    if not linear_api:
        typer.echo("❌ Linear API not configured. Run 'taskbridge config' first.")
        raise typer.Exit(1)

    try:
        typer.echo(f"Searching Linear for: {query}")
        issues = linear_api.get_issues(query=query, include_done=include_done)

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
            issues = linear_api.get_issues(query=issue_id, include_done=True)
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
            typer.echo("")
            typer.echo("🚨🚨🚨 WARNING: NO TOGGL PROJECT MAPPING FOUND! 🚨🚨🚨")
            typer.echo(f"⚠️  Linear project '{issue.project_id}' is not synced to Toggl")
            typer.echo("⚠️  Timer will be created WITHOUT a project assignment")
            typer.echo("⚠️  This means time tracking won't be properly categorized!")
            typer.echo("")
            typer.echo("🔧 FIX: Run 'taskbridge sync' to create project mappings")
            typer.echo("")
            
            # Ask if they want to continue
            if not typer.confirm("Continue anyway?", default=False):
                typer.echo("Timer start cancelled.")
                return
    else:
        typer.echo("")
        typer.echo("🟡🟡🟡 WARNING: ISSUE HAS NO PROJECT! 🟡🟡🟡")
        typer.echo("⚠️  This Linear issue is not assigned to any project")
        typer.echo("⚠️  Timer will be created without project categorization")
        typer.echo("⚠️  Consider assigning the issue to a Linear project first")
        typer.echo("")
        
        # Ask if they want to continue
        if not typer.confirm("Continue anyway?", default=True):
            typer.echo("Timer start cancelled.")
            return

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
            
            # Add Obsidian URL as comment in Linear
            url = config_manager.generate_obsidian_url(project_name, note_path.name)
            comment_body = f"📝 Obsidian note created: [Open in Obsidian]({url})"
            
            if linear_api.create_comment(issue.id, comment_body):
                typer.echo("   💬 Added Obsidian URL to Linear issue")
            else:
                typer.echo("   ⚠️  Failed to add comment to Linear issue")
                
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
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum number of issues to show"),
    include_done: bool = typer.Option(False, "--include-done", help="Include completed/canceled issues")
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

        issues = linear_api.get_issues(project_id=project_id, include_done=include_done)

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


# Taskwarrior Commands
@app.command("tw-projects")
def taskwarrior_projects():
    """Show Taskwarrior projects."""
    try:
        provider = TaskwarriorProvider()
        projects = provider.get_projects()
        
        if not projects:
            typer.echo("No Taskwarrior projects found.")
            return
            
        typer.echo(f"Found {len(projects)} Taskwarrior project(s):")
        typer.echo("=" * 60)
        
        for project in projects:
            typer.echo(f"Project: {project.name}")
            typer.echo(f"  State: {project.state}")
            typer.echo(f"  Progress: {project.progress:.1%}")
            typer.echo(f"  Tasks: {project.custom_fields.get('tasks_count', 0)}")
            typer.echo(f"  Pending: {project.custom_fields.get('pending_count', 0)}")
            typer.echo(f"  Completed: {project.custom_fields.get('completed_count', 0)}")
            if project.description:
                typer.echo(f"  Description: {project.description}")
            typer.echo()
            
    except Exception as e:
        typer.echo(f"❌ Error fetching Taskwarrior projects: {e}")
        raise typer.Exit(1)


@app.command("tw-tasks")
def taskwarrior_tasks(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filter by project"),
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Search query"),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum number of tasks to show"),
    include_done: bool = typer.Option(False, "--include-done", help="Include completed tasks")
):
    """Show Taskwarrior tasks."""
    try:
        provider = TaskwarriorProvider()
        issues = provider.get_issues(
            project_id=project, 
            query=query, 
            limit=limit,
            include_done=include_done
        )
        
        if not issues:
            typer.echo("No Taskwarrior tasks found.")
            return
            
        typer.echo(f"Found {len(issues)} task(s):")
        typer.echo("=" * 60)
        
        for issue in issues:
            typer.echo(f"Task: {issue.title}")
            typer.echo(f"  ID: {issue.id}")
            typer.echo(f"  State: {issue.state}")
            if issue.project_id:
                typer.echo(f"  Project: {issue.project_id}")
            if issue.priority:
                typer.echo(f"  Priority: {issue.priority}")
            if issue.estimate:
                typer.echo(f"  Estimate: {issue.estimate}")
            if issue.labels:
                typer.echo(f"  Tags: {', '.join(issue.labels)}")
            if issue.custom_fields.get('urgency'):
                typer.echo(f"  Urgency: {issue.custom_fields['urgency']}")
            typer.echo(f"  Created: {issue.created_at}")
            typer.echo(f"  Modified: {issue.updated_at}")
            typer.echo()
            
    except Exception as e:
        typer.echo(f"❌ Error fetching Taskwarrior tasks: {e}")
        raise typer.Exit(1)


@app.command("tw-export")
def taskwarrior_export(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filter by project"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    include_done: bool = typer.Option(False, "--include-done", help="Include completed tasks")
):
    """Export Taskwarrior tasks to JSON format."""
    try:
        provider = TaskwarriorProvider()
        issues = provider.get_issues(
            project_id=project,
            limit=0,  # No limit
            include_done=include_done
        )
        
        # Convert to exportable format
        export_data = []
        for issue in issues:
            export_data.append({
                "id": issue.id,
                "title": issue.title,
                "description": issue.description,
                "state": issue.state,
                "priority": issue.priority,
                "project_id": issue.project_id,
                "labels": issue.labels,
                "estimate": issue.estimate,
                "created_at": issue.created_at,
                "updated_at": issue.updated_at,
                "custom_fields": issue.custom_fields
            })
        
        import json
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2)
            typer.echo(f"✅ Exported {len(export_data)} tasks to {output_file}")
        else:
            typer.echo(json.dumps(export_data, indent=2))
            
    except Exception as e:
        typer.echo(f"❌ Error exporting Taskwarrior tasks: {e}")
        raise typer.Exit(1)


@app.command("tw-create")
def taskwarrior_create(
    title: str,
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
    priority: Optional[str] = typer.Option(None, "--priority", help="Priority (H, M, L)"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated tags")
):
    """Create a new Taskwarrior task."""
    try:
        provider = TaskwarriorProvider()
        
        # Parse tags
        tag_list = []
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',')]
        
        from .taskwarrior_provider import UniversalIssue
        issue = UniversalIssue(
            id="",  # Will be generated
            title=title,
            description=None,
            state="pending",
            priority=priority or "",
            assignee_id=None,
            project_id=project,
            labels=tag_list,
            estimate=None,
            url="",
            created_at="",
            updated_at="",
            custom_fields={}
        )
        
        task_uuid = provider.create_issue(issue)
        if task_uuid:
            typer.echo(f"✅ Created task: {title}")
            typer.echo(f"   UUID: {task_uuid}")
            if project:
                typer.echo(f"   Project: {project}")
            if priority:
                typer.echo(f"   Priority: {priority}")
            if tag_list:
                typer.echo(f"   Tags: {', '.join(tag_list)}")
        else:
            typer.echo("❌ Failed to create task")
            
    except Exception as e:
        typer.echo(f"❌ Error creating Taskwarrior task: {e}")
        raise typer.Exit(1)


@app.command("tw-complete")
def taskwarrior_complete(task_uuid: str):
    """Mark a Taskwarrior task as completed."""
    try:
        provider = TaskwarriorProvider()
        
        if provider.complete_issue(task_uuid):
            typer.echo(f"✅ Completed task: {task_uuid}")
        else:
            typer.echo(f"❌ Failed to complete task: {task_uuid}")
            
    except Exception as e:
        typer.echo(f"❌ Error completing task: {e}")
        raise typer.Exit(1)




@app.command("sync-linear-to-tw")
def sync_linear_to_taskwarrior(
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be done without making changes"),
    project_filter: Optional[str] = typer.Option(None, "--project", "-p", help="Only sync issues from specific Linear project"),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum number of issues to sync"),
    sync_completed: bool = typer.Option(True, "--sync-completed", help="Mark completed Linear tasks as done in Taskwarrior")
):
    """One-way sync: Linear issues → Taskwarrior tasks. Includes completion status sync."""
    if not linear_api:
        typer.echo("❌ Linear API not configured. Run 'taskbridge config' first.")
        raise typer.Exit(1)
    
    try:
        tw_provider = TaskwarriorProvider()
        
        typer.echo("🔄 Syncing Linear issues to Taskwarrior...")
        typer.echo("📥 Fetching Linear issues...")
        
        # Get Linear issues with optional project filter (include completed for sync)
        linear_issues = linear_api.get_issues(
            project_id=project_filter,
            limit=limit,
            include_done=True  # Include completed issues for status sync
        )
        
        typer.echo(f"Found {len(linear_issues)} Linear issues")
        
        if not linear_issues:
            typer.echo("No Linear issues found to sync.")
            return
        
        # Get project names for mapping
        projects = {p.id: p.name for p in linear_api.get_projects()}
        
        if dry_run:
            typer.echo("[DRY RUN] Would perform the following actions:")
            typer.echo("-" * 60)
            
            # Get existing tasks for dry-run analysis
            existing_tasks = tw_provider.get_issues(limit=0, include_done=True)
            existing_linear_ids = set()
            existing_titles = set()
            
            for task in existing_tasks:
                existing_titles.add(task.title)
                if task.custom_fields and "annotations" in task.custom_fields:
                    annotations = task.custom_fields["annotations"]
                    for annotation in annotations:
                        if isinstance(annotation, dict) and "description" in annotation:
                            desc = annotation["description"]
                            if desc.startswith("Linear ID: "):
                                existing_linear_ids.add(desc[11:])
            
            create_count = 0
            complete_count = 0
            skip_count = 0
            
            for issue in linear_issues:
                # Determine action for this issue
                action = "SKIP"
                if issue.id in existing_linear_ids:
                    if sync_completed and issue.state_type in ['completed', 'canceled']:
                        # Check if task needs completion
                        existing_task = None
                        for task in existing_tasks:
                            if task.custom_fields and "annotations" in task.custom_fields:
                                annotations = task.custom_fields["annotations"]
                                for annotation in annotations:
                                    if isinstance(annotation, dict) and "description" in annotation:
                                        desc = annotation["description"]
                                        if desc == f"Linear ID: {issue.id}":
                                            existing_task = task
                                            break
                                if existing_task:
                                    break
                        
                        if existing_task and existing_task.state == "pending":
                            action = "COMPLETE"
                            complete_count += 1
                        else:
                            skip_count += 1
                    else:
                        skip_count += 1
                elif issue.title in existing_titles:
                    action = "SKIP (title exists)"
                    skip_count += 1
                elif issue.state_type in ['completed', 'canceled']:
                    action = "SKIP (completed in Linear)"
                    skip_count += 1
                else:
                    action = "CREATE"
                    create_count += 1
                
                # Display issue with action
                project_name = projects.get(issue.project_id, "linear") if issue.project_id else "linear"
                
                # Parse client information for dry run display
                client_name = None
                if issue.project_id:
                    linear_projects = linear_api.get_projects()
                    linear_project = next((p for p in linear_projects if p.id == issue.project_id), None)
                    if linear_project and linear_project.labels:
                        client_name, parsed_project_name = linear_api.parse_client_project_name(linear_project.labels)
                        if parsed_project_name:
                            project_name = parsed_project_name
                
                # Use client.project format if client exists
                if client_name:
                    project_name = f"{client_name}.{project_name}"
                
                priority_map = {0: "", 1: "L", 2: "M", 3: "H", 4: "H"}
                priority = priority_map.get(issue.priority, "")
                
                # Show action icon
                action_icon = {
                    "CREATE": "✅",
                    "COMPLETE": "✅",
                    "SKIP": "⏭️",
                    "SKIP (title exists)": "⏭️",
                    "SKIP (completed in Linear)": "⏭️"
                }.get(action, "❓")
                
                typer.echo(f"{action_icon} [{action}] {issue.title}")
                typer.echo(f"   Project: {project_name}")
                typer.echo(f"   Linear State: {issue.state_type}")
                if client_name:
                    typer.echo(f"   Client: {client_name}")
                if priority:
                    typer.echo(f"   Priority: {priority}")
                if issue.labels:
                    typer.echo(f"   Labels: {', '.join(issue.labels)}")
                typer.echo()
            
            typer.echo(f"Summary:")
            typer.echo(f"   Would create: {create_count}")
            typer.echo(f"   Would complete: {complete_count}")
            typer.echo(f"   Would skip: {skip_count}")
            typer.echo(f"   Total: {len(linear_issues)}")
            return
        
        # Ask for confirmation
        if not typer.confirm(f"Sync {len(linear_issues)} Linear issues with Taskwarrior?"):
            typer.echo("Sync cancelled.")
            return
        
        # Get existing Taskwarrior tasks to avoid duplicates
        typer.echo("🔍 Checking for existing tasks...")
        existing_tasks = tw_provider.get_issues(limit=0, include_done=True)
        
        # Check for tasks that already have Linear IDs
        existing_linear_ids = set()
        existing_titles = set()
        
        for task in existing_tasks:
            existing_titles.add(task.title)
            # Check if task has Linear ID in annotations
            if task.custom_fields and "annotations" in task.custom_fields:
                annotations = task.custom_fields["annotations"]
                for annotation in annotations:
                    if isinstance(annotation, dict) and "description" in annotation:
                        desc = annotation["description"]
                        if desc.startswith("Linear ID: "):
                            existing_linear_ids.add(desc[11:])  # Remove 'Linear ID: ' prefix
        
        # Sync the issues
        created_count = 0
        skipped_count = 0
        failed_count = 0
        completed_count = 0
        
        typer.echo("📝 Syncing Taskwarrior tasks...")
        
        for issue in linear_issues:
            # Check if task already exists
            if issue.id in existing_linear_ids:
                # Task exists - check if completion status needs to be synced
                if sync_completed and issue.state_type in ['completed', 'canceled']:
                    # Find the existing task by Linear ID
                    existing_task = None
                    for task in existing_tasks:
                        if task.custom_fields and "annotations" in task.custom_fields:
                            annotations = task.custom_fields["annotations"]
                            for annotation in annotations:
                                if isinstance(annotation, dict) and "description" in annotation:
                                    desc = annotation["description"]
                                    if desc == f"Linear ID: {issue.id}":
                                        existing_task = task
                                        break
                            if existing_task:
                                break
                    
                    if existing_task and existing_task.state == "pending":
                        # Mark as completed in Taskwarrior
                        if tw_provider.complete_issue(existing_task.id):
                            completed_count += 1
                            typer.echo(f"✅ Completed: {issue.title}")
                        else:
                            typer.echo(f"❌ Failed to complete: {issue.title}")
                    else:
                        skipped_count += 1
                        typer.echo(f"⏭️  Skipped (already completed): {issue.title}")
                else:
                    skipped_count += 1
                    typer.echo(f"⏭️  Skipped (exists): {issue.title}")
                continue
            
            elif issue.title in existing_titles:
                skipped_count += 1
                typer.echo(f"⏭️  Skipped (title exists): {issue.title}")
                continue
            
            # Convert Linear issue to Taskwarrior task
            project_name = projects.get(issue.project_id, "linear") if issue.project_id else "linear"
            
            # Parse client information from Linear labels  
            client_name = None
            if issue.project_id:
                # Get the full project to access labels
                linear_projects = linear_api.get_projects()
                linear_project = next((p for p in linear_projects if p.id == issue.project_id), None)
                if linear_project and linear_project.labels:
                    client_name, parsed_project_name = linear_api.parse_client_project_name(linear_project.labels)
                    if parsed_project_name:
                        project_name = parsed_project_name
            
            # Use client.project format if client exists
            if client_name:
                project_name = f"{client_name}.{project_name}"
            
            priority_map = {0: "", 1: "L", 2: "M", 3: "H", 4: "H"}
            priority = priority_map.get(issue.priority, "")
            
            # Add Linear-specific tags
            tags = list(issue.labels) if issue.labels else []
            tags.append("_linear")  # Use underscore prefix for system tag
            
            # Add client tag if we found one
            if client_name:
                tags.append(f"client:{client_name}")
            
            # Map special Linear labels to system tags
            if issue.labels:
                for label in issue.labels:
                    if label.lower() == "blocked":
                        tags.append("_blocked")
            
            # Check for Obsidian URLs in Linear issue description/comments
            annotations = []
            
            # Add Linear ID as annotation instead of tag
            annotations.append({
                "description": f"Linear ID: {issue.id}",
                "entry": issue.created_at
            })
            
            # Look for Obsidian URLs in description
            import re
            if issue.description:
                obsidian_urls = re.findall(r'obsidian://[^\s\)\]]+', issue.description)
                for url in obsidian_urls:
                    annotations.append({
                        "description": f"📝 Obsidian: {url}",
                        "entry": issue.created_at
                    })
            
            # Look for Obsidian URLs in comments
            try:
                comments = linear_api.get_issue_comments(issue.id)
                for comment in comments:
                    if comment.get('body'):
                        obsidian_urls = re.findall(r'obsidian://[^\s\)\]]+', comment['body'])
                        for url in obsidian_urls:
                            annotations.append({
                                "description": f"📝 Obsidian: {url}",
                                "entry": comment.get('createdAt', issue.created_at)
                            })
            except Exception as e:
                # Ignore comment fetching errors
                typer.echo(f"   ⚠️ Could not fetch comments: {e}")
                pass
            
            # Skip creating completed Linear issues unless they need to be tracked
            if issue.state_type in ['completed', 'canceled']:
                skipped_count += 1
                typer.echo(f"⏭️  Skipped (completed in Linear): {issue.title}")
                continue
            
            from .taskwarrior_provider import UniversalIssue
            universal_issue = UniversalIssue(
                id="",
                title=issue.title,
                description=issue.description,
                state="pending",
                priority=priority,
                assignee_id=None,
                project_id=project_name,
                labels=tags,
                estimate=str(issue.estimate) if issue.estimate else None,
                url=issue.url,
                created_at=issue.created_at,
                updated_at=issue.updated_at,
                custom_fields={
                    "linear_id": issue.id,
                    "annotations": annotations,
                    "client_name": client_name
                }
            )
            
            # Create in Taskwarrior
            task_uuid = tw_provider.create_issue(universal_issue)
            if task_uuid:
                created_count += 1
                typer.echo(f"✅ Created: {issue.title}")
            else:
                failed_count += 1
                typer.echo(f"❌ Failed: {issue.title}")
        
        # Summary
        typer.echo("\n" + "=" * 50)
        typer.echo("📊 Sync Summary:")
        typer.echo(f"   ✅ Created: {created_count}")
        typer.echo(f"   ✅ Completed: {completed_count}")
        typer.echo(f"   ⏭️  Skipped: {skipped_count}")
        typer.echo(f"   ❌ Failed: {failed_count}")
        typer.echo(f"   📋 Total: {len(linear_issues)}")
        
        if created_count > 0 or completed_count > 0:
            typer.echo(f"\n🎉 Successfully synced {created_count + completed_count} Linear issues to Taskwarrior!")
            if created_count > 0:
                typer.echo("💡 Tip: Use 'taskbridge tw-tasks --query linear' to see synced tasks")
            if completed_count > 0:
                typer.echo("💡 Tip: Completed Linear tasks are now marked as done in Taskwarrior")
        
    except Exception as e:
        typer.echo(f"❌ Error during sync: {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
