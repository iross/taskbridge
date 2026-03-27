"""Main CLI entry point for TaskBridge."""

import contextlib
import subprocess
import urllib.parse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import typer

from .bartib_integration import BartibIntegration
from .config import config as config_manager
from .database import TaskTimeTracking, TodoistNoteMapping, db
from .todoist_api import TodoistAPI

# Main app
app = typer.Typer(
    name="taskbridge",
    help="TaskBridge - Todoist and Obsidian integration",
    add_completion=False,
)

# Command groups
config_app = typer.Typer(help="Configuration commands")
task_app = typer.Typer(help="Task management commands")
project_app = typer.Typer(help="Project management commands")
map_app = typer.Typer(help="Task-to-note mapping commands")
sync_app = typer.Typer(help="Synchronization commands")
time_app = typer.Typer(help="Time tracking commands")
meeting_app = typer.Typer(help="Meeting time tracking commands")

app.add_typer(config_app, name="config")
app.add_typer(task_app, name="task")
app.add_typer(project_app, name="project")
app.add_typer(map_app, name="map")
app.add_typer(sync_app, name="sync")
app.add_typer(time_app, name="time")
app.add_typer(meeting_app, name="meeting")


# ============================================================================
# CONFIG COMMANDS
# ============================================================================


@config_app.command("todoist")
def config_todoist():
    """Configure Todoist integration settings."""
    typer.echo("Todoist Configuration")
    typer.echo("=" * 30)

    # 1. Get and validate API token
    current_token = config_manager.get_todoist_token()
    if current_token:
        typer.echo(f"Current token: {current_token[:8]}...")
        if not typer.confirm("Update Todoist token?"):
            token = current_token
        else:
            token = typer.prompt("Enter Todoist API token")
    else:
        typer.echo("Get your token from: https://todoist.com/app/settings/integrations/developer")
        token = typer.prompt("Enter Todoist API token")

    # Validate token
    if not config_manager.validate_todoist_token(token):
        typer.echo("❌ Invalid token")
        raise typer.Exit(1) from None

    config_manager.set("todoist_token", token)
    typer.echo("✅ Token validated and saved")

    # 2. Configure sync label
    current_label = config_manager.get_todoist_sync_label()
    typer.echo(f"\nCurrent sync label: {current_label}")
    typer.echo("Tasks with this label will trigger Obsidian note creation")

    if typer.confirm("Update sync label?"):
        label = typer.prompt("Enter sync label", default="@obsidian")
        config_manager.set("todoist_sync_label", label)

    # 3. Configure project mappings
    if typer.confirm("\nConfigure project → folder mappings?"):
        try:
            api = TodoistAPI(token)
            projects = api.get_projects()

            typer.echo(f"\nFound {len(projects)} Todoist projects:")
            for i, proj in enumerate(projects, 1):
                typer.echo(f"{i}. {proj.name} (ID: {proj.id})")

            while typer.confirm("\nAdd project mapping?"):
                project_num = typer.prompt("Select project number", type=int)
                if 1 <= project_num <= len(projects):
                    project = projects[project_num - 1]

                    client_name = typer.prompt(f"Client name for '{project.name}'", default="")
                    folder_name = typer.prompt("Obsidian folder name", default=project.name)

                    config_manager.set_todoist_project_mapping(project.id, client_name, folder_name)
                    typer.echo(f"✅ Mapped {project.name} → {folder_name}")
                else:
                    typer.echo("Invalid selection")
        except Exception as e:
            typer.echo(f"⚠️  Error fetching projects: {e}")

    typer.echo("\n✅ Todoist configuration complete!")


@config_app.command("obsidian")
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
    except ValueError as e:
        typer.echo(f"❌ {e}")
        raise typer.Exit(1) from None


@config_app.command("gcal")
def config_gcal():
    """Configure Google Calendar integration for time-gap filling."""
    typer.echo("Google Calendar Configuration")
    typer.echo("=" * 30)
    typer.echo(
        "You need a credentials.json file from Google Cloud Console.\n"
        "  1. Go to console.cloud.google.com → APIs & Services → Credentials\n"
        "  2. Create an OAuth 2.0 Client ID (Desktop app)\n"
        "  3. Download the JSON and note its path\n"
        "  4. Enable the Google Calendar API in your project\n"
    )

    current_path = config_manager.get_gcal_credentials_path()
    if current_path:
        typer.echo(f"Current credentials: {current_path}")
        if not typer.confirm("Update credentials path?"):
            credentials_path = current_path
        else:
            credentials_path = typer.prompt("Path to credentials.json")
    else:
        credentials_path = typer.prompt("Path to credentials.json")

    current_cal = config_manager.get_gcal_calendar_id()
    calendar_id = typer.prompt("Calendar ID", default=current_cal)

    try:
        config_manager.set_gcal_config(credentials_path, calendar_id)
    except ValueError as e:
        typer.echo(f"❌ {e}")
        raise typer.Exit(1) from None

    typer.echo("\nTesting authentication (browser will open for first-time auth)...")
    try:
        from taskbridge.gcal_integration import GoogleCalendarClient

        creds_path = config_manager.get_gcal_credentials_path()
        assert creds_path is not None  # set just above
        client = GoogleCalendarClient(
            credentials_path=creds_path,
            token_path=config_manager.get_gcal_token_path(),
        )
        client.authenticate()
        typer.echo("✅ Google Calendar configured and authenticated")
    except Exception as e:
        typer.echo(f"❌ Authentication failed: {e}")
        raise typer.Exit(1) from None


# ============================================================================
# TASK COMMANDS
# ============================================================================


@task_app.command("list")
def task_list(
    project: str | None = typer.Option(
        None, "--project", "-p", help="Filter by project ID or name"
    ),
    label: str | None = typer.Option(None, "--label", "-l", help="Filter by label"),
    filter_query: str | None = typer.Option(None, "--filter", "-f", help="Todoist filter query"),
    limit: int = typer.Option(20, "--limit", help="Maximum tasks to display"),
    include_done: bool = typer.Option(False, "--include-done", help="Include completed tasks"),
    without_notes: bool = typer.Option(
        False, "--without-notes", help="Only show tasks without notes"
    ),
):
    """List Todoist tasks with their IDs and details."""
    if not config_manager.get_todoist_token():
        typer.echo("❌ Todoist not configured. Run 'taskbridge config todoist' first.")
        raise typer.Exit(1) from None

    try:
        api = TodoistAPI()

        # If project is provided as name, try to find ID
        actual_project_id = project
        if project and not project.isdigit():
            projects = api.get_projects()
            matching = [p for p in projects if p.name.lower() == project.lower()]
            if matching:
                actual_project_id = matching[0].id
                typer.echo(f"📁 Using project: {matching[0].name} (ID: {actual_project_id})")
            else:
                typer.echo(f"⚠️  Project '{project}' not found, searching all projects...")
                actual_project_id = None

        # Fetch tasks
        typer.echo("🔍 Fetching Todoist tasks...")
        all_tasks = api.get_tasks(
            project_id=actual_project_id, label=label, filter_query=filter_query
        )

        # Filter by completion status
        tasks = [t for t in all_tasks if not t.is_completed] if not include_done else all_tasks

        # Filter by notes if requested
        if without_notes:
            tasks_with_notes = []
            for task in tasks:
                existing_note = db.get_todoist_note_by_task_id(task.id)
                if existing_note is None:
                    tasks_with_notes.append(task)
            tasks = tasks_with_notes

        # Apply limit
        tasks = tasks[:limit]

        if not tasks:
            typer.echo("No tasks found.")
            return

        typer.echo(f"\nFound {len(tasks)} task(s):")
        typer.echo("=" * 80)

        # Cache projects to avoid repeated API calls
        project_cache = {}

        # Get mappings to show note status
        mappings = db.get_all_todoist_mappings()
        mappings_dict = {m.todoist_task_id: m for m in mappings}

        for i, task in enumerate(tasks, 1):
            typer.echo(f"\n{i}. {task.content}")
            typer.echo(f"   ID: {task.id}")

            # Show description if available
            if task.description:
                desc = (
                    task.description[:80] + "..."
                    if len(task.description) > 80
                    else task.description
                )
                typer.echo(f"   Description: {desc}")

            # Show project
            if task.project_id:
                if task.project_id not in project_cache:
                    project_obj = api.get_project(task.project_id)
                    project_cache[task.project_id] = project_obj.name if project_obj else "Unknown"
                typer.echo(f"   📁 Project: {project_cache[task.project_id]}")

            # Show labels
            if task.labels:
                typer.echo(f"   🏷️  Labels: {', '.join(task.labels)}")

            # Show priority
            if task.priority > 1:
                priority_map = {4: "High", 3: "Medium", 2: "Low"}
                typer.echo(f"   ⚡ Priority: {priority_map.get(task.priority, 'Normal')}")

            # Show due date
            if task.due:
                due_date = task.due.get("date", "")
                if due_date:
                    typer.echo(f"   📅 Due: {due_date}")

            # Show completion status
            if task.is_completed:
                typer.echo("   ✅ Status: Completed")

            # Show mapping status
            if task.id in mappings_dict:
                note_name = Path(mappings_dict[task.id].note_path).name
                typer.echo(f"   📝 Note: {note_name}")
            else:
                typer.echo("   📝 Note: (none)")

            typer.echo(f"   🔗 URL: {task.url}")

        if len(all_tasks) > limit:
            typer.echo(
                f"\n... showing {limit} of {len(all_tasks)} tasks. Use --limit to show more."
            )

    except Exception as e:
        typer.echo(f"❌ Error: {e}")
        raise typer.Exit(1) from None


