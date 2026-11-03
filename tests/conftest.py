"""共用夹具：TestClient（mock 模型、不限流），指标在每个用例前清零。"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import server.app as app_module  # noqa: E402
import server.audit as audit_module  # noqa: E402
import server.metrics as metrics_module  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    metrics_module.reset()
    monkeypatch.setattr(audit_module, 'AUDIT_DIR', tmp_path / 'audit')
    monkeypatch.setattr(app_module, 'API_KEY', '')      # 强制 mock，不打外网
    monkeypatch.setattr(app_module, 'RATE_LIMIT', 10_000)
    with TestClient(app_module.app) as c:
        yield c
    metrics_module.reset()
