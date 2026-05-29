"""Tests for GrepTool."""

import sys
import tempfile
from pathlib import Path

# Ensure the project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.tools.grep import GrepTool
from app.tool_registry import ToolContext


def test_schema():
    tool = GrepTool()
    schema = tool.schema()
    assert schema["name"] == "grep"
    assert "pattern" in schema["input_schema"]["properties"]
    assert "path" in schema["input_schema"]["properties"]
    assert schema["input_schema"]["required"] == ["pattern", "path"]


def test_basic_search():
    tool = GrepTool()
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        (tmp / "hello.txt").write_text("hello world\nfoo bar\nhello again\n")
        (tmp / "data.txt").write_text("good morning\nhello there\nbye\n")
        ctx = ToolContext(workspace=tmp)

        result = tool.run({"pattern": "hello", "path": str(tmp)}, ctx)
        assert result.ok, f"expected ok, got: {result.content}"
        assert "hello.txt:1:hello world" in result.content
        assert "hello.txt:3:hello again" in result.content
        assert "data.txt:2:hello there" in result.content
        assert "Found 3 match(es)" in result.content


def test_no_match():
    tool = GrepTool()
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        (tmp / "hello.txt").write_text("hello world\n")
        ctx = ToolContext(workspace=tmp)
        result = tool.run({"pattern": "zzzz_nonexistent", "path": str(tmp)}, ctx)
        assert result.ok
        assert "No matches found" in result.content


def test_max_results():
    tool = GrepTool()
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        (tmp / "f.txt").write_text("match\nmatch\nmatch\nmatch\nmatch\n")
        ctx = ToolContext(workspace=tmp)
        result = tool.run({"pattern": "match", "path": str(tmp), "max_results": 2}, ctx)
        assert result.ok
        # Count non-empty lines: summary + 2 matches
        non_empty = [l for l in result.content.split("\n") if l.strip()]
        assert len(non_empty) == 3, f"expected 3 non-empty lines, got {len(non_empty)}"


def test_fixed_string():
    tool = GrepTool()
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        # A pattern that is special in regex
        (tmp / "f.txt").write_text("hello.world\nhelloxworld\n")
        ctx = ToolContext(workspace=tmp)
        # As regex, '.' matches any char, so both lines match
        result_regex = tool.run({"pattern": "hello.world", "path": str(tmp / "f.txt")}, ctx)
        assert result_regex.ok
        assert "2 match" in result_regex.content

        # As fixed string, only the literal '.' line matches
        result_fixed = tool.run(
            {"pattern": "hello.world", "path": str(tmp / "f.txt"), "fixed_string": True}, ctx
        )
        assert result_fixed.ok
        assert "hello.world" in result_fixed.content
        assert "helloxworld" not in result_fixed.content


def test_case_insensitive():
    tool = GrepTool()
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        (tmp / "f.txt").write_text("Hello\nHELLO\nhello\n")
        ctx = ToolContext(workspace=tmp)
        # Case sensitive: only exact matches
        r1 = tool.run({"pattern": "hello", "path": str(tmp / "f.txt")}, ctx)
        assert r1.ok
        assert "HELLO" not in r1.content

        # Case insensitive: matches all
        r2 = tool.run(
            {"pattern": "hello", "path": str(tmp / "f.txt"), "case_insensitive": True}, ctx
        )
        assert r2.ok
        assert "Hello" in r2.content
        assert "HELLO" in r2.content


def test_invalid_regex():
    tool = GrepTool()
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        (tmp / "f.txt").write_text("hello")
        ctx = ToolContext(workspace=tmp)
        result = tool.run({"pattern": "[invalid", "path": str(tmp / "f.txt")}, ctx)
        assert not result.ok
        assert "invalid regex" in result.content


def test_path_escape():
    tool = GrepTool()
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        ctx = ToolContext(workspace=tmp)
        result = tool.run({"pattern": "test", "path": str(tmp / ".." / ".." / "etc")}, ctx)
        assert not result.ok
        assert "escapes workspace" in result.content


def test_binary_file():
    tool = GrepTool()
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        (tmp / "bin.bin").write_bytes(b"\x00\x01hello\xff\xfe")
        ctx = ToolContext(workspace=tmp)
        result = tool.run({"pattern": "hello", "path": str(tmp / "bin.bin")}, ctx)
        assert result.ok
        assert "No matches found" in result.content


def test_not_exists():
    tool = GrepTool()
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        ctx = ToolContext(workspace=tmp)
        result = tool.run({"pattern": "x", "path": str(tmp / "nonexistent")}, ctx)
        assert not result.ok
        assert "does not exist" in result.content


def test_single_file():
    tool = GrepTool()
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        f = tmp / "single.txt"
        f.write_text("line1\nline2\nline3\n")
        ctx = ToolContext(workspace=tmp)
        result = tool.run({"pattern": "line2", "path": str(f)}, ctx)
        assert result.ok
        assert "single.txt:2:line2" in result.content


def test_hidden_files():
    tool = GrepTool()
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        (tmp / "visible.txt").write_text("secret data\n")
        (tmp / ".hidden.txt").write_text("secret data\n")
        ctx = ToolContext(workspace=tmp)

        # Without include_hidden, should only find in visible.txt
        r1 = tool.run({"pattern": "secret", "path": str(tmp)}, ctx)
        assert r1.ok
        assert "visible.txt" in r1.content
        assert ".hidden.txt" not in r1.content

        # With include_hidden, should find in both
        r2 = tool.run({"pattern": "secret", "path": str(tmp), "include_hidden": True}, ctx)
        assert r2.ok
        assert "visible.txt" in r2.content
        assert ".hidden.txt" in r2.content


def test_empty_pattern():
    tool = GrepTool()
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        ctx = ToolContext(workspace=tmp)
        result = tool.run({"pattern": "", "path": str(tmp)}, ctx)
        assert not result.ok
        assert "non-empty" in result.content


def test_empty_path():
    tool = GrepTool()
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        ctx = ToolContext(workspace=tmp)
        result = tool.run({"pattern": "test", "path": ""}, ctx)
        assert not result.ok
        assert "non-empty" in result.content