@task_app.command("show")
def task_show(task_id: str):
    """Show task details and mapping information."""
    if not config_manager.get_todoist_token():
        typer.echo("❌ Todoist not configured. Run 'taskbridge config todoist' first.")
        raise typer.Exit(1) from None

    try:
        api = TodoistAPI()

        # Get mapping from database
        mapping = db.get_todoist_note_by_task_id(task_id)
        if not mapping:
            typer.echo(f"❌ No mapping found for task ID: {task_id}")
            typer.echo("   This task may not have an Obsidian note yet.")
            typer.echo(f"   Use 'taskbridge task note {task_id}' to create one.")
            raise typer.Exit(1) from None

        # Get current task info from Todoist
        task = api.get_task(task_id)

        typer.echo("\n" + "=" * 70)
        typer.echo("📋 Task Mapping Details")
        typer.echo("=" * 70)

        if task:
            typer.echo("\n📝 Todoist Task:")
            typer.echo(f"   Title: {task.content}")
            typer.echo(f"   Task ID: {task.id}")

            project = api.get_project(task.project_id)
            project_name = project.name if project else "Unknown"
            typer.echo(f"   Current Project: {project_name} (ID: {task.project_id})")

            if task.labels:
                typer.echo(f"   Labels: {', '.join(task.labels)}")
        else:
            typer.echo("\n⚠️  Task not found in Todoist (may be deleted)")
            typer.echo(f"   Task ID: {task_id}")

        typer.echo("\n📖 Obsidian Note:")
        typer.echo(f"   Path: {mapping.note_path}")
        typer.echo(f"   URL: {mapping.obsidian_url}")

        # Check if file exists
        note_exists = Path(mapping.note_path).exists()
        typer.echo(f"   Exists: {'✅ Yes' if note_exists else '❌ No (deleted)'}")

        typer.echo("\n🗄️  Database Mapping:")
        typer.echo(f"   Mapped Project ID: {mapping.todoist_project_id}")
        typer.echo(f"   Created: {mapping.created_at}")
        typer.echo(f"   Updated: {mapping.updated_at}")

        # Show if there's a mismatch
        if task and task.project_id != mapping.todoist_project_id:
            typer.echo("\n⚠️  WARNING: Project mismatch detected!")
            typer.echo(f"   Todoist project: {task.project_id}")
            typer.echo(f"   Mapped project: {mapping.todoist_project_id}")
            typer.echo(f"   Use 'taskbridge map update {task_id}' to sync")

        if not note_exists:
            typer.echo("\n⚠️  WARNING: Note file doesn't exist!")
            typer.echo(f"   Use 'taskbridge task note {task_id}' to recreate it")

        typer.echo()

    except Exception as e:
        typer.echo(f"❌ Error: {e}")
        raise typer.Exit(1) from None


@task_app.command("done")
def task_done(
    task_id: str,
    archive_note: bool = typer.Option(
        True, "--archive-note/--no-archive-note", help="Move note to archive"
    ),
):
    """Mark a task as complete in Todoist and update the Obsidian note."""
    if not config_manager.get_todoist_token():
        typer.echo("❌ Todoist not configured. Run 'taskbridge config todoist' first.")
        raise typer.Exit(1) from None

    try:
        api = TodoistAPI()

        # Get task details before completing
        task = api.get_task(task_id)
        if not task:
            typer.echo(f"❌ Task {task_id} not found in Todoist")
            raise typer.Exit(1) from None

        typer.echo(f"Task: {task.content}")

        # Check if already completed
        if task.is_completed:
            typer.echo("⚠️  Task is already completed in Todoist")
        else:
            # Mark task as complete in Todoist
            typer.echo("\n✓ Marking task as complete in Todoist...")
            if api.close_task(task_id):
                typer.echo("✅ Task marked as complete in Todoist")
            else:
                typer.echo("❌ Failed to mark task as complete in Todoist")
                raise typer.Exit(1) from None

        # Stop time tracking if active for this task
        try:
            tracking = db.get_tracking_by_task_id(task_id)
            if tracking and not tracking.stopped_at:
                typer.echo("\n⏱️  Stopping time tracking...")
                success, duration = stop_tracking_internal(tracking)
                if success and duration > 0:
                    typer.echo(f"✅ Tracked {format_duration(duration)}")
        except Exception as e:
            typer.echo(f"⚠️  Warning: Could not stop time tracking: {e}")

        # Update Obsidian note if it exists
        mapping = db.get_todoist_note_by_task_id(task_id)
        if mapping:
            note_path = Path(mapping.note_path)

            if note_path.exists():
                typer.echo("\n📝 Updating Obsidian note...")

                # Read the note
                content = note_path.read_text()

                # Update status in frontmatter
                if "status: " in content:
                    # Replace existing status
                    import re

                    content = re.sub(r'status: "[^"]*"', 'status: "done"', content)
                    content = re.sub(r"status: '[^']*'", "status: 'done'", content)
                    content = re.sub(r"status: \S+", 'status: "done"', content)
                else:
                    # Add status if not present (after fileClass line)
                    content = content.replace(
                        'fileClass: "task"', 'fileClass: "task"\nstatus: "done"'
                    )

                # Write back
                note_path.write_text(content)
                typer.echo(f"✅ Updated note status to 'done': {note_path.name}")

                # Archive note if requested
                if archive_note:
                    vault_path = config_manager.get_obsidian_vault_path()
                    if vault_path:
                        archive_dir = Path(vault_path) / "40 Archive"
                        archive_dir.mkdir(exist_ok=True)

                        archive_path = archive_dir / note_path.name
                        note_path.rename(archive_path)

                        # Update database mapping
                        mapping.note_path = str(archive_path)
                        mapping.obsidian_url = config_manager.generate_obsidian_url(
                            "40 Archive", archive_path.name
                        )
                        db.update_todoist_note_mapping(mapping)

                        typer.echo(f"📦 Archived note to: {archive_path}")
            else:
                typer.echo(f"\n⚠️  Note file doesn't exist: {note_path}")
        else:
            typer.echo("\nℹ️  No Obsidian note found for this task")

        typer.echo("\n✅ Task completed!")

    except Exception as e:
        typer.echo(f"❌ Error: {e}")
        raise typer.Exit(1) from None


@task_app.command("select")
def task_select(
    project: str | None = typer.Option(
        None, "--project", "-p", help="Filter by project ID or name"
    ),
    label: str | None = typer.Option(None, "--label", "-l", help="Filter by label"),
    filter_query: str | None = typer.Option(None, "--filter", "-f", help="Todoist filter query"),
    limit: int = typer.Option(100, "--limit", help="Maximum tasks to display"),
    without_notes: bool = typer.Option(
        False, "--without-notes", help="Only show tasks without notes"
    ),
):
    """Select a task using fzf and output its ID."""
    if not config_manager.get_todoist_token():
        typer.echo("❌ Todoist not configured. Run 'taskbridge config todoist' first.", err=True)
        raise typer.Exit(1) from None

    # Check if fzf is installed
    fzf_check = subprocess.run(["which", "fzf"], capture_output=True)
    if fzf_check.returncode != 0:
        typer.echo("❌ fzf not found. Install it with: brew install fzf", err=True)
        raise typer.Exit(1) from None

    try:
        api = TodoistAPI()

        # If project is provided as name, try to find ID
        actual_project_id = project
        if project and not project.isdigit():
            projects = api.get_projects()
            matching = [p for p in projects if p.name.lower() == project.lower()]
            actual_project_id = matching[0].id if matching else None

        # Fetch tasks
        all_tasks = api.get_tasks(
            project_id=actual_project_id, label=label, filter_query=filter_query
        )

        # Filter out completed tasks
        tasks = [t for t in all_tasks if not t.is_completed]

        # Filter by notes if requested
        if without_notes:
            tasks_without_notes = []
            for task in tasks:
                existing_note = db.get_todoist_note_by_task_id(task.id)
                if existing_note is None:
                    tasks_without_notes.append(task)
            tasks = tasks_without_notes

        # Apply limit
        tasks = tasks[:limit]

        if not tasks:
            typer.echo("No tasks found.", err=True)
            raise typer.Exit(1) from None

        # Format tasks for fzf: ID | Title | Project | Labels | Due
        fzf_lines = []
        project_cache = {}

        for task in tasks:
            # Get project name
            project_name = ""
            if task.project_id:
                if task.project_id not in project_cache:
                    project_obj = api.get_project(task.project_id)
                    project_cache[task.project_id] = project_obj.name if project_obj else "Unknown"
                project_name = project_cache[task.project_id]

            # Get labels
            labels_str = ", ".join(task.labels) if task.labels else ""

            # Get due date
            due_str = ""
            if task.due:
                due_str = task.due.get("date", "")

            # Format line with all requested info (using simple separators, no emojis)
            parts = [task.id, task.content]
            if project_name:
                parts.append(f"[{project_name}]")
            if labels_str:
                parts.append(f"({labels_str})")
            if due_str:
                parts.append(f"due:{due_str}")

            line = " | ".join(parts)
            fzf_lines.append(line)

        # Pipe to fzf
        fzf_input = "\n".join(fzf_lines)

        # Run fzf with proper terminal access
        # stdin gets the data, stdout captures selection, stderr shows UI
        result = subprocess.run(
            [
                "fzf",
                "--height",
                "50%",
                "--layout=reverse",
                "--border",
                "--prompt",
                "Select task: ",
            ],
            input=fzf_input,
            text=True,
            stdout=subprocess.PIPE,
        )

        if result.returncode != 0:
            # User cancelled
            raise typer.Exit(1) from None

        # Extract task ID (first field before |)
        selected_line = result.stdout.strip()
        task_id = selected_line.split("|")[0].strip()

        # Output just the task ID
        typer.echo(task_id)

    except Exception as e:
        typer.echo(f"❌ Error: {e}", err=True)
        raise typer.Exit(1) from None


