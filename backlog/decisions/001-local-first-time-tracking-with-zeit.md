# ADR-001: Adopt Zeit for Local-First Time Tracking

## Status

**Accepted** - 2026-01-08

## Context

TaskBridge currently integrates Todoist tasks with Obsidian notes, but lacks time tracking capabilities. We need a local-first time tracking solution that:

- Stores data locally for privacy and offline access
- Provides a developer-friendly CLI interface
- Can be integrated programmatically with TaskBridge
- Supports data export and portability
- Is actively maintained

The solution should act as a bridge between task management and time tracking, enabling developers to track time spent on tasks from the command line before optionally syncing to external time tracking services.

## Decision

We will adopt **zeit** (https://codeberg.org/mrus/zeit) as our local-first time tracking solution.

### Rationale

1. **JSON-First Design**: Zeit provides JSON output for all commands (`-f json`), making it ideal for programmatic integration
2. **Natural Language Interface**: Supports intuitive commands like `zeit start work with note "..." on project/task`
3. **Modern Architecture**: Written in Go with BuntDB storage, single binary deployment
4. **Designed for Integration**: Explicitly built to integrate with external systems
5. **Active Development**: Recently released v1.0 (October 2025) with enhanced integration features
6. **Local-First**: All data stored locally in JSON format, easily auditable
7. **Data Portability**: Native export capabilities for backups and migration

## Implementation

A Python integration module (`zeit_integration.py`) has been created providing:

- Start/Stop tracking operations
- CRUD operations for time blocks
- Project and task management
- Filtering and querying capabilities
- Statistics and reporting
- Data export functionality

### Example Usage

```python
from taskbridge.zeit_integration import ZeitIntegration

zeit = ZeitIntegration()

# Start tracking
zeit.start_tracking(
    note="Working on authentication feature",
    project="taskbridge",
    task="auth"
)

# Stop tracking
zeit.stop_tracking()

# Query time blocks
blocks = zeit.list_blocks(project="taskbridge", start="today")
for block in blocks:
    print(f"{block.note}: {block.start} -> {block.end}")
```

## Consequences

### Positive

- **Developer UX**: Natural CLI interface improves adoption among developers
- **Privacy**: All time data stays local unless explicitly synced
- **Integration-Ready**: JSON API makes it straightforward to build features on top
- **Lightweight**: Single binary, no runtime dependencies
- **Flexible**: Can be used standalone or integrated with TaskBridge workflows

### Negative

- **Newer Tool**: Smaller community compared to established alternatives like Timewarrior
- **External Dependency**: Requires zeit binary to be installed on the system
- **Learning Curve**: Users need to understand zeit's project/task model

### Neutral

- **Local Storage**: While great for privacy, requires separate solution for team collaboration
- **CLI-Only**: No built-in GUI (though this aligns with our CLI-first philosophy)

## Alternatives Considered

### Timewarrior

**Verdict**: Solid but overkill

- ✅ Very mature and battle-tested
- ✅ Strong integration with Taskwarrior
- ❌ More complex than needed for basic time tracking
- ❌ C++ dependency adds complexity
- ❌ Custom data format less integration-friendly

### Watson

**Verdict**: Good Python alternative

- ✅ Python-native (matches TaskBridge stack)
- ✅ Simple data model, good export formats
- ✅ Could be imported as library
- ❌ Less feature-rich than zeit
- ❌ CLI interface less intuitive
- ⚠️ JSON output less comprehensive

### Timetrap

**Verdict**: Avoid due to maintenance concerns

- ✅ SQLite backend is solid
- ✅ Good export formats (CSV, iCal)
- ❌ "Sadly not maintained" according to alternatives
- ❌ Ruby dependency doesn't fit Python stack
- ❌ Reduced community activity

## Comparison Matrix

| Criterion | Zeit | Timewarrior | Watson | Timetrap |
|-----------|------|-------------|--------|----------|
| **Language** | Go | C++ | Python | Ruby |
| **Data Storage** | BuntDB (JSON) | Text files | Text/JSON | SQLite3 |
| **CLI UX** | ⭐⭐⭐⭐⭐ Natural language | ⭐⭐⭐⭐ Powerful | ⭐⭐⭐ Simple | ⭐⭐⭐ Simple |
| **Data Portability** | ⭐⭐⭐⭐⭐ Excellent JSON | ⭐⭐⭐ Custom format | ⭐⭐⭐⭐ Good | ⭐⭐⭐⭐ Excellent |
| **Integration** | ⭐⭐⭐⭐⭐ JSON everywhere | ⭐⭐⭐ Good | ⭐⭐⭐⭐ Python lib | ⭐⭐⭐ Moderate |
| **Community** | ⭐⭐⭐ Active, growing | ⭐⭐⭐⭐⭐ Strong | ⭐⭐⭐⭐ Strong | ⭐⭐ Weak |
| **Maintenance** | ⭐⭐⭐⭐ v1.0 Oct 2025 | ⭐⭐⭐⭐⭐ v1.9.1 Aug 2025 | ⭐⭐⭐⭐ Active | ⭐⭐ Concerns |

## Validation

A proof-of-concept implementation successfully demonstrated:

- ✅ Start/stop time tracking from Python
- ✅ Create, read, update time blocks
- ✅ Filter blocks by project, task, and time range
- ✅ Query statistics and aggregate data
- ✅ Export data for backup/migration

The POC confirms zeit meets all requirements and integrates smoothly with TaskBridge's Python codebase.

## Future Considerations

1. **Optional Remote Sync**: Consider building a sync adapter to push zeit data to services like Toggl or Clockify
2. **TaskBridge Commands**: Add `taskbridge time start/stop` commands that wrap zeit
3. **Automatic Tracking**: Explore auto-tracking when tasks transition to "In Progress"
4. **Reporting**: Build reports showing time spent per project/task/client
5. **Migration Tools**: If zeit adoption is low, maintain flexibility to switch

## References

- Zeit Repository: https://codeberg.org/mrus/zeit
- Zeit v1 Announcement: https://xn--gckvb8fzb.com/zeit-v1/
- Task-19: Evaluate local-first time tracking solutions
- POC Code: `src/taskbridge/zeit_integration.py`, `poc_zeit_demo.py`

## Sources

- [Zeit](https://zeit.observer/)
- [GitHub - mrusme/zeit](https://github.com/mrusme/zeit)
- [マリウス . Zeit v1](https://xn--gckvb8fzb.com/zeit-v1/)
- [Timewarrior - GothenburgBitFactory](https://github.com/GothenburgBitFactory/timewarrior)
- [Timewarrior.net](https://timewarrior.net/)
- [Watson - Jazzband](https://github.com/jazzband/Watson)
- [Watson Documentation](https://jazzband.github.io/Watson/)
- [Timetrap - GitHub](https://github.com/samg/timetrap)
