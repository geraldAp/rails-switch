import subprocess
from pathlib import Path

from railswitch_cli import cli
from railswitch_cli.cli import (
    GENERATED_RUNTIME_DEPENDENCIES,
    DependencyInstallStatus,
    install_generated_dependencies,
    main,
    update_env_example,
)

RAILSWITCH_VARIABLES = (
    "PAYSTACK_GH_SECRET_KEY",
    "PAYSTACK_ZA_SECRET_KEY",
    "PAYSTACK_CALLBACK_URL",
    "BACH_API_KEY",
    "BACH_BASE_URL",
    "STRIPE_SECRET_KEY",
    "STRIPE_SUCCESS_URL",
    "STRIPE_CANCEL_URL",
)


def test_update_env_example_creates_file_with_all_railswitch_variables(
    tmp_path: Path,
) -> None:
    env_path = tmp_path / ".env.example"

    updated = update_env_example(env_path)

    assert updated is True
    content = env_path.read_text()
    for variable in RAILSWITCH_VARIABLES:
        assert f"{variable}=" in content


def test_update_env_example_preserves_existing_content_and_values(
    tmp_path: Path,
) -> None:
    env_path = tmp_path / ".env.example"
    env_path.write_text(
        "DATABASE_URL=sqlite:///app.db\nPAYSTACK_GH_SECRET_KEY=existing-placeholder\n"
    )

    updated = update_env_example(env_path)

    assert updated is True
    content = env_path.read_text()
    assert "DATABASE_URL=sqlite:///app.db" in content
    assert "PAYSTACK_GH_SECRET_KEY=existing-placeholder" in content
    assert content.count("PAYSTACK_GH_SECRET_KEY=") == 1
    assert "PAYSTACK_ZA_SECRET_KEY=" in content


def test_update_env_example_does_not_duplicate_existing_railswitch_variables(
    tmp_path: Path,
) -> None:
    env_path = tmp_path / ".env.example"
    env_path.write_text(
        "\n".join(f"{variable}=existing-value" for variable in RAILSWITCH_VARIABLES)
        + "\n"
    )

    updated = update_env_example(env_path)

    assert updated is False
    content = env_path.read_text()
    for variable in RAILSWITCH_VARIABLES:
        assert content.count(f"{variable}=") == 1


def test_init_prints_generated_runtime_dependency_guidance(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["railswitch", "init", "--path", "app/payments"])

    main()

    output = capsys.readouterr().out
    assert "Install required dependencies:" in output
    dependency_command = "uv add httpx2 pydantic-settings"
    assert dependency_command in output
    for dependency in GENERATED_RUNTIME_DEPENDENCIES:
        assert dependency in dependency_command
    for dependency in ("fastapi", "sqlalchemy", "alembic", "pytest", "ruff"):
        assert dependency not in dependency_command


def test_install_generated_dependencies_returns_already_installed(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """[project]
name = "test-app"
version = "0.1.0"
dependencies = [
    "httpx2>=2.12.0",
    "pydantic-settings>=2.15.0",
]
"""
    )

    def fail_if_called(*args, **kwargs) -> None:
        raise AssertionError("subprocess.run should not be called")

    monkeypatch.setattr(cli.subprocess, "run", fail_if_called)

    status = install_generated_dependencies(tmp_path)

    assert status is DependencyInstallStatus.ALREADY_INSTALLED


def test_install_generated_dependencies_installs_missing_dependencies(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "test-app"\nversion = "0.1.0"\ndependencies = []\n'
    )
    calls = []

    def fake_run(command, *, cwd, check) -> None:
        calls.append((command, cwd, check))

    monkeypatch.setattr(cli.shutil, "which", lambda command: "/fake/bin/uv")
    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    status = install_generated_dependencies(tmp_path)

    assert status is DependencyInstallStatus.INSTALLED
    assert calls == [
        (
            ["/fake/bin/uv", "add", "httpx2", "pydantic-settings"],
            tmp_path,
            True,
        )
    ]


def test_install_generated_dependencies_skips_without_pyproject(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def fail_if_called(*args, **kwargs) -> None:
        raise AssertionError("subprocess.run should not be called")

    monkeypatch.setattr(cli.subprocess, "run", fail_if_called)

    status = install_generated_dependencies(tmp_path)

    assert status is DependencyInstallStatus.SKIPPED


def test_install_generated_dependencies_skips_when_uv_is_unavailable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "test-app"\nversion = "0.1.0"\ndependencies = []\n'
    )

    def fail_if_called(*args, **kwargs) -> None:
        raise AssertionError("subprocess.run should not be called")

    monkeypatch.setattr(cli.shutil, "which", lambda command: None)
    monkeypatch.setattr(cli.subprocess, "run", fail_if_called)

    status = install_generated_dependencies(tmp_path)

    assert status is DependencyInstallStatus.SKIPPED


def test_install_generated_dependencies_returns_failed_when_uv_add_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "test-app"\nversion = "0.1.0"\ndependencies = []\n'
    )

    def failing_run(*args, **kwargs) -> None:
        raise subprocess.CalledProcessError(returncode=1, cmd=args[0])

    monkeypatch.setattr(cli.shutil, "which", lambda command: "/fake/bin/uv")
    monkeypatch.setattr(cli.subprocess, "run", failing_run)

    status = install_generated_dependencies(tmp_path)

    assert status is DependencyInstallStatus.FAILED


def test_init_prints_already_installed_dependency_message(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["railswitch", "init", "--path", "app/payments"])
    monkeypatch.setattr(
        cli,
        "install_generated_dependencies",
        lambda project_root: DependencyInstallStatus.ALREADY_INSTALLED,
    )

    main()

    assert (
        "All required RailSwitch dependencies are already installed."
        in capsys.readouterr().out
    )


def test_init_prints_manual_command_when_dependency_installation_fails(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["railswitch", "init", "--path", "app/payments"])
    monkeypatch.setattr(
        cli,
        "install_generated_dependencies",
        lambda project_root: DependencyInstallStatus.FAILED,
    )

    main()

    output = capsys.readouterr().out
    assert "RailSwitch was scaffolded, but dependency installation failed." in output
    assert "uv add httpx2 pydantic-settings" in output