@task_app.command("note")
def task_note(
    task_id: str,
    open_note: bool = typer.Option(True, "--open/--no-open", help="Open note after creation"),
    focus: bool = typer.Option(True, "--focus/--no-focus", help="Start Raycast Focus session"),
):
    """Create or recreate an Obsidian note for a Todoist task."""
    if not config_manager.get_todoist_token():
        typer.echo("❌ Todoist not configured. Run 'taskbridge config todoist' first.")
        raise typer.Exit(1) from None

    if not config_manager.get_obsidian_vault_path():
        typer.echo("❌ Obsidian not configured. Run 'taskbridge config obsidian' first.")
        raise typer.Exit(1) from None

    try:
        api = TodoistAPI()

        # Get task details
        task = api.get_task(task_id)
        if not task:
            typer.echo(f"❌ Task {task_id} not found in Todoist")
            raise typer.Exit(1) from None

        typer.echo(f"Task: {task.content}")

        # Get project info (manual mapping → hierarchy inference)
        project_name, client_name = resolve_project_info(task.project_id, api)
        suffix = f" (client: {client_name})" if client_name else ""
        typer.echo(f"Project: {project_name}{suffix}")

        # Create the note
        typer.echo(f"\n📝 Creating note in {project_name}...")
        note_path = config_manager.create_task_note(
            project_name=project_name,
            task_title=task.content,
            client=client_name,
            status="backlog",
            tags=task.labels,
        )

        typer.echo(f"✅ Created note: {note_path}")

        # Generate Obsidian URL
        obsidian_url = config_manager.generate_obsidian_url(project_name, note_path.name)
        typer.echo(f"🔗 Obsidian URL: {obsidian_url}")

        # Update or create database mapping
        existing_mapping = db.get_todoist_note_by_task_id(task_id)
        if existing_mapping:
            typer.echo("\n📝 Updating existing mapping...")
            existing_mapping.note_path = str(note_path)
            existing_mapping.obsidian_url = obsidian_url
            existing_mapping.todoist_project_id = task.project_id

            if db.update_todoist_note_mapping(existing_mapping):
                typer.echo("✅ Updated database mapping")
            else:
                typer.echo("❌ Failed to update database")
        else:
            typer.echo("\n📝 Creating new mapping...")
            mapping = TodoistNoteMapping(
                todoist_task_id=task_id,
                todoist_project_id=task.project_id,
                note_path=str(note_path),
                obsidian_url=obsidian_url,
            )

            if db.create_todoist_note_mapping(mapping):
                typer.echo("✅ Created database mapping")
            else:
                typer.echo("❌ Failed to create database mapping")

        # Add comment to Todoist
        try:
            typer.echo("\n💬 Adding Obsidian URL to Todoist task...")
            comment_text = f"📝 Obsidian note: [Open Note]({obsidian_url})"
            if api.create_comment(task_id, comment_text):
                typer.echo("✅ Added Obsidian URL as comment")
            else:
                typer.echo("⚠️  Failed to add comment (note still created)")
        except Exception as e:
            typer.echo(f"⚠️  Warning: Could not add comment: {e}")

        # Auto-start time tracking
        try:
            typer.echo("\n⏱️  Starting time tracking...")

            # Stop any active tracking first
            active = db.get_active_tracking()
            if active and active.todoist_task_id != task_id:
                stop_tracking_internal(active)
                typer.echo("   ⏹️  Stopped previous tracking")

            # Start new tracking
            bartib = BartibIntegration()
            bartib_project = build_bartib_project(project_name, client_name, tags=task.labels)

            bartib.start_tracking(description=task.content, project=bartib_project)

            db.create_tracking_record(
                todoist_task_id=task_id,
                project_name=bartib_project,
                task_name=task.content,
                started_at=datetime.now(),
            )

            api.create_comment(task_id, "⏱️ Started tracking time")
            if focus:
                start_focus_session(task.content)
            typer.echo("✅ Time tracking started")

        except Exception as e:
            typer.echo(f"⚠️  Warning: Could not start time tracking: {e}")

        # Open note if requested
        if open_note and config_manager.open_obsidian_note(project_name, note_path.name):
            typer.echo("📖 Opened note in Obsidian")

    except Exception as e:
        typer.echo(f"❌ Error: {e}")
        raise typer.Exit(1) from None


# ============================================================================
# PROJECT COMMANDS
# ============================================================================


@project_app.command("list")
def project_list(
    source: str = typer.Option("all", "--source", "-s", help="Source: todoist, obsidian, or all"),
):
    """List projects from Todoist and/or Obsidian."""
    has_todoist = bool(config_manager.get_todoist_token())
    has_obsidian = bool(config_manager.get_obsidian_vault_path())

    if source == "todoist" and not has_todoist:
        typer.echo("❌ Todoist not configured. Run 'taskbridge config todoist' first.")
        raise typer.Exit(1) from None

    if source == "obsidian" and not has_obsidian:
        typer.echo("❌ Obsidian not configured. Run 'taskbridge config obsidian' first.")
        raise typer.Exit(1) from None

    try:
        # Todoist projects
        if source in ("all", "todoist") and has_todoist:
            api = TodoistAPI()
            projects = api.get_projects()

            if projects:
                typer.echo(f"\n📝 Todoist Projects ({len(projects)}):")
                typer.echo("=" * 70)

                for project in projects:
                    typer.echo(f"📁 {project.name}")
                    typer.echo(f"   ID: {project.id}")
                    if project.parent_id:
                        typer.echo(f"   Parent: {project.parent_id}")
                    typer.echo(f"   Color: {project.color}")
                    if project.is_favorite:
                        typer.echo("   ⭐ Favorite")
                    typer.echo(f"   URL: {project.url}")
                    typer.echo()

        # Obsidian projects
        if source in ("all", "obsidian") and has_obsidian:
            projects = config_manager.get_obsidian_projects()

            if projects:
                typer.echo(f"\n📖 Obsidian Projects ({len(projects)}):")
                typer.echo("=" * 70)

                vault_path = config_manager.get_obsidian_vault_path()
                for project in projects:
                    project_path = Path(vault_path) / "10 Projects" / project
                    md_files = list(project_path.glob("*.md"))

                    typer.echo(f"📁 {project}")
                    typer.echo(f"   Path: {project_path}")
                    typer.echo(f"   Notes: {len(md_files)}")
                    typer.echo()

    except Exception as e:
        typer.echo(f"❌ Error: {e}")
        raise typer.Exit(1) from None


@project_app.command("create")
def project_create(
    name: str | None = typer.Option(None, "--name", "-n", help="Project name"),
    client: str | None = typer.Option(None, "--client", "-c", help="Client name"),
):
    """Create a project in both Todoist and Obsidian."""
    if not config_manager.get_todoist_token():
        typer.echo("❌ Todoist not configured. Run 'taskbridge config todoist' first.")
        raise typer.Exit(1) from None

    if not config_manager.get_obsidian_vault_path():
        typer.echo("❌ Obsidian not configured. Run 'taskbridge config obsidian' first.")
        raise typer.Exit(1) from None

    try:
        api = TodoistAPI()

        # Get project details interactively if not provided
        if not name:
            name = typer.prompt("Enter project name")

        if not client:
            client = typer.prompt("Enter client name (optional, press Enter to skip)", default="")

        # Create in Todoist
        typer.echo(f"\n📝 Creating project '{name}' in Todoist...")
        todoist_project = api.create_project(name=name)
        typer.echo(f"✅ Created Todoist project (ID: {todoist_project.id})")

        # Create Obsidian folder
        typer.echo("\n📁 Creating folder in Obsidian...")
        project_dir = config_manager.create_project_directory(name)
        typer.echo(f"✅ Created folder: {project_dir}")

        # Open project in Obsidian
        vault_name = config_manager.get_obsidian_vault_name()
        encoded_project = urllib.parse.quote(name)
        obsidian_url = (
            f"obsidian://open?vault={vault_name}&file=10%20Projects%2F{encoded_project}%2F"
        )

        typer.echo("\n📖 Opening project in Obsidian...")
        typer.echo("💡 Use your Obsidian template to create the project overview note")
        subprocess.run(["open", obsidian_url])

        # Save mapping
        config_manager.set_todoist_project_mapping(todoist_project.id, client, name)
        typer.echo("✅ Saved project mapping")

        # Display summary
        typer.echo("\n" + "=" * 60)
        typer.echo("🎉 Project created successfully!")
        typer.echo(f"   📝 Name: {name}")
        if client:
            typer.echo(f"   👤 Client: {client}")
        typer.echo(f"   🔗 Todoist: {todoist_project.url}")
        typer.echo(f"   📁 Obsidian: {project_dir}")
        typer.echo("=" * 60)

    except Exception as e:
        typer.echo(f"❌ Error: {e}")
        raise typer.Exit(1) from None


