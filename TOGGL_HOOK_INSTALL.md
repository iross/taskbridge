# Taskwarrior Toggl Hook Installation Guide

This guide explains how to install and use the Taskwarrior-Toggl integration hook that automatically starts and stops Toggl timers based on Taskwarrior task events.

## Prerequisites

1. **Taskwarrior** must be installed and configured
2. **TaskBridge** must be properly installed with Toggl API access configured
3. **Toggl API token** must be configured in TaskBridge settings

## Installation

### 1. Create Hook Directory
```bash
mkdir -p ~/.task/hooks
```

### 2. Copy the Hook Script
```bash
cp /Users/iross/projects/taskbridge/on-modify.toggl ~/.task/hooks/
```

### 3. Make Script Executable
```bash
chmod +x ~/.task/hooks/on-modify.toggl
```

### 4. Update Python Path (if needed)
If you get "env: python: No such file or directory" errors, update the shebang line to use an absolute path:
```bash
# Find your Python path
which python

# Edit the first line of the script to use the absolute path
# For example: #!/Users/yourusername/.pyenv/shims/python
```

## Usage

The hook works automatically once installed. Here's how it integrates with your Taskwarrior workflow:

### Starting a Task Timer
```bash
task start <task_id>
```
- Automatically starts a Toggl timer
- Uses task description as timer description
- Maps client and project based on task tags and project

### Stopping a Task Timer  
```bash
task stop <task_id>
# or
task done <task_id>
```
- Automatically stops the running Toggl timer
- Reports time spent on the task
- Shows total project time accumulated

### Client and Project Mapping

#### Client Tags
Use tags in the format `client:ClientName` to associate tasks with Toggl clients:
```bash
task add "Review proposal" client:AcmeCorp project:Marketing
```

#### Project Mapping
- Uses Taskwarrior project field directly
- If project name contains client name, client name is filtered out
- Creates new Toggl projects automatically if they don't exist
- Falls back to "General" project if none specified

### Examples

```bash
# Task with client and project
task add "Design homepage" client:AcmeCorp project:Website

# Start the task (starts Toggl timer)
task start 1

# Stop the task (stops Toggl timer, shows time report)
task done 1
```

Output when starting:
```
⏱️  Started Toggl timer for AcmeCorp in project 'Website': Design homepage
```

Output when stopping:
```
⏹️  Stopped Toggl timer in project 'Website': Design homepage (45m)
📊  Total project time: 3h 25m
```

## Logging

Hook activity is logged to:
- `~/.task/hooks/toggl-hook.log` - Detailed logging
- stderr - Error messages and user feedback

## Troubleshooting

### Hook Not Working
1. Check hook permissions: `ls -la ~/.task/hooks/on-modify.toggl`
2. Verify Taskwarrior can execute it: `~/.task/hooks/on-modify.toggl` (should show usage)
3. Check the log file for errors: `tail -f ~/.task/hooks/toggl-hook.log`

### Toggl API Errors
1. Verify TaskBridge Toggl configuration: run `taskbridge` and check Toggl settings
2. Test Toggl API manually: `python -c "from taskbridge.toggl_api import TogglAPI; api = TogglAPI(); print('OK')"`
3. Check API token validity in your Toggl account settings

### Import Errors
1. Ensure TaskBridge is properly installed
2. Update the Python path in the script if TaskBridge is in a different location
3. Install required dependencies: `pip install -r taskbridge/requirements.txt`

## Configuration

The hook uses your existing TaskBridge configuration for:
- Toggl API token
- Default workspace settings
- Logging preferences

No additional configuration is required beyond TaskBridge setup.

## Limitations

1. **Project Time Reporting**: Currently shows placeholder values. Full implementation would require Toggl Reports API integration.
2. **Multiple Running Timers**: Hook stops any existing timer when starting a new one.
3. **Task Modifications**: Changes to running tasks don't update timer details yet.

## Uninstalling

To remove the hook:
```bash
rm ~/.task/hooks/on-modify.toggl
```

Existing Toggl time entries will not be affected.