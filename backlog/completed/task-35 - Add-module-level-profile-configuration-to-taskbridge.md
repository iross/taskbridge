---
id: TASK-35
title: Add module-level profile configuration to taskbridge
status: Done
assignee: []
created_date: '2026-08-07 18:53'
updated_date: '2026-08-11 01:49'
labels: []
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Let config.yaml define named profiles (e.g. home, work), each enabling a specific set of modules, so machine-specific runs (via a default_profile setting or a --profile override) only activate the sources relevant to that context.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 config.yaml supports a profiles block mapping profile name to a list of enabled module names
- [x] #2 A default_profile key selects the active profile; commands accept a --profile flag to override it for a single run
- [x] #3 Config exposes a helper (is_module_enabled(name)) that callers use instead of checking raw config directly
- [x] #4 Modules omitted from every profile default to disabled, not enabled, to avoid silently exposing a source nobody opted into
- [x] #5 Unit tests cover default profile selection, --profile override, and an unconfigured/missing profiles block
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add Config.get_profiles() reading a profiles dict from config.yaml (default {})
2. Add Config.get_default_profile() reading default_profile (default None)
3. Add Config.is_module_enabled(name, profile=None): resolves profile arg -> default_profile -> None; missing profile/profiles block or module not listed all resolve to False
4. Unit tests: default profile selection, explicit profile override, module not in any profile, missing profiles block entirely
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Added Config.get_profiles(), get_default_profile(), and is_module_enabled(name, profile=None). Resolution order: explicit profile arg -> default_profile -> disabled. Any unresolved profile, missing profiles block, or module absent from the resolved profile all resolve to False. No CLI wiring yet - that happens in task-36s --profile flag. Tests: tests/unit/test_config.py (TestModuleProfiles, 6 cases). ruff check/format and ty check pass.
<!-- SECTION:NOTES:END -->