@project_app.command("archive")
def project_archive(
    name_or_id: str,
    source: str = typer.Option("todoist", "--source", "-s", help="Source: todoist or obsidian"),
):
    """Archive a project."""
    if source == "todoist":
        if not config_manager.get_todoist_token():
            typer.echo("❌ Todoist not configured. Run 'taskbridge config todoist' first.")
            raise typer.Exit(1) from None

        try:
            api = TodoistAPI()

            # Try to use as ID first, otherwise search by name
            project_id = name_or_id
            if not name_or_id.isdigit():
                projects = api.get_projects()
                matching = [p for p in projects if p.name.lower() == name_or_id.lower()]
                if not matching:
                    typer.echo(f"❌ No project found with name: {name_or_id}")
                    raise typer.Exit(1) from None
                if len(matching) > 1:
                    typer.echo(f"❌ Multiple projects found with name: {name_or_id}")
                    for p in matching:
                        typer.echo(f"   - {p.name} (ID: {p.id})")
                    raise typer.Exit(1) from None
                project_id = matching[0].id
                typer.echo(f"Found project: {matching[0].name} (ID: {project_id})")

            # Confirm before archiving
            if not typer.confirm(f"\n⚠️  Archive project {project_id}?"):
                typer.echo("Cancelled")
                return

            if api.archive_project(project_id):
                typer.echo(f"✅ Archived project: {project_id}")
            else:
                typer.echo(f"❌ Failed to archive project: {project_id}")

        except Exception as e:
            typer.echo(f"❌ Error: {e}")
            raise typer.Exit(1) from None

    elif source == "obsidian":
        if not config_manager.get_obsidian_vault_path():
            typer.echo("❌ Obsidian not configured. Run 'taskbridge config obsidian' first.")
            raise typer.Exit(1) from None

        try:
            # Confirm before archiving
            if not typer.confirm(f"\n⚠️  Archive project '{name_or_id}' (move to 40 Archive/)?"):
                typer.echo("Cancelled")
                return

            if config_manager.archive_obsidian_project(name_or_id):
                typer.echo(f"✅ Archived project: {name_or_id}")
                typer.echo(f"   Moved to: 40 Archive/{name_or_id}")
            else:
                typer.echo(f"❌ Failed to archive project: {name_or_id}")

        except ValueError as e:
            typer.echo(f"❌ Error: {e}")
            raise typer.Exit(1) from None
        except Exception as e:
            typer.echo(f"❌ Error: {e}")
            raise typer.Exit(1) from None
    else:
        typer.echo(f"❌ Invalid source: {source}. Use 'todoist' or 'obsidian'.")
        raise typer.Exit(1) from None


# ============================================================================
# MAPPING COMMANDS
# ============================================================================


@map_app.command("list")
def map_list(
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum mappings to display"),
    check_files: bool = typer.Option(
        False, "--check-files", "-c", help="Check if note files exist"
    ),
):
    """List all task-to-note mappings."""
    try:
        mappings = db.get_all_todoist_mappings()

        if not mappings:
            typer.echo("No task mappings found.")
            return

        # Limit results
        display_mappings = mappings[:limit]

        typer.echo(f"\n📋 Task Mappings ({len(display_mappings)} of {len(mappings)} total):")
        typer.echo("=" * 80)

        # Optionally get task names from Todoist
        api = None
        if config_manager.get_todoist_token():
            api = TodoistAPI()

        for i, mapping in enumerate(display_mappings, 1):
            typer.echo(f"\n{i}. Task ID: {mapping.todoist_task_id}")

            # Try to get task name
            if api:
                try:
                    task = api.get_task(mapping.todoist_task_id)
                    if task:
                        typer.echo(f"   Title: {task.content}")
                        project = api.get_project(task.project_id)
                        typer.echo(f"   Current Project: {project.name if project else 'Unknown'}")
                except Exception:
                    typer.echo("   Title: (could not fetch)")

            typer.echo(f"   Mapped Project ID: {mapping.todoist_project_id}")
            typer.echo(f"   Note: {Path(mapping.note_path).name}")

            if check_files:
                exists = Path(mapping.note_path).exists()
                typer.echo(f"   File exists: {'✅' if exists else '❌'}")

            typer.echo(f"   Created: {mapping.created_at}")

        if len(mappings) > limit:
            typer.echo(f"\n... and {len(mappings) - limit} more. Use --limit to show more.")

    except Exception as e:
        typer.echo(f"❌ Error: {e}")
        raise typer.Exit(1) from None


@map_app.command("show")
def map_show(task_id: str):
    """Show mapping details for a task (alias for 'task show')."""
    # Just call task_show
    task_show(task_id)


@map_app.command("update")
def map_update(
    task_id: str,
    sync_project: bool = typer.Option(
        True, "--sync-project/--no-sync-project", help="Update project ID from Todoist"
    ),
):
    """Update the database mapping for a task (useful when project changes)."""
    if not config_manager.get_todoist_token():
        typer.echo("❌ Todoist not configured. Run 'taskbridge config todoist' first.")
        raise typer.Exit(1) from None

    try:
        api = TodoistAPI()

        # Get current mapping
        mapping = db.get_todoist_note_by_task_id(task_id)
        if not mapping:
            typer.echo(f"❌ No mapping found for task ID: {task_id}")
            raise typer.Exit(1) from None

        task = api.get_task(task_id)
        if not task:
            typer.echo(f"❌ Task {task_id} not found in Todoist")
            raise typer.Exit(1) from None

        typer.echo(f"Task: {task.content}")
        typer.echo(f"Current mapping project ID: {mapping.todoist_project_id}")

        current_project = api.get_project(task.project_id)
        current_project_name = current_project.name if current_project else "Unknown"
        typer.echo(f"Current Todoist project: {current_project_name} (ID: {task.project_id})")

        if sync_project:
            if task.project_id == mapping.todoist_project_id:
                typer.echo("✅ Project IDs already match, nothing to update")
                return

            mapping.todoist_project_id = task.project_id

            if db.update_todoist_note_mapping(mapping):
                typer.echo(f"✅ Updated project ID to: {task.project_id}")

                # Verify
                updated = db.get_todoist_note_by_task_id(task_id)
                if updated:
                    typer.echo(f"✅ Verified new project ID: {updated.todoist_project_id}")
            else:
                typer.echo("❌ Failed to update mapping")
                raise typer.Exit(1) from None

    except Exception as e:
        typer.echo(f"❌ Error: {e}")
        raise typer.Exit(1) from None


# ============================================================================
# SYNC COMMANDS
# ============================================================================


@sync_app.command("notes")
def sync_notes(
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Preview without creating notes"),
    label: str | None = typer.Option(None, "--label", "-l", help="Override sync label from config"),
):
    """Sync Todoist tasks with sync label to Obsidian notes."""
    if not config_manager.get_todoist_token():
        typer.echo("❌ Todoist not configured. Run 'taskbridge config todoist' first.")
        raise typer.Exit(1) from None

    if not config_manager.get_obsidian_vault_path():
        typer.echo("❌ Obsidian not configured. Run 'taskbridge config obsidian' first.")
        raise typer.Exit(1) from None

    try:
        api = TodoistAPI()

        # Get sync label
        sync_label = label or config_manager.get_todoist_sync_label()
        typer.echo(f"🔍 Searching for tasks with label: {sync_label}")

        # Fetch tasks with the label
        tasks = api.get_tasks(label=sync_label)
        typer.echo(f"Found {len(tasks)} task(s)")

        if not tasks:
            typer.echo("No tasks found to sync")
            return

        # Get existing mappings to avoid duplicates
        existing_mappings = {m.todoist_task_id for m in db.get_all_todoist_mappings()}

        # Filter out already synced tasks
        new_tasks = [t for t in tasks if t.id not in existing_mappings]
        typer.echo(f"New tasks to sync: {len(new_tasks)}")
        typer.echo(f"Already synced: {len(tasks) - len(new_tasks)}")

        if not new_tasks:
            typer.echo("✅ All tasks already have notes")
            return

        if dry_run:
            typer.echo("\n[DRY RUN] Would create notes for:")
            typer.echo("-" * 60)
            for task in new_tasks:
                project = api.get_project(task.project_id)
                typer.echo(f"✅ {task.content}")
                typer.echo(f"   Project: {project.name if project else 'Unknown'}")
                typer.echo(f"   Labels: {', '.join(task.labels)}")
                typer.echo()
            return

        # Confirm before proceeding
        if not typer.confirm(f"\nCreate notes for {len(new_tasks)} tasks?"):
            typer.echo("Cancelled")
            return

        created_count = 0
        failed_count = 0

        for task in new_tasks:
            try:
                # Get project mapping
                project_mapping = config_manager.get_todoist_project_mappings().get(task.project_id)
                if not project_mapping:
                    project = api.get_project(task.project_id)
                    project_name = project.name if project else "Todoist"
                    client_name = ""
                else:
                    project_name = project_mapping["folder"]
                    client_name = project_mapping.get("client", "")

                # Create note
                note_path = config_manager.create_task_note(
                    project_name=project_name,
                    task_title=task.content,
                    client=client_name,
                    status="backlog",
                    tags=task.labels,
                )

                # Generate URL
                obsidian_url = config_manager.generate_obsidian_url(project_name, note_path.name)

                # Save mapping
                mapping = TodoistNoteMapping(
                    todoist_task_id=task.id,
                    todoist_project_id=task.project_id,
                    note_path=str(note_path),
                    obsidian_url=obsidian_url,
                )
                db.create_todoist_note_mapping(mapping)

                # Add comment
                comment_text = f"📝 Obsidian note: [Open Note]({obsidian_url})"
                api.create_comment(task.id, comment_text)

                created_count += 1
                typer.echo(f"✅ {task.content}")

            except Exception as e:
                failed_count += 1
                typer.echo(f"❌ Failed: {task.content} - {e}")

        # Summary
        typer.echo("\n" + "=" * 60)
        typer.echo(f"✅ Created: {created_count}")
        typer.echo(f"❌ Failed: {failed_count}")
        typer.echo(f"📋 Total: {len(new_tasks)}")

    except Exception as e:
        typer.echo(f"❌ Error: {e}")
        raise typer.Exit(1) from None


