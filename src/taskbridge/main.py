"""Main CLI entry point for TaskBridge."""

import typer

from .config import config as config_manager
from .database import db
from .taskwarrior_provider import TaskwarriorProvider

app = typer.Typer(
    name="taskbridge",
    help="TaskBridge - Integration hub for Todoist, Taskwarrior, and Obsidian",
    add_completion=False,
)


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
    except ValueError as e:
        typer.echo(f"❌ {e}")
        raise typer.Exit(1)


@app.command("config-taskwarrior")
def config_taskwarrior():
    """Configure Taskwarrior integration settings."""
    typer.echo("Taskwarrior Configuration")
    typer.echo("=" * 30)

    current_cmd = config_manager.get_taskwarrior_cmd()
    current_enabled = config_manager.get_taskwarrior_enabled()

    typer.echo(f"Current command path: {current_cmd}")
    typer.echo(f"Current status: {'Enabled' if current_enabled else 'Disabled'}")

    if typer.confirm("Update Taskwarrior configuration?"):
        # Test if Taskwarrior is available
        try:
            TaskwarriorProvider(current_cmd)
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
                    TaskwarriorProvider(custom_cmd)
                    config_manager.set_taskwarrior_cmd(custom_cmd)
                    config_manager.set_taskwarrior_enabled(True)
                    typer.echo(f"✅ Taskwarrior configured with custom path: {custom_cmd}")
                except Exception as e2:
                    typer.echo(f"❌ Custom path also failed: {e2}")
                    raise typer.Exit(1)


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
    project: str | None = typer.Option(None, "--project", "-p", help="Filter by project"),
    query: str | None = typer.Option(None, "--query", "-q", help="Search query"),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum number of tasks to show"),
    include_done: bool = typer.Option(False, "--include-done", help="Include completed tasks"),
):
    """Show Taskwarrior tasks."""
    try:
        provider = TaskwarriorProvider()
        issues = provider.get_issues(
            project_id=project,
            query=query,
            limit=limit,
            include_done=include_done,
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
            if issue.custom_fields.get("urgency"):
                typer.echo(f"  Urgency: {issue.custom_fields['urgency']}")
            typer.echo(f"  Created: {issue.created_at}")
            typer.echo(f"  Modified: {issue.updated_at}")
            typer.echo()

    except Exception as e:
        typer.echo(f"❌ Error fetching Taskwarrior tasks: {e}")
        raise typer.Exit(1)


@app.command("tw-export")
def taskwarrior_export(
    project: str | None = typer.Option(None, "--project", "-p", help="Filter by project"),
    output_file: str | None = typer.Option(None, "--output", "-o", help="Output file path"),
    include_done: bool = typer.Option(False, "--include-done", help="Include completed tasks"),
):
    """Export Taskwarrior tasks to JSON format."""
    try:
        provider = TaskwarriorProvider()
        issues = provider.get_issues(
            project_id=project,
            limit=0,  # No limit
            include_done=include_done,
        )

        # Convert to exportable format
        export_data = []
        for issue in issues:
            export_data.append(
                {
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
                    "custom_fields": issue.custom_fields,
                }
            )

        import json

        if output_file:
            with open(output_file, "w") as f:
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
    project: str | None = typer.Option(None, "--project", "-p", help="Project name"),
    priority: str | None = typer.Option(None, "--priority", help="Priority (H, M, L)"),
    tags: str | None = typer.Option(None, "--tags", help="Comma-separated tags"),
):
    """Create a new Taskwarrior task."""
    try:
        provider = TaskwarriorProvider()

        # Parse tags
        tag_list = []
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",")]

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
            custom_fields={},
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


@app.command("config-todoist")
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
        raise typer.Exit(1)

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
        from .todoist_api import TodoistAPI

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


@app.command("create-project")
def create_project(
    name: str | None = typer.Option(None, "--name", "-n", help="Project name"),
    client: str | None = typer.Option(None, "--client", "-c", help="Client name"),
):
    """Create a project in both Todoist and Obsidian with automatic linking."""
    # Check prerequisites
    if not config_manager.get_todoist_token():
        typer.echo("❌ Todoist not configured. Run 'taskbridge config-todoist' first.")
        raise typer.Exit(1)

    if not config_manager.get_obsidian_vault_path():
        typer.echo("❌ Obsidian not configured. Run 'taskbridge config-obsidian' first.")
        raise typer.Exit(1)

    try:
        import subprocess
        import urllib.parse

        from .todoist_api import TodoistAPI

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

        # Trigger Obsidian to open the project folder (user's template will create overview)
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
        typer.echo(f"❌ Error creating project: {e}")
        raise typer.Exit(1)


