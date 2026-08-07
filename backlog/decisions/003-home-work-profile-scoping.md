# ADR-003: Home/Work Profile Scoping for taskbridge Modules

## Status

**Proposed** - 2026-08-07

## Context

The inbox report (ADR-002) will eventually cover a work-only source (Apple
Mail) alongside sources relevant in any context (Obsidian, Todoist). Home
and work run on separate machines, and Mail is exclusively a work inbox —
there's no plan to track personal email through taskbridge. Without any
gating, running `inbox report` at home would still attempt the Mail
adapter, which is either pointless (no work account configured on that
machine) or actively unwanted (surfacing a work inbox in a home context).

Because the machines are already separate, module state itself doesn't
need cross-machine awareness — each machine's `config.yaml` only needs to
know its own context.

## Decision

Add a **module-level profile toggle**, not per-account or per-instance
filtering. `config.yaml` gains:

```yaml
default_profile: home
profiles:
  home:
    enabled_modules: [obsidian_inbox, todoist_inbox]
  work:
    enabled_modules: [obsidian_inbox, todoist_inbox, mail, drafts]
```

`default_profile` is set once per machine. Commands accept an optional
`--profile` flag to preview another profile's view without editing config.
A module not listed in the active profile is skipped entirely — not run,
not shown as a zero count — so `inbox report` on the home machine never
attempts to reach Mail at all.

This is deliberately coarser than per-account tagging (e.g. tagging
individual mailboxes or Obsidian folders with a profile): there is
currently no case requiring that granularity, since Mail is single-purpose
and Obsidian/Todoist sources are relevant in both contexts. If a future
source needs finer scoping, that's a separate decision when it's actually
needed.

## Implementation

- `Config.is_module_enabled(name, profile=None)` resolves the active
  profile (explicit arg, else `--profile` flag, else `default_profile`)
  and checks membership in that profile's `enabled_modules`
- Modules absent from every profile default to disabled — an
  unconfigured module never silently appears
- `inbox report` consults this before invoking each adapter; adapters
  themselves stay unaware of profiles entirely

## Consequences

### Positive
- Each adapter stays simple — profile logic lives in one place (config +
  the aggregator), not duplicated per adapter
- Machines don't need to coordinate; each just sets its own
  `default_profile` once

### Negative
- Coarse toggle can't express "mail module on, but only this mailbox" —
  acceptable today since that case doesn't exist, but would need revisiting
  if a mixed-account scenario ever comes up

### Neutral
- No auto-detection of "which context am I in" (network, location, etc.) —
  explicit config only, consistent with avoiding speculative features

## References

- ADR-002: Unified Location-Based Inbox Model for Cross-Tool Triage
- Implementation breakdown for this decision: see backlog tasks created alongside it
