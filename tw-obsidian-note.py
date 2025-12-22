#!/usr/bin/env python3

"""
tw-obsidian-note.py
Creates and opens Obsidian notes for taskwarrior tasks using the same structure as taskbridge
"""

import json
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path


def print_status(color_code: str, message: str):
    """Print colored status message"""
    colors = {
        "red": "\033[0;31m",
        "green": "\033[0;32m",
        "yellow": "\033[1;33m",
        "blue": "\033[0;34m",
        "nc": "\033[0m",
    }
    print(f"{colors.get(color_code, '')}{message}{colors['nc']}")


def parse_simple_yaml(content: str) -> dict:
    """Simple YAML parser for key: value pairs"""
    config = {}
    for line in content.strip().split("\n"):
        line = line.strip()
        if line and ":" in line and not line.startswith("#"):
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            # Remove quotes if present
            if value.startswith(('"', "'")) and value.endswith(('"', "'")):
                value = value[1:-1]
            config[key] = value
    return config


def get_obsidian_config():
    """Get Obsidian configuration from taskbridge config"""
    config_dir = Path.home() / ".taskbridge"

    # Try YAML config first, then JSON
    yaml_config = config_dir / "config.yaml"
    json_config = config_dir / "config.json"

    config = None

    if yaml_config.exists():
        try:
            with open(yaml_config) as f:
                content = f.read()
                config = parse_simple_yaml(content)
        except OSError as e:
            print_status("red", f"❌ Error reading YAML config: {e}")
            sys.exit(1)
    elif json_config.exists():
        try:
            with open(json_config) as f:
                config = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print_status("red", f"❌ Error reading JSON config: {e}")
            sys.exit(1)
    else:
        print_status(
            "red", "❌ Taskbridge config not found. Run 'taskbridge config-obsidian' first."
        )
        sys.exit(1)

    vault_path = config.get("obsidian_vault_path")
    vault_name = config.get("obsidian_vault_name", "obsidian")

    if not vault_path:
        print_status(
            "red", "❌ Obsidian vault path not configured. Run 'taskbridge config-obsidian' first."
        )
        sys.exit(1)

    return vault_path, vault_name