@sync_app.command("projects")
def sync_projects(
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Preview without making changes"),
):
    """Sync projects across Todoist and Obsidian."""
    has_todoist = bool(config_manager.get_todoist_token())
    has_obsidian = bool(config_manager.get_obsidian_vault_path())

    if not (has_todoist or has_obsidian):
        typer.echo("❌ Neither Todoist nor Obsidian is configured.")
        typer.echo("   Run 'taskbridge config todoist' or 'taskbridge config obsidian'")
        raise typer.Exit(1) from None

    try:
        # Collect projects from all sources
        all_projects = {}

        # Get Todoist projects
        if has_todoist:
            api = TodoistAPI()
            todoist_projects = api.get_projects()
            typer.echo(f"📥 Found {len(todoist_projects)} Todoist projects")

            for proj in todoist_projects:
                # Skip inbox and team projects
                if proj.is_inbox_project or proj.is_team_inbox:
                    continue

                all_projects[proj.name] = {
                    "todoist": True,
                    "obsidian": False,
                    "todoist_obj": proj,
                }

        # Get Obsidian projects
        if has_obsidian:
            obsidian_projects = config_manager.get_obsidian_projects()
            typer.echo(f"📥 Found {len(obsidian_projects)} Obsidian projects")

            for proj_name in obsidian_projects:
                if proj_name in all_projects:
                    all_projects[proj_name]["obsidian"] = True
                else:
                    all_projects[proj_name] = {
                        "todoist": False,
                        "obsidian": True,
                    }

        # Find projects that need syncing
        projects_to_sync = []
        for name, sources in all_projects.items():
            needs_sync = False
            if has_todoist and not sources["todoist"]:
                needs_sync = True
            if has_obsidian and not sources["obsidian"]:
                needs_sync = True

            if needs_sync:
                projects_to_sync.append((name, sources))

        if not projects_to_sync:
            typer.echo("\n✅ All projects are synced across all systems")
            return

        # Display sync plan
        typer.echo(f"\n🔄 Found {len(projects_to_sync)} project(s) to sync:")
        typer.echo("=" * 70)

        for name, sources in projects_to_sync:
            typer.echo(f"📁 {name}")
            status_parts = []
            if sources["todoist"]:
                status_parts.append("✓ Todoist")
            else:
                status_parts.append("✗ Todoist")

            if sources["obsidian"]:
                status_parts.append("✓ Obsidian")
            else:
                status_parts.append("✗ Obsidian")

            typer.echo(f"   {' | '.join(status_parts)}")
            typer.echo()

        if dry_run:
            typer.echo("[DRY RUN] No changes made")
            return

        if not typer.confirm(f"\nSync {len(projects_to_sync)} projects?"):
            typer.echo("Cancelled")
            return

        # Perform sync
        synced_count = 0
        failed_count = 0

        for name, sources in projects_to_sync:
            try:
                # Create in Todoist if needed
                if has_todoist and not sources["todoist"]:
                    api = TodoistAPI()
                    new_proj = api.create_project(name=name)
                    sources["todoist_obj"] = new_proj
                    typer.echo(f"✅ Created in Todoist: {name}")

                # Create in Obsidian if needed
                if has_obsidian and not sources["obsidian"]:
                    config_manager.create_project_directory(name)
                    typer.echo(f"✅ Created in Obsidian: {name}")

                synced_count += 1

            except Exception as e:
                failed_count += 1
                typer.echo(f"❌ Failed: {name} - {e}")

        # Summary
        typer.echo("\n" + "=" * 70)
        typer.echo("📊 Sync Summary:")
        typer.echo(f"   ✅ Synced: {synced_count}")
        typer.echo(f"   ❌ Failed: {failed_count}")
        typer.echo(f"   📋 Total: {len(projects_to_sync)}")

    except Exception as e:
        typer.echo(f"❌ Error: {e}")
        raise typer.Exit(1) from None


# ============================================================================
# TIME TRACKING HELPER FUNCTIONS
# ============================================================================


def start_focus_session(title: str = "") -> None:
    """Start a Raycast Focus session, copying title to clipboard. Best-effort, never raises."""
    with contextlib.suppress(Exception):
        if title:
            subprocess.run(["pbcopy"], input=title.encode(), timeout=5)
        subprocess.run(
            ["open", "raycast://extensions/raycast/raycast-focus/start-focus-session"],
            capture_output=True,
            timeout=5,
        )


def sanitize_project_name(name: str) -> str:
    """Sanitize project name (remove emojis, special chars, normalize)."""
    import re

    # Remove emojis and special characters, keep alphanumeric and spaces
    cleaned = re.sub(r"[^\w\s-]", "", name)
    # Replace spaces with hyphens, strip
    cleaned = cleaned.strip().replace(" ", "-")
    # Remove multiple consecutive hyphens
    cleaned = re.sub(r"-+", "-", cleaned)
    # Remove leading/trailing hyphens
    cleaned = cleaned.strip("-")

    # If empty after cleaning, use a default
    return cleaned if cleaned else "general"


def resolve_project_info(project_id: str, api: "TodoistAPI") -> tuple[str, str]:
    """Return (project_name, client_name) for a Todoist project.

    Manual config mappings take precedence. Otherwise the top-level ancestor
    in the project hierarchy becomes the client and the direct project becomes
    the folder name.
    """
    manual = config_manager.get_todoist_project_mappings().get(project_id)
    if manual:
        return manual["folder"], manual.get("client", "")

    project = api.get_project(project_id)
    if not project:
        return "Unknown", ""

    if not project.parent_id:
        return project.name, ""

    # Walk up to the root ancestor — that becomes the client
    current = project
    client_name = project.name
    while current.parent_id:
        parent = api.get_project(current.parent_id)
        if not parent:
            break
        client_name = parent.name
        current = parent

    return project.name, client_name


def build_bartib_project(project: str, client: str = "", tags: list[str] | None = None) -> str:
    """Build bartib project name encoding client, project, and tags.

    Format: "client::project::tag1,tag2" (client and tags are optional)

    Args:
        project: Project name
        client: Client name (optional)
        tags: Task labels/tags (optional)

    Returns:
        Bartib project string, e.g. "acme-corp::my-project::work,urgent"
    """
    parts = []
    if client:
        parts.append(sanitize_project_name(client))
    parts.append(sanitize_project_name(project))
    if tags:
        parts.append(",".join(sanitize_project_name(t) for t in tags))
    return "::".join(parts)


def format_duration(seconds: int) -> str:
    """Format seconds as human-readable duration."""
    if seconds == 0:
        return "0m"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def parse_project_segments(project_name: str) -> tuple[str, str]:
    """Split a bartib project string into (client, project).

    Tags (third segment onward) are ignored for grouping purposes.
    Projects with no '::' separator are returned as ('(other)', project_name).
    """
    parts = project_name.split("::")
    if len(parts) == 1:
        return "(other)", parts[0]
    return parts[0], parts[1]


@dataclass
class ReportEntry:
    """A single time-tracked entry for the report."""

    client: str
    project: str
    description: str
    seconds: int


def build_report_entries(records: list[TaskTimeTracking], now: datetime) -> list[ReportEntry]:
    """Convert tracking records into flat report entries, crediting active sessions to now."""
    entries = []
    for record in records:
        start = record.started_at
        if start is None:
            continue
        end = record.stopped_at if record.stopped_at else now
        seconds = max(0, int((end - start).total_seconds()))
        if seconds == 0:
            continue
        client, project = parse_project_segments(record.project_name)
        entries.append(
            ReportEntry(
                client=client,
                project=project,
                description=record.task_name,
                seconds=seconds,
            )
        )
    return entries


