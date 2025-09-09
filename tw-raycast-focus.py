#!/usr/bin/env python3

"""
tw-raycast-focus.py
Starts Raycast Focus mode for the active taskwarrior task using the task description as the goal
"""

import json
import subprocess
import sys
import urllib.parse
from pathlib import Path

def print_status(color_code: str, message: str):
    """Print colored status message"""
    colors = {
        'red': '\033[0;31m',
        'green': '\033[0;32m',
        'yellow': '\033[1;33m',
        'blue': '\033[0;34m',
        'nc': '\033[0m'
    }
    print(f"{colors.get(color_code, '')}{message}{colors['nc']}")

def get_active_task():
    """Get active task from taskwarrior"""
    try:
        result = subprocess.run(
            ['task', '+ACTIVE', 'export'],
            capture_output=True,
            text=True,
            check=True
        )

        tasks = json.loads(result.stdout)
        if not tasks:
            print_status('red', "❌ No active task found. Start a task first with 'task <id> start'")
            sys.exit(1)

        return tasks[0]
    except subprocess.CalledProcessError as e:
        print_status('red', f"❌ Error getting active task: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print_status('red', f"❌ Error parsing task data: {e}")
        sys.exit(1)

def start_raycast_focus(task_description: str):
    """Start Raycast Focus mode with task description as goal"""
    try:
        # URL-encode the goal parameter
        encoded_goal = urllib.parse.quote(task_description)
        focus_url = f"raycast://focus/start?goal={encoded_goal}"

        print_status('blue', f"🎯 Starting Raycast Focus mode with goal: {task_description}")

        if sys.platform == 'darwin':  # macOS
            subprocess.run(['open', focus_url], check=True)
            print_status('green', "✅ Raycast Focus mode started successfully")
        else:
            print_status('yellow', f"⚠️  Raycast Focus is only available on macOS")
            print_status('blue', f"Focus URL: {focus_url}")

    except subprocess.CalledProcessError as e:
        print_status('red', f"❌ Error starting Raycast Focus mode: {e}")
        sys.exit(1)
    except Exception as e:
        print_status('red', f"❌ Unexpected error: {e}")
        sys.exit(1)

def get_focus_status():
    """Check if there's already an active focus session"""
    # This is a placeholder - Raycast doesn't provide an easy way to check focus status
    # We could potentially check if there are any focus-related processes or windows
    # For now, we'll just inform the user
    print_status('blue', "ℹ️  Note: This will start a new focus session (or do nothing if one is already active)")

def main():
    """Main function"""
    print_status('blue', "🔍 Looking for active taskwarrior task...")

    # Get active task
    task = get_active_task()

    task_uuid = task['uuid']
    task_description = task['description']
    project_name = task.get('project', 'Default')

    print_status('green', f"✅ Found active task: {task_description}")
    if project_name and project_name != 'Default':
        print_status('blue', f"📁 Project: {project_name}")

    # Check for any existing focus session (informational only)
    get_focus_status()

    # Start Raycast Focus mode
    start_raycast_focus(task_description)

    print_status('green', "🎉 Done! Raycast Focus mode started for your active task.")
    print_status('yellow', "💡 Tip: Use 'raycast://focus/complete' URL or the Raycast UI to end the focus session")

if __name__ == "__main__":
    main()
