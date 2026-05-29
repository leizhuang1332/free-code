from __future__ import annotations

from pathlib import Path


class WorkspacePathError(ValueError):
    pass


def resolve_workspace_path(workspace: Path, raw_path: str) -> Path:
    root = workspace.resolve()
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = root / candidate

    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise WorkspacePathError(f"path escapes workspace: {raw_path}") from exc

    return resolved
