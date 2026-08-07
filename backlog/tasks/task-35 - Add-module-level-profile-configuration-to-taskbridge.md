---
id: TASK-35
title: Add module-level profile configuration to taskbridge
status: To Do
assignee: []
created_date: '2026-08-07 18:53'
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
- [ ] #1 config.yaml supports a profiles block mapping profile name to a list of enabled module names,A default_profile key selects the active profile; commands accept a --profile flag to override it for a single run,Config exposes a helper (e.g. is_module_enabled(name)) that callers use instead of checking raw config directly,Modules omitted from every profile default to disabled, not enabled, to avoid silently exposing a source nobody opted into,Unit tests cover default profile selection, --profile override, and an unconfigured/missing profiles block
<!-- AC:END -->
