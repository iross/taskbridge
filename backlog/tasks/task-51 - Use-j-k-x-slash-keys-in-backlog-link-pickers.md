---
id: TASK-51
title: Use j/k/x/slash keys in backlog link pickers
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-30 15:42'
updated_date: '2026-10-30 15:44'
labels:
  - backlog
dependencies: []
priority: medium
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
backlog link's fzf pickers open in search mode, so moving needs the arrow keys and marking needs TAB. Browsing a list with j/k, marking with x and searching only after pressing / is quicker and matches the user's editor habits.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Both backlog link pickers open in browse mode with the search input hidden; j and k move down and up
- [x] #2 In the backlog task picker x marks or unmarks the current task and Enter links every marked task (or the current one if none are marked)
- [x] #3 / shows the search input; while searching, j, k, x and / are typed into the query
- [x] #4 Esc while searching returns to browse mode keeping the filter; Esc while browsing cancels without linking
- [x] #5 Each picker's header shows the keys
- [x] #6 task select keeps its current fzf behaviour
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. fzf_args builds the picker command line; browse_keys adds --no-input and the j/k/x/slash/esc bindings plus a header hint
2. Both backlog link pickers use browse_keys; task select does not
3. Integration test drives real fzf through a pty with real keystrokes
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
- main.py: fzf_args(prompt, header, multi, browse_keys, extra_args) builds the command; _run_fzf(lines, args) runs it. With browse_keys: --no-input (typing is ignored while the input is hidden), --bind j:down,k:up,x:toggle (multi only), /:show-input+unbind(j,k,x,/), and esc:transform that prints abort when $FZF_INPUT_STATE is hidden, else hide-input+rebind(...). The header gains a key hint line.
- Both backlog link pickers pass browse_keys=True; pick_task_with_fzf defaults to False so task select is unchanged (asserted in test_task_select.py). Arrow keys and TAB still work.
- tests/integration/test_fzf_browse_keys.py runs real fzf (0.74) in a 40x120 pty and sends keystrokes: j/x multi-mark, x unmark + k, Enter with no marks, / with x/k/i typed into the query, Esc in search keeps the filter and re-enables x, Esc while browsing cancels, x ignored in the single picker. Removing the unbind or the Esc transform each fails a test. ~20s, so it runs under just test-all, not the pre-commit unit tests.
- Requires an fzf with --no-input and FZF_INPUT_STATE (0.59+).
<!-- SECTION:NOTES:END -->
