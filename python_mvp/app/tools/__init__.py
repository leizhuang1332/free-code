"""Built-in MVP tools."""

from app.tool_registry import ToolRegistry
from app.tools.bash import BashTool
from app.tools.list_dir import ListDirTool
from app.tools.read_file import ReadFileTool
from app.tools.write_file import WriteFileTool


def create_read_only_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(ListDirTool())
    registry.register(ReadFileTool())
    return registry


def create_all_tools_registry() -> ToolRegistry:
    registry = create_read_only_registry()
    registry.register(WriteFileTool())
    registry.register(BashTool())
    return registry
