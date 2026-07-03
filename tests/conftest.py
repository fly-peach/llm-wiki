"""pytest 共享配置"""

import pytest


@pytest.fixture
def sample_workspace_path(tmp_path):
    """创建临时工作区目录"""
    ws = tmp_path / "test-workspace"
    ws.mkdir()
    (ws / "wiki").mkdir()
    return ws