def get_active_task():
    """Get active task from taskwarrior"""
    try:
        result = subprocess.run(
            ["task", "+ACTIVE", "export"], capture_output=True, text=True, check=True
        )

        tasks = json.loads(result.stdout)
        if not tasks:
            print_status(
                "red", "❌ No active task found. Start a task first with 'task <id> start'"
            )
            sys.exit(1)

        return tasks[0]
    except subprocess.CalledProcessError as e:
        print_status("red", f"❌ Error getting active task: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print_status("red", f"❌ Error parsing task data: {e}")
        sys.exit(1)


def sanitize_filename(title: str) -> str:
    """Sanitize filename to match taskbridge behavior"""
    # Keep only alphanumeric, spaces, hyphens, and underscores
    safe_title = re.sub(r"[^a-zA-Z0-9 _-]", "", title)
    # Remove trailing whitespace
    return safe_title.rstrip()


def remove_client_from_project(project_name: str) -> str:
    """Remove client name prefix from project name if present"""
    # Look for pattern like "ClientName.RestOfProject" or "ClientName - RestOfProject"
    # Match client names that end with a period followed by more text
    match = re.match(r"^([A-Za-z]+\.)\s*(.+)", project_name)
    if match:
        client_prefix, remaining_project = match.groups()
        return remaining_project.strip()

    # Also handle "Client - Project" pattern
    match = re.match(r"^([A-Za-z]+)\s*-\s*(.+)", project_name)
    if match:
        potential_client, remaining_project = match.groups()
        # Only remove if the potential client looks like a client name (short, capitalized)
        if len(potential_client) <= 6 and potential_client.isupper():
            return remaining_project.strip()

    return project_name


def create_obsidian_note(
    vault_path: str, project_name: str, task_title: str, task_uuid: str
) -> Path:
    """Create Obsidian note with frontmatter"""
    # Remove client prefix from project name for directory structure
    clean_project_name = remove_client_from_project(project_name)

    # Create project directory
    project_dir = Path(vault_path) / "10 Projects" / clean_project_name
    project_dir.mkdir(parents=True, exist_ok=True)

    # Create sanitized filename
    safe_title = sanitize_filename(task_title)
    note_path = project_dir / f"{safe_title}.md"

    # Check if note already exists
    if note_path.exists():
        print_status("yellow", f"📝 Note already exists: {safe_title}.md")
    else:
        print_status("blue", f"📝 Creating new note: {safe_title}.md")

        # Create note content with frontmatter
        frontmatter = {
            "fileClass": "task",
            "project": clean_project_name,
            "status": "in-progress",
            "client": "",
            "tags": [],
            "due": "",
            "taskwarrior_uuid": task_uuid,
        }

        content = "---\n"
        for key, value in frontmatter.items():
            if isinstance(value, list):
                if value:
                    content += f"{key}: {value}\n"
                else:
                    content += f"{key}: []\n"
            elif isinstance(value, str):
                content += f'{key}: "{value}"\n' if value else f'{key}: ""\n'
            else:
                content += f"{key}: {value}\n"

        content += f"""---

# {task_title}

## Notes

## Tasks
- [ ]

## Links
"""

        with open(note_path, "w") as f:
            f.write(content)

        print_status("green", f"✅ Created note: {safe_title}.md")

    return note_path


def get_existing_obsidian_link(task_uuid: str) -> str:
    """Get existing Obsidian link from task annotations"""
    try:
        result = subprocess.run(
            ["task", task_uuid, "export"], capture_output=True, text=True, check=True
        )

        task_data = json.loads(result.stdout)[0]
        annotations = task_data.get("annotations", [])

        # Look for obsidian:// links in annotations
        for annotation in annotations:
            description = annotation.get("description", "")
            if "obsidian://" in description:
                # Extract the URL from the annotation
                import re

                match = re.search(r"obsidian://[^\s]+", description)
                if match:
                    return match.group(0)

        return ""

    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        print_status("red", f"❌ Error getting task annotations: {e}")
        return ""


def annotate_task(task_uuid: str, project_name: str, task_title: str, vault_name: str):
    """Annotate taskwarrior task with Obsidian link"""
    # Remove client prefix from project name for URL
    clean_project_name = remove_client_from_project(project_name)

    # Create obsidian:// URL
    safe_title = sanitize_filename(task_title)
    encoded_project = urllib.parse.quote(clean_project_name)
    encoded_title = urllib.parse.quote(safe_title)
    obsidian_url = f"obsidian://open?vault={vault_name}&file=10%20Projects%2F{encoded_project}%2F{encoded_title}.md"

    # Check if annotation already exists
    existing_link = get_existing_obsidian_link(task_uuid)

    if not existing_link:
        try:
            subprocess.run(["task", task_uuid, "annotate", obsidian_url], check=True)
            print_status("green", "✅ Added Obsidian link to task annotations")
        except subprocess.CalledProcessError as e:
            print_status("red", f"❌ Error annotating task: {e}")
    else:
        print_status("yellow", "📝 Obsidian link already exists in task annotations")


def open_obsidian_url(obsidian_url: str):
    """Open Obsidian using a URL"""
    print_status("blue", "🚀 Opening note in Obsidian...")

    try:
        if sys.platform == "darwin":  # macOS
            subprocess.run(["open", obsidian_url], check=True)
        elif sys.platform.startswith("linux"):  # Linux
            subprocess.run(["xdg-open", obsidian_url], check=True)
        else:
            print_status("yellow", f"⚠️  Please manually open: {obsidian_url}")
    except subprocess.CalledProcessError:
        print_status("yellow", f"⚠️  Could not open automatically. Please open: {obsidian_url}")


def open_in_obsidian(vault_name: str, project_name: str, task_title: str):
    """Open note in Obsidian"""
    # Remove client prefix from project name for URL
    clean_project_name = remove_client_from_project(project_name)

    safe_title = sanitize_filename(task_title)
    encoded_project = urllib.parse.quote(clean_project_name)
    encoded_title = urllib.parse.quote(safe_title)
    obsidian_url = f"obsidian://open?vault={vault_name}&file=10%20Projects%2F{encoded_project}%2F{encoded_title}.md"

    open_obsidian_url(obsidian_url)


def main():
    """Main function"""
    print_status("blue", "🔍 Looking for active taskwarrior task...")

    # Get Obsidian configuration
    vault_path, vault_name = get_obsidian_config()

    # Get active task
    task = get_active_task()

    task_uuid = task["uuid"]
    task_description = task["description"]
    project_name = task.get("project", "Default")

    print_status("green", f"✅ Found active task: {task_description}")
    print_status("blue", f"📁 Project: {project_name}")

    # Check if task already has an Obsidian link
    existing_link = get_existing_obsidian_link(task_uuid)

    if existing_link:
        print_status("yellow", "📝 Found existing Obsidian link in task annotations")
        print_status("blue", "🚀 Opening existing note...")
        open_obsidian_url(existing_link)
        print_status("green", "🎉 Done! Opened existing Obsidian note.")
    else:
        print_status("blue", "📝 No existing note found, creating new one...")

        # Create Obsidian note
        create_obsidian_note(vault_path, project_name, task_description, task_uuid)

        # Annotate taskwarrior task
        annotate_task(task_uuid, project_name, task_description, vault_name)

        # Open in Obsidian
        open_in_obsidian(vault_name, project_name, task_description)

        print_status("green", "🎉 Done! Note created and opened in Obsidian.")


if __name__ == "__main__":
    main()
