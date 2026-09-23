import os
import runpy
import subprocess
from pathlib import Path

import pytest

CONNECT = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/connect_chatgpt.py"))
configure = CONNECT["configure"]
prepare_config = CONNECT["prepare_config"]


SAMPLE = """control_plane:
  tunnel_id: tunnel_0123456789abcdef0123456789abcdef
  api_key: ${OPENAI_API_KEY}
health:
  listen_addr: 127.0.0.1:0
mcp:
  command: /private/launch.sh
"""
TUNNEL_ID = "tunnel_0123456789abcdef0123456789abcdef"


def test_prepare_config_references_private_key_without_embedding_it(tmp_path):
    result = prepare_config(SAMPLE, tmp_path / "runtime-key", tmp_path / "health.url")
    assert f'api_key: "file:{tmp_path / "runtime-key"}"' in result
    assert f'url_file: "{tmp_path / "health.url"}"' in result
    assert result.count("url_file:") == 1
    with pytest.raises(ValueError, match="格式已變更"):
        prepare_config(SAMPLE.replace("api_key:", "credential:"), tmp_path / "key", tmp_path / "url")


def test_configure_keeps_existing_profile_on_unknown_official_layout(tmp_path, monkeypatch):
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    launch = state / "launch.sh"
    launch.write_text("#!/bin/sh\n")
    launch.chmod(0o700)
    profiles = state / "tunnel-profiles"
    profiles.mkdir(mode=0o700)
    config = profiles / "local-workspace.yaml"
    config.write_text("existing: true\n")
    config.chmod(0o600)
    client = tmp_path / "tunnel-client"
    client.write_text("")
    client.chmod(0o700)

    def fake_run(command, **_kwargs):
        Path(command[command.index("--profile-dir") + 1], "local-workspace.yaml").write_text(
            SAMPLE.replace("api_key:", "credential:")
        )
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(ValueError, match="格式已變更"):
        configure(state, client, TUNNEL_ID, "sk-test-secret-000000000000")
    assert config.read_text() == "existing: true\n"
    assert not (state / "runtime-key").exists()


def test_configure_stores_secret_privately_and_runs_doctor(tmp_path, monkeypatch):
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    launch = state / "launch.sh"
    launch.write_text("#!/bin/sh\n")
    launch.chmod(0o700)
    client = tmp_path / "tunnel-client"
    client.write_text("")
    client.chmod(0o700)
    calls = []

    def fake_run(command, **_kwargs):
        calls.append(command)
        if "init" in command:
            Path(command[command.index("--profile-dir") + 1], "local-workspace.yaml").write_text(SAMPLE)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    config = configure(state, client, TUNNEL_ID, "sk-test-secret-000000000000")
    key = state / "runtime-key"
    assert key.read_text() == "sk-test-secret-000000000000\n"
    assert "sk-test-secret" not in config.read_text()
    assert os.stat(key).st_mode & 0o077 == 0
    assert os.stat(config).st_mode & 0o077 == 0
    assert calls[-1][1] == "doctor"
    assert configure(state, client, TUNNEL_ID, None) == config


def test_failed_doctor_leaves_no_new_key_or_profile(tmp_path, monkeypatch):
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    launch = state / "launch.sh"
    launch.write_text("#!/bin/sh\n")
    launch.chmod(0o700)
    client = tmp_path / "tunnel-client"
    client.write_text("")
    client.chmod(0o700)

    def fake_run(command, **_kwargs):
        if "init" in command:
            Path(command[command.index("--profile-dir") + 1], "local-workspace.yaml").write_text(SAMPLE)
        else:
            raise subprocess.CalledProcessError(1, command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(subprocess.CalledProcessError):
        configure(state, client, TUNNEL_ID, "sk-test-secret-000000000000")
    assert not (state / "runtime-key").exists()
    assert not (state / "tunnel-profiles/local-workspace.yaml").exists()
