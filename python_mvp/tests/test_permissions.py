from app.permissions import PermissionMode, PermissionPolicy, ToolCapability


def test_allow_all_allows_every_capability():
    policy = PermissionPolicy(PermissionMode.ALLOW_ALL)

    assert policy.can_use_tool("read_file", ToolCapability.READ) is True
    assert policy.can_use_tool("write_file", ToolCapability.WRITE) is True
    assert policy.can_use_tool("shell", ToolCapability.EXECUTE) is True


def test_read_only_allows_read_and_denies_write_execute():
    policy = PermissionPolicy(PermissionMode.READ_ONLY)

    assert policy.can_use_tool("read_file", ToolCapability.READ) is True
    assert policy.can_use_tool("write_file", ToolCapability.WRITE) is False
    assert policy.can_use_tool("shell", ToolCapability.EXECUTE) is False


def test_deny_all_denies_every_capability():
    policy = PermissionPolicy(PermissionMode.DENY_ALL)

    assert policy.can_use_tool("read_file", ToolCapability.READ) is False
    assert policy.can_use_tool("write_file", ToolCapability.WRITE) is False