@app.command("create-todoist-note")
def create_todoist_note(
    task_id: str,
    open_note: bool = typer.Option(
        True, "--open/--no-open", help="Open note in Obsidian after creation"
    ),
):
    """Create Obsidian note for a specific Todoist task."""
    if not config_manager.get_todoist_token():
        typer.echo("❌ Todoist not configured. Run 'taskbridge config-todoist' first.")
        raise typer.Exit(1)

    if not config_manager.get_obsidian_vault_path():
        typer.echo("❌ Obsidian not configured. Run 'taskbridge config-obsidian' first.")
        raise typer.Exit(1)

    try:
        from .database import TodoistNoteMapping
        from .todoist_api import TodoistAPI

        api = TodoistAPI()

        # Check if note already exists
        existing = db.get_todoist_note_by_task_id(task_id)
        if existing:
            typer.echo(f"⚠️  Note already exists: {existing.note_path}")
            if not typer.confirm("Recreate note?"):
                if open_note:
                    import subprocess

                    subprocess.run(["open", existing.obsidian_url])
                return

        # Fetch task from Todoist
        typer.echo(f"📥 Fetching task {task_id}...")
        task = api.get_task(task_id)
        if not task:
            typer.echo(f"❌ Task {task_id} not found")
            raise typer.Exit(1)

        # Get project mapping
        project_mapping = config_manager.get_todoist_project_mappings().get(task.project_id)
        if not project_mapping:
            typer.echo(f"⚠️  No mapping for project {task.project_id}")
            # Use project name directly
            project = api.get_project(task.project_id)
            project_name = project.name if project else "Todoist"
            client_name = ""
        else:
            project_name = project_mapping["folder"]
            client_name = project_mapping.get("client", "")

        # Create Obsidian note
        typer.echo(f"📝 Creating note in {project_name}...")
        note_path = config_manager.create_task_note(
            project_name=project_name,
            task_title=task.content,
            client=client_name,
            status="backlog",
            tags=task.labels,
        )

        # Generate Obsidian URL
        obsidian_url = config_manager.generate_obsidian_url(project_name, note_path.name)

        # Save mapping to database
        mapping = TodoistNoteMapping(
            todoist_task_id=task_id,
            todoist_project_id=task.project_id,
            note_path=str(note_path),
            obsidian_url=obsidian_url,
        )
        db.create_todoist_note_mapping(mapping)

        typer.echo(f"✅ Created note: {note_path.name}")

        # Add Obsidian URL as comment in Todoist
        typer.echo("💬 Adding Obsidian URL to Todoist task...")
        comment_text = f"📝 Obsidian note: [Open Note]({obsidian_url})"
        if api.create_comment(task_id, comment_text):
            typer.echo("✅ Added Obsidian URL as comment")
        else:
            typer.echo("⚠️  Failed to add comment (note still created)")

        # Open note if requested
        if open_note:
            if config_manager.open_obsidian_note(project_name, note_path.name):
                typer.echo("📖 Opened note in Obsidian")
        else:
            typer.echo(f"📖 Obsidian URL: {obsidian_url}")

    except Exception as e:
        typer.echo(f"❌ Error: {e}")
        raise typer.Exit(1)


@app.command("sync-todoist-notes")
def sync_todoist_notes(
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Preview without creating notes"),
    label: str | None = typer.Option(None, "--label", "-l", help="Override sync label from config"),
):
    """Scan Todoist tasks with sync label and create Obsidian notes."""
    if not config_manager.get_todoist_token():
        typer.echo("❌ Todoist not configured. Run 'taskbridge config-todoist' first.")
        raise typer.Exit(1)

    if not config_manager.get_obsidian_vault_path():
        typer.echo("❌ Obsidian not configured. Run 'taskbridge config-obsidian' first.")
        raise typer.Exit(1)

    try:
        from .database import TodoistNoteMapping
        from .todoist_api import TodoistAPI

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
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
