"""Tests for frontmatter edits that leave untouched keys exactly as written."""

import pytest

from taskbridge import frontmatter

NOTE = """---
fileClass: task
tags: ['backend', 'ops']
aliases:
  - one
  - two
due: ''
---

# Title
"""


class TestSplitJoin:
    @pytest.mark.parametrize(
        "text",
        [NOTE, "---\n---\nbody\n", "---\na: 1\n---\n", "---\na: 1\n---\n\n---\nnot fm\n"],
    )
    def test_round_trips_exactly(self, text):
        lines, body = frontmatter.split(text)
        assert lines is not None
        assert frontmatter.join(lines, body) == text

    def test_no_frontmatter(self):
        assert frontmatter.split("# Title\n") == (None, "# Title\n")

    def test_unterminated(self):
        with pytest.raises(frontmatter.FrontmatterError, match="unterminated"):
            frontmatter.split("---\na: 1\n")

    @pytest.mark.parametrize("inner", ["a: [", "- just\n- a list"])
    def test_load_rejects_invalid_or_non_mapping(self, inner):
        with pytest.raises(frontmatter.FrontmatterError):
            frontmatter.load(inner.split("\n"))


class TestSetList:
    def lines(self):
        lines, _ = frontmatter.split(NOTE)
        assert lines is not None
        return lines

    def test_replaces_flow_list_in_place_leaving_other_lines(self):
        result = frontmatter.set_list(self.lines(), "tags", ["backend", "backlog/my repo"])

        assert result == [
            "fileClass: task",
            "tags:",
            "  - backend",
            "  - backlog/my repo",
            "aliases:",
            "  - one",
            "  - two",
            "due: ''",
        ]

    def test_replaces_block_list(self):
        result = frontmatter.set_list(self.lines(), "aliases", ["three"])

        assert frontmatter.load(result)["aliases"] == ["three"]
        assert result[-1] == "due: ''"

    def test_handles_unindented_block_list(self):
        result = frontmatter.set_list(["tags:", "- a", "- b", "x: 1"], "tags", ["c"])

        assert result == ["tags:", "  - c", "x: 1"]

    def test_appends_missing_key(self):
        result = frontmatter.set_list(self.lines(), "backlog_tasks", ["repo/TASK-1"])

        assert result[: len(self.lines())] == self.lines()
        assert frontmatter.load(result)["backlog_tasks"] == ["repo/TASK-1"]

    def test_does_not_touch_keys_sharing_a_prefix(self):
        result = frontmatter.set_list(["tags_extra: x", "tags: []"], "tags", ["a"])

        assert result == ["tags_extra: x", "tags:", "  - a"]

    def test_empty_list(self):
        assert frontmatter.set_list(["tags:", "  - a"], "tags", []) == ["tags: []"]

    @pytest.mark.parametrize("value", ["it's", "a: b", "#hash", "- dash", "yes", "1.0", "ü"])
    def test_awkward_values_round_trip(self, value):
        result = frontmatter.set_list([], "k", [value])

        assert frontmatter.load(result)["k"] == [value]
