from pathlib import Path

import pytest

from app.tool_registry import ToolContext
from app.tools.list_dir import ListDirTool
from app.tools.path_guard import WorkspacePathError, resolve_workspace_path
from app.tools.read_file import ReadFileTool


# --- path guard ---

def test_resolve_workspace_path_allows_relative_path_inside_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "README.md"
    target.write_text("hello", encoding="utf-8")

    resolved = resolve_workspace_path(workspace, "README.md")

    assert resolved == target.resolve()


def test_resolve_workspace_path_rejects_parent_escape(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    with pytest.raises(WorkspacePathError, match="path escapes workspace"):
        resolve_workspace_path(workspace, "../secret.txt")


def test_resolve_workspace_path_rejects_absolute_escape(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("secret", encoding="utf-8")

    with pytest.raises(WorkspacePathError, match="path escapes workspace"):
        resolve_workspace_path(workspace, str(outside))


# --- list_dir ---

def test_list_dir_lists_names_sorted(tmp_path):
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "subdir").mkdir()
    tool = ListDirTool()

    result = tool.run({"path": "."}, ToolContext(workspace=tmp_path))

    assert result.ok is True
    assert result.content.splitlines() == ["a.txt", "b.txt", "subdir/"]


def test_list_dir_rejects_file_path(tmp_path):
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    tool = ListDirTool()

    result = tool.run({"path": "a.txt"}, ToolContext(workspace=tmp_path))

    assert result.ok is False
    assert "not a directory" in result.content


def test_list_dir_rejects_workspace_escape(tmp_path):
    tool = ListDirTool()

    result = tool.run({"path": ".."}, ToolContext(workspace=tmp_path))

    assert result.ok is False
    assert "path escapes workspace" in result.content


# --- read_file ---

def test_read_file_reads_text(tmp_path):
    (tmp_path / "README.md").write_text("hello", encoding="utf-8")
    tool = ReadFileTool(max_bytes=100)

    result = tool.run({"path": "README.md"}, ToolContext(workspace=tmp_path))

    assert result.ok is True
    assert result.content == "hello"


def test_read_file_rejects_directory(tmp_path):
    (tmp_path / "subdir").mkdir()
    tool = ReadFileTool(max_bytes=100)

    result = tool.run({"path": "subdir"}, ToolContext(workspace=tmp_path))

    assert result.ok is False
    assert "not a file" in result.content


def test_read_file_rejects_large_file(tmp_path):
    (tmp_path / "large.txt").write_text("abcdef", encoding="utf-8")
    tool = ReadFileTool(max_bytes=5)

    result = tool.run({"path": "large.txt"}, ToolContext(workspace=tmp_path))

    assert result.ok is False
    assert "file too large" in result.content


def test_read_file_rejects_workspace_escape(tmp_path):
    tool = ReadFileTool(max_bytes=100)

    result = tool.run({"path": "../secret.txt"}, ToolContext(workspace=tmp_path))

    assert result.ok is False
    assert "path escapes workspace" in result.content
