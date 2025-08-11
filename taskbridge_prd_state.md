# TaskBridge - Product Requirements Document

## Project Overview

**Project Name**: TaskBridge  
**Purpose**: Python library + CLI that maintains synchronized project/client mappings between Linear and Toggl, with Raycast integration for seamless issue-to-time-tracking workflow.

**Database Location**: `~/.taskbridge/mappings.db`  
**Configuration**: `~/.taskbridge/config.yaml`

## Technical Specifications

### Technology Stack
- **Language**: Python 3.9+
- **CLI Framework**: Typer
- **HTTP Client**: requests
- **Database**: SQLite3 (built-in)
- **Configuration**: PyYAML
- **Package Manager**: uv (preferred), pip fallback
- **Package Structure**: pip-installable with pyproject.toml

### Architecture
- **Core Library**: Python package with CLI interface
- **Raycast Integration**: Script Commands that execute CLI functions
- **Data Storage**: SQLite for project mappings
- **API Integration**: Direct GraphQL calls to Linear and HTTP calls to Toggl APIs

## Core Functionality

### Entity Mapping Strategy
- **Linear Projects**: Use `#client/CLIENT_NAME` label convention
- **Toggl Structure**: Client → Project hierarchy
- **Mapping Example**: Linear project "GPU Cluster Migration" with `#client/CHTC` label → Toggl Client "CHTC" → Project "GPU Cluster Migration"
- **Data Flow**: Linear as source of truth for issues, bidirectional sync for projects/clients

### CLI Commands
1. `taskbridge config` - Interactive setup of API keys
2. `taskbridge sync` - Preview and sync projects between systems
3. `taskbridge search <query>` - Search Linear issues
4. `taskbridge start [issue-id]` - Start Toggl timer (interactive search if no ID)
5. `taskbridge status` - Show current running timer
6. `taskbridge stop` - Stop current timer
7. `taskbridge list-projects` - Show current project mappings

### Behavioral Specifications

#### Sync Behavior
- Show preview of all changes before execution
- Require explicit user confirmation
- Handle edge cases: projects not having `#client/CLIENT_NAME` labels shown in preview for user decision
- Bidirectional project creation between systems

#### Timer Management
- Auto-stop current timer when starting new one
- Interactive search when no issue ID provided
- Store timer metadata linking to Linear issue

#### Error Handling
- Basic error messages (no fancy formatting)
- Standard Python logging
- Graceful API failure handling

## Implementation Tasks

### Phase 1: Project Foundation
**Task 1: Project Structure Setup**
- Create pip-installable Python package with uv
- Set up pyproject.toml with dependencies: typer, requests, pyyaml
- Create directory structure:
  ```
  taskbridge/
  ├── pyproject.toml
  ├── src/taskbridge/
  │   ├── __init__.py
  │   ├── cli.py
  │   ├── config.py
  │   ├── database.py
  │   ├── linear_api.py
  │   ├── toggl_api.py
  │   └── sync.py
  └── raycast_commands/
  ```
- Set up entry point for `taskbridge` command

**Task 2: Configuration Management**
- Implement config.py to handle ~/.taskbridge/config.yaml
- Create interactive `taskbridge config` command using typer.prompt()
- Store Linear and Toggl API keys securely
- Create config directory if it doesn't exist
- Validate API keys can connect to both services

**Task 3: Database Schema**
- Design SQLite schema for project mappings:
  - `projects` table: id, linear_id, linear_name, toggl_client_id, toggl_project_id, created_at, updated_at
  - `sync_log` table: id, action, timestamp, details
- Implement database.py with create, read, update, delete operations
- Handle database migrations and initialization

### Phase 2: API Integration
**Task 4: Linear API Client**
- Implement linear_api.py with GraphQL requests
- Functions needed:
  - `get_projects()` - fetch all projects
  - `create_project(name)` - create new project
  - `get_issues(project_id=None, query=None)` - search/filter issues
- Parse `#client/CLIENT_NAME` format from project labels
- Handle GraphQL authentication and error responses

