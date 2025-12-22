"""Main CLI entry point for TaskBridge."""

import subprocess
import urllib.parse
from pathlib import Path

import typer

from .config import config as config_manager
from .database import TodoistNoteMapping, db
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

app.add_typer(config_app, name="config")
app.add_typer(task_app, name="task")
app.add_typer(project_app, name="project")
app.add_typer(map_app, name="map")
app.add_typer(sync_app, name="sync")


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


@task_app.command("note")
def task_note(
    task_id: str,
    open_note: bool = typer.Option(True, "--open/--no-open", help="Open note after creation"),
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

        # Get project info
        project = api.get_project(task.project_id)
        project_name_todoist = project.name if project else "Todoist"

        # Check for project mapping
        project_mapping = config_manager.get_todoist_project_mappings().get(task.project_id)
        if project_mapping:
            project_name = project_mapping["folder"]
            client_name = project_mapping.get("client", "")
            typer.echo(f"Using mapped project: {project_name}")
        else:
            project_name = project_name_todoist
            client_name = ""
            typer.echo(f"Using Todoist project name: {project_name}")

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


if __name__ == "__main__":
    app()