def format_report(entries: list[ReportEntry]) -> str:
    """Format report entries into a hierarchical text report."""
    if not entries:
        return "No tracked time found for this period."

    total_seconds = sum(e.seconds for e in entries)

    # Aggregate: client → project → list of (description, seconds)
    from collections import defaultdict

    client_seconds: dict[str, int] = defaultdict(int)
    project_seconds: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    project_descriptions: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

    for entry in entries:
        client_seconds[entry.client] += entry.seconds
        project_seconds[entry.client][entry.project] += entry.seconds
        if entry.description not in project_descriptions[entry.client][entry.project]:
            project_descriptions[entry.client][entry.project].append(entry.description)

    total_hours = total_seconds / 3600
    lines = [f"Total: {total_hours:.1f}h\n"]

    for client in sorted(client_seconds, key=lambda c: client_seconds[c], reverse=True):
        c_secs = client_seconds[client]
        c_frac = c_secs / total_seconds
        lines.append(f"{client}  {c_frac:.2f}")

        for project in sorted(
            project_seconds[client], key=lambda p: project_seconds[client][p], reverse=True
        ):
            p_secs = project_seconds[client][project]
            p_frac = p_secs / c_secs
            lines.append(f"  - {project}: {p_frac:.2f}")
            for desc in project_descriptions[client][project]:
                lines.append(f"    - {desc}")

    return "\n".join(lines)


def find_workday_gaps(
    records: list[TaskTimeTracking],
    work_start: datetime,
    work_end: datetime,
    now: datetime,
    min_minutes: int = 15,
) -> list[tuple[datetime, datetime]]:
    """Return untracked intervals within the work window.

    Args:
        records: Tracked sessions for the day (from parse_bartib_file).
        work_start: Beginning of the work window (naive datetime).
        work_end: End of the work window (naive datetime).
        now: Current time (used to cap active sessions without a stop time).
        min_minutes: Gaps shorter than this are ignored.

    Returns:
        List of (gap_start, gap_end) pairs sorted chronologically.
    """
    from datetime import timedelta

    intervals: list[tuple[datetime, datetime]] = []
    for r in records:
        if r.started_at is None:
            continue
        start = r.started_at
        end = r.stopped_at if r.stopped_at else now
        # Clamp to work window
        start = max(start, work_start)
        end = min(end, work_end)
        if start < end:
            intervals.append((start, end))

    intervals.sort(key=lambda x: x[0])

    # Merge overlapping intervals
    merged: list[list[datetime]] = []
    for s, e in intervals:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])

    threshold = timedelta(minutes=min_minutes)
    gaps: list[tuple[datetime, datetime]] = []
    cursor = work_start
    for s, e in merged:
        if s - cursor >= threshold:
            gaps.append((cursor, s))
        cursor = max(cursor, e)
    if work_end - cursor >= threshold:
        gaps.append((cursor, work_end))

    return gaps


def split_gap_by_events(
    gap_start: datetime,
    gap_end: datetime,
    events: list,
) -> list[tuple[datetime, datetime, str | None]]:
    """Divide a gap into sub-blocks aligned with calendar event boundaries.

    Each returned tuple is (block_start, block_end, event_title_or_None).
    Blocks not covered by any event have title=None.

    Args:
        gap_start: Start of the untracked gap.
        gap_end: End of the untracked gap.
        events: List of CalendarEvent objects that may overlap the gap.
    """
    # Collect breakpoints from events that overlap the gap
    breakpoints: set[datetime] = {gap_start, gap_end}
    overlapping = []
    for ev in events:
        ev_s = max(ev.start, gap_start)
        ev_e = min(ev.end, gap_end)
        if ev_s < ev_e:
            breakpoints.add(ev_s)
            breakpoints.add(ev_e)
            overlapping.append(ev)

    sorted_pts = sorted(breakpoints)
    blocks: list[tuple[datetime, datetime, str | None]] = []
    for i in range(len(sorted_pts) - 1):
        b_start = sorted_pts[i]
        b_end = sorted_pts[i + 1]
        mid = b_start + (b_end - b_start) / 2
        title = None
        for ev in overlapping:
            if ev.start <= mid < ev.end:
                title = ev.title
                break
        blocks.append((b_start, b_end, title))

    return blocks


def get_recent_projects(bartib_file: str, limit: int = 20) -> list[str]:
    """Return the most recently used distinct bartib project names.

    Args:
        bartib_file: Path to the bartib activity file.
        limit: Maximum number of distinct project names to return.
    """
    projects: list[str] = []
    seen: set[str] = set()
    try:
        with open(bartib_file) as f:
            lines = f.readlines()
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            parts = line.split(" | ", 2)
            if len(parts) == 3:
                project = parts[1]
                if project not in seen:
                    seen.add(project)
                    projects.append(project)
                    if len(projects) >= limit:
                        break
    except OSError:
        pass
    return projects


def append_bartib_entry(project: str, description: str, start: datetime, end: datetime) -> None:
    """Append a completed time entry directly to the bartib file.

    Args:
        project: Bartib project string (e.g. "CHTC::htcondor").
        description: Activity description.
        start: Entry start time.
        end: Entry end time.

    Raises:
        RuntimeError: If BARTIB_FILE env var is not set.
    """
    import os

    bartib_file = os.environ.get("BARTIB_FILE")
    if not bartib_file:
        raise RuntimeError(
            "BARTIB_FILE environment variable is not set. "
            "Set it to the path of your bartib activity log."
        )
    start_str = start.strftime("%Y-%m-%d %H:%M")
    end_str = end.strftime("%Y-%m-%d %H:%M")
    line = f"{start_str} - {end_str} | {project} | {description}\n"
    with open(bartib_file, "a") as f:
        f.write(line)