**Task 5: Toggl API Client**
- Implement toggl_api.py with requests
- Functions needed:
  - `get_clients()` - fetch all clients
  - `get_projects(client_id=None)` - fetch projects
  - `create_client(name)` - create new client
  - `create_project(name, client_id)` - create new project
  - `start_timer(project_id, description)` - start time entry
  - `stop_timer()` - stop current timer
  - `get_current_timer()` - check running timer
- Handle API authentication and error responses

### Phase 3: Core Logic
**Task 6: Sync Engine**
- Implement sync.py with core synchronization logic
- Parse Linear projects to extract Client/Project structure from labels
- Compare existing mappings with current API state
- Generate preview of changes (creates, conflicts, edge cases)
- Execute approved changes and update database
- Handle projects not having `#client/CLIENT_NAME` labels

**Task 7: CLI Interface**
- Implement cli.py using typer
- All commands from specification:
  - `config` - call config setup
  - `sync` - run sync with preview/confirmation
  - `search <query>` - search Linear issues, display results
  - `start [issue-id]` - start timer (with interactive search fallback)
  - `status` - show current timer
  - `stop` - stop current timer
  - `list-projects` - show mappings
- Handle command-line arguments and options
- Auto-stop current timer when starting new one

### Phase 4: Raycast Integration
**Task 8: Raycast Script Commands**
- Create raycast_commands/ directory with script files
- Each script calls appropriate taskbridge CLI command:
  - `search-issues.py` - Interactive issue search and timer start
  - `sync-projects.sh` - Run project sync
  - `current-timer.sh` - Show current timer status
  - `stop-timer.sh` - Stop current timer
- Include proper Raycast metadata headers
- Handle script arguments and output formatting

**Task 9: Testing & Polish**
- Test full workflow: config → sync → search → start → stop
- Verify Raycast integration works correctly
- Handle edge cases and error conditions
- Create basic documentation/README
- Test installation process with uv/pip

## User Stories & Acceptance Criteria

### Epic 1: Initial Setup
**Story**: As a user, I want to set up TaskBridge with my API credentials
**Acceptance Criteria**:
- `taskbridge config` prompts for Linear and Toggl API keys
- Config stored securely in ~/.taskbridge/config.yaml
- Keys validated by connecting to both APIs
- Database initialized automatically

### Epic 2: Project Synchronization
**Story**: As a user, I want to sync projects between Linear and Toggl
**Acceptance Criteria**:
- `taskbridge sync` shows preview of all changes
- Projects with `#client/CLIENT_NAME` labels map correctly
- Projects without client labels shown for user decision
- User must confirm before any changes are made
- Bidirectional creation (Linear → Toggl and Toggl → Linear)

### Epic 3: Task-Based Time Tracking
**Story**: As a user, I want to start timers from Linear issues via Raycast
**Acceptance Criteria**:
- `taskbridge start` without ID shows interactive search
- `taskbridge start <id>` starts timer directly
- Running timers auto-stopped when starting new ones
- Timer descriptions include issue titles
- Raycast integration allows seamless issue selection

### Epic 4: Timer Management
**Story**: As a user, I want to monitor and control my active timers
**Acceptance Criteria**:
- `taskbridge status` shows current timer details
- `taskbridge stop` ends current timer
- Integration works from both CLI and Raycast

## Success Metrics
- Time saved per day (manual timer creation eliminated)
- Accuracy of project mappings (no misclassified time entries)
- User adoption (successful setup and daily use)
- Sync reliability (conflicts resolved, no data loss)

## Risk Mitigation
- **API Rate Limits**: Implement request throttling and caching
- **Data Loss**: Database backups, transaction safety
- **Authentication**: Secure credential storage, token refresh handling
- **Sync Conflicts**: Clear preview and user confirmation required
- **Raycast Compatibility**: Test script commands thoroughly

## Future Enhancements (Out of Scope)
- Automatic background sync
- Advanced conflict resolution rules
- Time tracking analytics
- Multi-user support
- GUI interface