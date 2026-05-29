from app.tool_registry import ToolContext
from app.tools.write_file import WriteFileTool


def test_write_file_writes_utf8_text(tmp_path):
    tool = WriteFileTool(max_bytes=100)

    result = tool.run({"path": "notes/a.txt", "content": "hello"}, ToolContext(workspace=tmp_path))

    assert result.ok is True
    assert result.content == "wrote notes/a.txt"
    assert (tmp_path / "notes" / "a.txt").read_text(encoding="utf-8") == "hello"


def test_write_file_rejects_workspace_escape(tmp_path):
    tool = WriteFileTool(max_bytes=100)

    result = tool.run({"path": "../secret.txt", "content": "secret"}, ToolContext(workspace=tmp_path))

    assert result.ok is False
    assert "path escapes workspace" in result.content


def test_write_file_rejects_large_content(tmp_path):
    tool = WriteFileTool(max_bytes=5)

    result = tool.run({"path": "large.txt", "content": "abcdef"}, ToolContext(workspace=tmp_path))

    assert result.ok is False
    assert "content too large" in result.content


def test_write_file_rejects_missing_content(tmp_path):
    tool = WriteFileTool(max_bytes=100)

    result = tool.run({"path": "a.txt"}, ToolContext(workspace=tmp_path))

    assert result.ok is False
    assert "content must be a string" in result.content