def parse_bartib_file(from_dt: datetime, to_dt: datetime) -> list[TaskTimeTracking]:
    """Parse the bartib activity file and return records whose start time is in [from_dt, to_dt).

    Reads the file path from the BARTIB_FILE environment variable.
    Raises RuntimeError if BARTIB_FILE is not set.
    """
    import os

    bartib_file = os.environ.get("BARTIB_FILE")
    if not bartib_file:
        raise RuntimeError(
            "BARTIB_FILE environment variable is not set. "
            "Set it to the path of your bartib activity log."
        )

    records: list[TaskTimeTracking] = []
    with open(bartib_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(" | ", 2)
            if len(parts) != 3:
                continue
            time_part, project_name, task_name = parts[0], parts[1], parts[2]

            # Active session: "YYYY-MM-DD HH:MM"
            # Completed session: "YYYY-MM-DD HH:MM - YYYY-MM-DD HH:MM"
            if " - " in time_part:
                start_str, stop_str = time_part.split(" - ", 1)
                started_at = datetime.strptime(start_str.strip(), "%Y-%m-%d %H:%M")
                stopped_at = datetime.strptime(stop_str.strip(), "%Y-%m-%d %H:%M")
            else:
                started_at = datetime.strptime(time_part.strip(), "%Y-%m-%d %H:%M")
                stopped_at = None

            if started_at < from_dt or started_at >= to_dt:
                continue

            records.append(
                TaskTimeTracking(
                    project_name=project_name,
                    task_name=task_name,
                    started_at=started_at,
                    stopped_at=stopped_at,
                )
            )
    return records


def stop_tracking_internal(tracking: TaskTimeTracking) -> tuple[bool, int]:
    """Stop bartib tracking and update records.

    Returns:
        tuple[bool, int]: (success, duration_in_seconds)
    """
    try:
        bartib = BartibIntegration()
        bartib.stop_tracking()

        # Calculate duration from started_at stored in database
        stopped_at = datetime.now()
        duration = 0
        if tracking.started_at:
            duration = int((stopped_at - tracking.started_at).total_seconds())

        # Update database
        db.update_tracking_record(tracking, stopped_at=stopped_at)

        # Add comment to Todoist if linked (not a synthetic meeting ID)
        is_meeting = tracking.todoist_task_id.startswith("meeting:")
        if tracking.todoist_task_id and not is_meeting and duration > 0:
            try:
                api = TodoistAPI()
                formatted_time = format_duration(duration)
                api.create_comment(tracking.todoist_task_id, f"⏱️ Tracked {formatted_time}")
            except Exception:
                pass  # Don't fail if comment fails

        return True, duration

    except Exception:
        return False, 0


# ============================================================================
# TIME TRACKING COMMANDS
# ============================================================================


@time_app.command("start")
def time_start(
    task: str | None = typer.Option(None, "--task", "-t", help="Todoist task ID to link"),
    note: str | None = typer.Option(None, "--note", "-n", help="Note/description for tracking"),
    focus: bool = typer.Option(True, "--focus/--no-focus", help="Start Raycast Focus session"),
):
    """Start time tracking, optionally linked to a Todoist task."""
    try:
        bartib = BartibIntegration()

        # Check for active tracking
        active = db.get_active_tracking()
        if active:
            # Auto-stop previous tracking
            if active.todoist_task_id != task:
                typer.echo(
                    f"⏹️  Stopping previous tracking: {active.task_name} ({active.project_name})"
                )
                success, duration = stop_tracking_internal(active)
                if success:
                    typer.echo(f"   ✅ Tracked {format_duration(duration)}")
            else:
                typer.echo("⚠️  Already tracking this task")
                return

        # If task ID provided, link to Todoist
        if task:
            if not config_manager.get_todoist_token():
                typer.echo("❌ Todoist not configured. Run 'taskbridge config todoist' first.")
                raise typer.Exit(1) from None

            api = TodoistAPI()
            todoist_task = api.get_task(task)

            if not todoist_task:
                typer.echo(f"❌ Task {task} not found in Todoist")
                raise typer.Exit(1) from None

            # Get project name (manual mapping → hierarchy inference)
            project_name, client_name = resolve_project_info(todoist_task.project_id, api)
            bartib_project = build_bartib_project(
                project_name, client_name, tags=todoist_task.labels
            )

            # Use task content as description if not provided
            if not note:
                note = todoist_task.content

            # Start bartib tracking
            bartib.start_tracking(description=note, project=bartib_project)

            # Save to database
            db.create_tracking_record(
                todoist_task_id=task,
                project_name=bartib_project,
                task_name=todoist_task.content,
                started_at=datetime.now(),
            )

            # Add comment to Todoist
            with contextlib.suppress(Exception):
                api.create_comment(task, "⏱️ Started tracking time")

            if focus:
                start_focus_session(todoist_task.content)
            typer.echo(f"▶️  Started tracking: {todoist_task.content}")
            typer.echo(f"   📁 Project: {bartib_project}")
            typer.echo(f"   🔗 Task ID: {task}")

        else:
            # Generic tracking without Todoist link
            if not note:
                note = typer.prompt("What are you working on?")

            # Use a default project for generic tracking
            bartib.start_tracking(description=note, project="taskbridge")
            typer.echo(f"▶️  Started tracking: {note}")
            typer.echo("   ℹ️  Use --task to link to a Todoist task")

    except RuntimeError as e:
        typer.echo(f"❌ Bartib error: {e}")
        typer.echo("   Make sure bartib is installed: https://github.com/nikolassv/bartib")
        raise typer.Exit(1) from None
    except Exception as e:
        typer.echo(f"❌ Error: {e}")
        raise typer.Exit(1) from None


@time_app.command("stop")
def time_stop():
    """Stop active time tracking."""
    try:
        # Check for active tracking
        active = db.get_active_tracking()

        if not active:
            typer.echo("⚠️  No active tracking session")
            return

        typer.echo(f"⏹️  Stopping: {active.task_name} ({active.project_name})")

        # Stop tracking
        success, duration = stop_tracking_internal(active)

        if success:
            typer.echo(f"✅ Tracked {format_duration(duration)}")
            if active.todoist_task_id:
                typer.echo(f"   🔗 Linked to task: {active.todoist_task_id}")
        else:
            typer.echo("⚠️  Warning: Could not stop bartib tracking")

    except Exception as e:
        typer.echo(f"❌ Error: {e}")
        raise typer.Exit(1) from None


@time_app.command("list")
def time_list(
    project: str | None = typer.Option(None, "--project", "-p", help="Filter by project"),
    days: int = typer.Option(7, "--days", "-d", help="Number of days to show"),
):
    """List recent time tracking activities."""
    try:
        from datetime import timedelta

        bartib = BartibIntegration()

        if days == 1:
            output = bartib.list_activities(project=project, today=True)
        else:
            from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            output = bartib.list_activities(project=project, from_date=from_date)

        if not output.strip():
            typer.echo(f"No activities found in the last {days} days")
            return

        typer.echo(f"\n⏱️  Activities (last {days} days):")
        typer.echo(output)

    except RuntimeError as e:
        typer.echo(f"❌ Bartib error: {e}")
        raise typer.Exit(1) from None
    except Exception as e:
        typer.echo(f"❌ Error: {e}")
        raise typer.Exit(1) from None


@time_app.command("report")
def time_report(
    date: str | None = typer.Option(None, "--date", help="Report for a specific date (YYYY-MM-DD)"),
    from_date: str | None = typer.Option(None, "--from", help="Start date (YYYY-MM-DD)"),
    to_date: str | None = typer.Option(None, "--to", help="End date (YYYY-MM-DD, inclusive)"),
):
    """Daily summary report grouped by client and project."""
    from datetime import timedelta

    try:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if from_date or to_date:
            start = datetime.strptime(from_date, "%Y-%m-%d") if from_date else today
            end_day = datetime.strptime(to_date, "%Y-%m-%d") if to_date else today
        elif date:
            start = datetime.strptime(date, "%Y-%m-%d")
            end_day = start
        else:
            start = today
            end_day = today

        end = end_day + timedelta(days=1)  # exclusive upper bound
        label = (
            start.strftime("%Y-%m-%d")
            if start == end_day
            else (f"{start.strftime('%Y-%m-%d')} – {end_day.strftime('%Y-%m-%d')}")
        )

        records = parse_bartib_file(start, end)
        entries = build_report_entries(records, now=datetime.now())
        report = format_report(entries)

        typer.echo(f"Report: {label}\n")
        typer.echo(report)

    except (ValueError, RuntimeError) as e:
        typer.echo(f"❌ {e}")
        raise typer.Exit(1) from None


@time_app.command("fill")
def time_fill(
    date: str | None = typer.Option(
        None, "--date", help="Date to fill gaps for (YYYY-MM-DD, default: today)"
    ),
    work_start: str = typer.Option("08:00", "--start", help="Start of workday (HH:MM)"),
    work_end: str = typer.Option("16:00", "--end", help="End of workday (HH:MM)"),
    no_gcal: bool = typer.Option(False, "--no-gcal", help="Skip Google Calendar lookup"),
    min_gap: int = typer.Option(15, "--min-gap", help="Minimum gap size in minutes to fill"),
):
    """Interactively fill time tracking gaps, optionally using Google Calendar events."""
    import os
    from datetime import timedelta

    bartib_file = os.environ.get("BARTIB_FILE")
    if not bartib_file:
        typer.echo("❌ BARTIB_FILE environment variable is not set.")
        raise typer.Exit(1) from None

    # Resolve target date
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            typer.echo(f"❌ Invalid date format: {date} (expected YYYY-MM-DD)")
            raise typer.Exit(1) from None
    else:
        target_date = today

    # Parse work window
    try:
        ws_h, ws_m = (int(x) for x in work_start.split(":"))
        we_h, we_m = (int(x) for x in work_end.split(":"))
    except (ValueError, TypeError):
        typer.echo("❌ Invalid time format (expected HH:MM)")
        raise typer.Exit(1) from None

    window_start = target_date.replace(hour=ws_h, minute=ws_m, second=0, microsecond=0)
    window_end = target_date.replace(hour=we_h, minute=we_m, second=0, microsecond=0)
    now = datetime.now()

    typer.echo(
        f"\nFilling time gaps for {target_date.strftime('%Y-%m-%d')}  ({work_start} – {work_end})"
    )

    # Load tracked sessions for the day
    try:
        records = parse_bartib_file(window_start, window_start + timedelta(days=1))
    except RuntimeError as e:
        typer.echo(f"❌ {e}")
        raise typer.Exit(1) from None

    gaps = find_workday_gaps(records, window_start, window_end, now=now, min_minutes=min_gap)

    if not gaps:
        typer.echo("✅ No gaps found — workday appears fully tracked.")
        return

    total_gap_mins = sum(int((e - s).total_seconds() / 60) for s, e in gaps)
    typer.echo(
        f"Found {len(gaps)} gap(s) totalling {total_gap_mins // 60}h {total_gap_mins % 60}m\n"
    )

    # Optionally fetch calendar events
    cal_events: list = []
    gcal_creds = config_manager.get_gcal_credentials_path()
    if not no_gcal and gcal_creds:
        typer.echo("Fetching calendar events...")
        try:
            from taskbridge.gcal_integration import GoogleCalendarClient

            gcal = GoogleCalendarClient(
                credentials_path=gcal_creds,
                token_path=config_manager.get_gcal_token_path(),
            )
            cal_events = gcal.get_events(target_date, config_manager.get_gcal_calendar_id())
            typer.echo(f"Found {len(cal_events)} calendar event(s)\n")
        except Exception as e:
            typer.echo(f"⚠️  Could not fetch calendar events: {e}")
            typer.echo("   Continuing without calendar suggestions.\n")
    elif not no_gcal and not config_manager.get_gcal_credentials_path():
        typer.echo(
            "ℹ️  Google Calendar not configured. Run 'taskbridge config gcal' to set up.\n"
            "   Continuing without calendar suggestions.\n"
        )

    recent_projects = get_recent_projects(bartib_file)
    last_project: str | None = recent_projects[0] if recent_projects else None

    filled_count = 0
    for gap_idx, (gap_start_dt, gap_end_dt) in enumerate(gaps, 1):
        gap_mins = int((gap_end_dt - gap_start_dt).total_seconds() / 60)
        typer.echo(
            f"── Gap {gap_idx} of {len(gaps)} "
            f"({gap_start_dt.strftime('%H:%M')} – {gap_end_dt.strftime('%H:%M')}, "
            f"{gap_mins // 60}h {gap_mins % 60}m) {'─' * 20}"
        )

        # Find calendar events overlapping this gap
        overlapping = [ev for ev in cal_events if ev.start < gap_end_dt and ev.end > gap_start_dt]
        if overlapping:
            typer.echo("  Calendar events:")
            letters = "abcdefghijklmnopqrstuvwxyz"
            for i, ev in enumerate(overlapping):
                ev_s = max(ev.start, gap_start_dt)
                ev_e = min(ev.end, gap_end_dt)
                ev_mins = int((ev_e - ev_s).total_seconds() / 60)
                label = letters[i] if i < len(letters) else str(i + 1)
                typer.echo(
                    f"    {label}) {ev.title:<38} "
                    f"{ev.start.strftime('%H:%M')} – {ev.end.strftime('%H:%M')} "
                    f"({ev_mins}m)"
                )

        # Ask how to handle this gap
        if overlapping:
            typer.echo("\n  s) Split by calendar events   f) Fill as one block   k) Skip   q) Quit")
            choice = typer.prompt("  Choice", default="s").strip().lower()
        else:
            typer.echo("\n  f) Fill as one block   k) Skip   q) Quit")
            choice = typer.prompt("  Choice", default="f").strip().lower()

        if choice == "q":
            typer.echo("Quitting.")
            return
        if choice == "k":
            typer.echo("  Skipped.\n")
            continue

        # Build list of sub-blocks to fill
        if choice == "s" and overlapping:
            # Let the user pick which events to include in the split
            letters = "abcdefghijklmnopqrstuvwxyz"
            all_labels = [
                letters[i] if i < len(letters) else str(i + 1) for i in range(len(overlapping))
            ]
            raw_sel = (
                typer.prompt(
                    f"  Use events ({', '.join(all_labels)}) — enter letters or 'all'",
                    default="all",
                )
                .strip()
                .lower()
            )
            if raw_sel == "all":
                selected_events = overlapping
            else:
                chosen = {c.strip() for c in raw_sel.replace(",", " ").split()}
                selected_events = [
                    ev
                    for i, ev in enumerate(overlapping)
                    if (letters[i] if i < len(letters) else str(i + 1)) in chosen
                ]
            blocks = split_gap_by_events(gap_start_dt, gap_end_dt, selected_events)
        else:
            blocks = [(gap_start_dt, gap_end_dt, None)]

        typer.echo("")
        for b_start, b_end, suggested_title in blocks:
            b_mins = int((b_end - b_start).total_seconds() / 60)
            label = f'"{suggested_title}"' if suggested_title else "(no calendar event)"
            typer.echo(
                f"  [{b_start.strftime('%H:%M')} – {b_end.strftime('%H:%M')}]  {label}  ({b_mins}m)"
            )

            # Project selection
            if recent_projects:
                typer.echo("  Recent projects:")
                for i, p in enumerate(recent_projects, 1):
                    default_marker = "  ← default" if p == last_project else ""
                    typer.echo(f"    {i}) {p}{default_marker}")
                typer.echo("    (or type a project name / client::project)")

                default_hint = "1" if last_project == recent_projects[0] else ""
                raw = typer.prompt("  Project", default=default_hint).strip()
                if raw.isdigit():
                    idx = int(raw) - 1
                    if 0 <= idx < len(recent_projects):
                        project = recent_projects[idx]
                    else:
                        typer.echo("  Invalid selection, skipping block.")
                        continue
                elif raw:
                    project = raw
                else:
                    project = last_project or ""
            else:
                project = typer.prompt("  Project (client::project)").strip()

            if not project:
                typer.echo("  No project entered, skipping block.")
                continue

            # Description
            default_desc = suggested_title or ""
            description = typer.prompt("  Description", default=default_desc).strip()
            if not description:
                typer.echo("  No description entered, skipping block.")
                continue

            # Write to bartib
            try:
                append_bartib_entry(project, description, b_start, b_end)
                typer.echo(
                    f"  ✓ Added {b_start.strftime('%H:%M')} – {b_end.strftime('%H:%M')}  "
                    f"{project}  {description}"
                )
                last_project = project
                filled_count += 1
            except RuntimeError as e:
                typer.echo(f"  ❌ {e}")

        typer.echo("")

    typer.echo(f"Done. Added {filled_count} entr{'y' if filled_count == 1 else 'ies'}.")


@time_app.command("stats")
def time_stats(
    project: str | None = typer.Option(None, "--project", "-p", help="Filter by project"),
    period: str = typer.Option("week", "--period", help="Period: today, week, last_week"),
):
    """View time tracking report."""
    try:
        bartib = BartibIntegration()

        report = bartib.get_report(
            project=project,
            today=(period == "today"),
            current_week=(period == "week"),
            last_week=(period == "last_week"),
        )

        if not report.strip():
            typer.echo(f"No activities recorded for {period}")
            return

        typer.echo(f"\n📊 Time Report ({period}):")
        typer.echo(report)

    except RuntimeError as e:
        typer.echo(f"❌ Bartib error: {e}")
        raise typer.Exit(1) from None
    except Exception as e:
        typer.echo(f"❌ Error: {e}")
        raise typer.Exit(1) from None


# ============================================================================
# MEETING COMMANDS
# ============================================================================


@meeting_app.command("define")
def meeting_define(
    alias: str,
    description: str = typer.Option(..., "--description", "-d", help="Meeting description"),
    project: str = typer.Option("", "--project", "-p", help="Project context"),
    client: str = typer.Option("", "--client", "-c", help="Client context"),
    tags: str = typer.Option("", "--tags", "-t", help="Comma-separated tags"),
):
    """Define a recurring meeting template by alias."""
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    config_manager.set_meeting(
        alias=alias,
        description=description,
        project=project,
        client=client,
        tags=tag_list,
    )

    bartib_project = build_bartib_project(project or "meetings", client, tag_list)
    typer.echo(f"✅ Defined meeting '{alias}'")
    typer.echo(f"   Description: {description}")
    typer.echo(f"   Bartib project: {bartib_project}")
    typer.echo(f"   Start with: taskbridge meeting start {alias}")


@meeting_app.command("list")
def meeting_list():
    """List all defined recurring meeting templates."""
    meetings = config_manager.get_meetings()

    if not meetings:
        typer.echo("No recurring meetings defined.")
        typer.echo("   Use 'taskbridge meeting define <alias>' to add one.")
        return

    typer.echo(f"\n📅 Recurring Meetings ({len(meetings)}):")
    typer.echo("=" * 60)

    for alias, m in meetings.items():
        bartib_project = build_bartib_project(
            m.get("project") or "meetings", m.get("client", ""), m.get("tags", [])
        )
        typer.echo(f"\n  {alias}")
        typer.echo(f"    Description : {m['description']}")
        typer.echo(f"    Bartib      : {bartib_project}")
        if m.get("tags"):
            typer.echo(f"    Tags        : {', '.join(m['tags'])}")

    typer.echo()


@meeting_app.command("undefine")
def meeting_undefine(alias: str):
    """Remove a recurring meeting definition."""
    if config_manager.delete_meeting(alias):
        typer.echo(f"✅ Removed meeting '{alias}'")
    else:
        typer.echo(f"❌ No meeting named '{alias}'")
        raise typer.Exit(1) from None


@meeting_app.command("start")
def meeting_start(
    name: str,
    project: str = typer.Option("", "--project", "-p", help="Project (overrides definition)"),
    client: str = typer.Option("", "--client", "-c", help="Client (overrides definition)"),
    tags: str = typer.Option("", "--tags", "-t", help="Comma-separated tags (overrides)"),
    focus: bool = typer.Option(True, "--focus/--no-focus", help="Start Raycast Focus session"),
):
    """Start tracking a meeting. NAME is an alias or an ad-hoc description."""
    try:
        bartib = BartibIntegration()

        # Resolve alias or treat name as ad-hoc description
        definition = config_manager.get_meetings().get(name)
        if definition:
            description = definition["description"]
            resolved_project = project or definition.get("project") or "meetings"
            resolved_client = client or definition.get("client", "")
            tag_str = tags or ",".join(definition.get("tags", []))
        else:
            description = name
            resolved_project = project or "meetings"
            resolved_client = client
            tag_str = tags

        tag_list = [t.strip() for t in tag_str.split(",") if t.strip()] if tag_str else []
        if "meeting" not in tag_list:
            tag_list.append("meeting")
        bartib_project = build_bartib_project(resolved_project, resolved_client, tag_list)

        # Stop any active tracking first
        active = db.get_active_tracking()
        if active:
            typer.echo(f"⏹️  Stopping: {active.task_name} ({active.project_name})")
            success, duration = stop_tracking_internal(active)
            if success:
                typer.echo(f"   ✅ Tracked {format_duration(duration)}")

        # Start bartib
        bartib.start_tracking(description=description, project=bartib_project)

        # Save to DB with a synthetic task ID so stop/list still work
        slug = name.lower().replace(" ", "-")
        db.create_tracking_record(
            todoist_task_id=f"meeting:{slug}",
            project_name=bartib_project,
            task_name=description,
            started_at=datetime.now(),
        )

        if focus:
            start_focus_session(description)
        typer.echo(f"▶️  Meeting: {description}")
        typer.echo(f"   📁 {bartib_project}")
        if definition:
            typer.echo(f"   (recurring: {name})")

    except RuntimeError as e:
        typer.echo(f"❌ Bartib error: {e}")
        raise typer.Exit(1) from None
    except Exception as e:
        typer.echo(f"❌ Error: {e}")
        raise typer.Exit(1) from None


if __name__ == "__main__":
    app()
