"""The real backlog CLI keeps a parent link written by taskbridge (ADR-004)."""

import shutil
import subprocess
from pathlib import Path

import pytest

from taskbridge import backlog

REPO_CONFIG = Path(__file__).parents[2] / "backlog" / "config.yml"

pytestmark = pytest.mark.skipif(shutil.which("backlog") is None, reason="backlog CLI not installed")


def test_backlog_edit_keeps_parent_link(tmp_path):
    (tmp_path / "backlog" / "tasks").mkdir(parents=True)
    shutil.copy(REPO_CONFIG, tmp_path / "backlog" / "config.yml")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    path = tmp_path / "backlog" / "tasks" / "task-1 - Thing.md"
    path.write_text(
        "---\nid: TASK-1\ntitle: Thing\nstatus: To Do\nassignee: []\n"
        "created_date: '2026-10-30 12:00'\nlabels: []\ndependencies: []\n---\n\n"
        "## Description\n\n<!-- SECTION:DESCRIPTION:BEGIN -->\nx\n"
        "<!-- SECTION:DESCRIPTION:END -->\n"
    )
    backlog.set_parent_task(path, "PARENT1")

    subprocess.run(
        ["backlog", "task", "edit", "1", "-s", "In Progress", "--add-label", "x"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    assert "status: In Progress" in path.read_text()
    assert backlog.read_references(path) == [backlog.todoist_task_url("PARENT1")]
