from app.tools import create_all_tools_registry, create_read_only_registry


def test_create_read_only_registry_registers_file_tools():
    registry = create_read_only_registry()

    assert [schema["name"] for schema in registry.schemas()] == [
        "grep",
        "list_dir",
        "read_file",
    ]


def test_create_all_tools_registry_includes_all_tools():
    registry = create_all_tools_registry()

    assert [schema["name"] for schema in registry.schemas()] == [
        "grep",
        "list_dir",
        "read_file",
        "edit_file",
        "write_file",
        "bash",
    ]
