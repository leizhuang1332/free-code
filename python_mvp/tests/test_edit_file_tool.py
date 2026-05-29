from pathlib import Path

from app.tool_registry import ToolContext
from app.tools.edit_file import EditFileTool


def test_edit_file_replaces_single_occurrence(tmp_path):
    file = tmp_path / "test.txt"
    file.write_text("hello world\nthis is a test\nhello again\n")

    tool = EditFileTool(max_bytes=100)
    result = tool.run(
        {"path": "test.txt", "old_string": "this is a test", "new_string": "EDITED"},
        ToolContext(workspace=tmp_path),
    )

    assert result.ok is True
    assert "Successfully edited" in result.content
    assert file.read_text(encoding="utf-8") == "hello world\nEDITED\nhello again\n"


def test_edit_file_rejects_not_found(tmp_path):
    file = tmp_path / "test.txt"
    file.write_text("hello world\n")

    tool = EditFileTool(max_bytes=100)
    result = tool.run(
        {"path": "test.txt", "old_string": "nonexistent", "new_string": "x"},
        ToolContext(workspace=tmp_path),
    )

    assert result.ok is False
    assert "old_string was not found" in result.content


def test_edit_file_rejects_multiple_occurrences(tmp_path):
    file = tmp_path / "test.txt"
    file.write_text("hello\nhello\nworld\n")

    tool = EditFileTool(max_bytes=100)
    result = tool.run(
        {"path": "test.txt", "old_string": "hello", "new_string": "hi"},
        ToolContext(workspace=tmp_path),
    )

    assert result.ok is False
    assert "appears 2 times" in result.content


def test_edit_file_rejects_workspace_escape(tmp_path):
    tool = EditFileTool(max_bytes=100)
    result = tool.run(
        {"path": "../secret.txt", "old_string": "x", "new_string": "y"},
        ToolContext(workspace=tmp_path),
    )

    assert result.ok is False
    assert "path escapes workspace" in result.content


def test_edit_file_rejects_empty_old_string(tmp_path):
    tool = EditFileTool(max_bytes=100)
    result = tool.run(
        {"path": "test.txt", "old_string": "", "new_string": "x"},
        ToolContext(workspace=tmp_path),
    )

    assert result.ok is False
    assert "old_string must be a non-empty string" in result.content


def test_edit_file_rejects_missing_path(tmp_path):
    tool = EditFileTool(max_bytes=100)
    result = tool.run(
        {"old_string": "x", "new_string": "y"},
        ToolContext(workspace=tmp_path),
    )

    assert result.ok is False
    assert "path must be a non-empty string" in result.content


def test_edit_file_rejects_large_file(tmp_path):
    file = tmp_path / "large.txt"
    file.write_text("a" * 100)

    tool = EditFileTool(max_bytes=50)
    result = tool.run(
        {"path": "large.txt", "old_string": "a" * 50, "new_string": "b"},
        ToolContext(workspace=tmp_path),
    )

    assert result.ok is False
    assert "file too large" in result.content


def test_edit_file_rejects_nonexistent_file(tmp_path):
    tool = EditFileTool(max_bytes=100)
    result = tool.run(
        {"path": "nonexistent.txt", "old_string": "x", "new_string": "y"},
        ToolContext(workspace=tmp_path),
    )

    assert result.ok is False
    assert "path does not exist" in result.content


def test_edit_file_rejects_directory_path(tmp_path):
    tool = EditFileTool(max_bytes=100)
    result = tool.run(
        {"path": ".", "old_string": "x", "new_string": "y"},
        ToolContext(workspace=tmp_path),
    )

    assert result.ok is False
    assert "not a file" in result.content
