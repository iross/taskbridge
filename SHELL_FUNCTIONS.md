# Shell Functions for TaskBridge

This file contains convenient shell functions that use `taskbridge task select` with fzf for quick task workflows.

## Installation

Add these functions to your shell configuration file:
- **Bash/Zsh**: `~/.bashrc` or `~/.zshrc`
- **Fish**: `~/.config/fish/config.fish`

After adding, reload your shell: `source ~/.zshrc` (or restart your terminal)

## Prerequisites

Install fzf:
```bash
brew install fzf
```

## Bash/Zsh Functions

### Quick Task Note Creation
Select a task and create an Obsidian note for it:
```bash
tnote() {
    local filter="${1:-today}"
    local task_id=$(taskbridge task select -f "$filter")
    if [ -n "$task_id" ]; then
        taskbridge task note "$task_id"
    fi
}
```

Usage:
```bash
tnote                  # Select from today's tasks
tnote "priority 1"     # Select from high priority tasks
tnote "@work"          # Select from tasks with @work label
```

### Quick Task Start (Time Tracking)
Select a task and start time tracking:
```bash
tstart() {
    local filter="${1:-today}"
    local task_id=$(taskbridge task select -f "$filter")
    if [ -n "$task_id" ]; then
        taskbridge time start -t "$task_id"
    fi
}
```

Usage:
```bash
tstart                 # Select from today's tasks
tstart "overdue"       # Select from overdue tasks
```

### Quick Task Completion
Select a task and mark it as done:
```bash
tdone() {
    local filter="${1:-today}"
    local task_id=$(taskbridge task select -f "$filter")
    if [ -n "$task_id" ]; then
        taskbridge task done "$task_id"
    fi
}
```

Usage:
```bash
tdone                  # Select from today's tasks
tdone "priority 1"     # Select from high priority tasks
```

### Show Task Details
Select a task and show its full details:
```bash
tshow() {
    local filter="${1:-today}"
    local task_id=$(taskbridge task select -f "$filter")
    if [ -n "$task_id" ]; then
        taskbridge task show "$task_id"
    fi
}
```

### Tasks Without Notes
Quickly select and create notes for tasks that don't have them yet:
```bash
tnote-new() {
    local filter="${1:-today}"
    local task_id=$(taskbridge task select -f "$filter" --without-notes)
    if [ -n "$task_id" ]; then
        taskbridge task note "$task_id"
    fi
}
```

### Project-Specific Task Selection
Select tasks from a specific project:
```bash
tproject() {
    local project="${1}"
    if [ -z "$project" ]; then
        echo "Usage: tproject <project-name>"
        return 1
    fi
    local task_id=$(taskbridge task select -p "$project")
    if [ -n "$task_id" ]; then
        taskbridge task note "$task_id"
    fi
}
```

Usage:
```bash
tproject "Client Work"    # Select tasks from "Client Work" project
```

## Fish Shell Functions

### Quick Task Note Creation
```fish
function tnote
    set filter (count $argv > 0 && echo $argv[1] || echo "today")
    set task_id (taskbridge task select -f $filter)
    if test -n "$task_id"
        taskbridge task note $task_id
    end
end
```

### Quick Task Start
```fish
function tstart
    set filter (count $argv > 0 && echo $argv[1] || echo "today")
    set task_id (taskbridge task select -f $filter)
    if test -n "$task_id"
        taskbridge time start -t $task_id
    end
end
```

### Quick Task Completion
```fish
function tdone
    set filter (count $argv > 0 && echo $argv[1] || echo "today")
    set task_id (taskbridge task select -f $filter)
    if test -n "$task_id"
        taskbridge task done $task_id
    end
end
```

## Advanced Examples

### Combined Note Creation and Time Tracking
```bash
twork() {
    local filter="${1:-today}"
    local task_id=$(taskbridge task select -f "$filter" --without-notes)
    if [ -n "$task_id" ]; then
        taskbridge task note "$task_id" --no-open  # Note already starts tracking
        echo "Started working on task $task_id"
    fi
}
```

### Select from Multiple Projects
```bash
tselect() {
    local task_id=$(taskbridge task select "$@")
    if [ -n "$task_id" ]; then
        echo "Selected task ID: $task_id"
        echo "Copied to clipboard!"
        echo -n "$task_id" | pbcopy  # macOS clipboard
    fi
}
```

## Todoist Filter Examples

The filter query (`-f` flag) supports all Todoist filter syntax:

- `today` - Tasks due today
- `overdue` - Overdue tasks
- `priority 1` - High priority tasks (p1)
- `priority 2` - Medium priority tasks (p2)
- `@work` - Tasks with @work label
- `#Project Name` - Tasks in specific project
- `due before: tomorrow` - Tasks due before tomorrow
- `assigned to: me` - Tasks assigned to you
- `no date` - Tasks with no due date
- `7 days` - Tasks due in next 7 days

## Tips

1. **Start with common filters**: Create functions for your most common workflows
2. **Chain commands**: Use `&&` to run multiple commands after selection
3. **Error handling**: The functions above handle cancellation (ESC in fzf) gracefully
4. **Customize fzf**: Set `FZF_DEFAULT_OPTS` for custom colors and keybindings

Example fzf customization:
```bash
export FZF_DEFAULT_OPTS='--height 50% --border --color=16'
```
