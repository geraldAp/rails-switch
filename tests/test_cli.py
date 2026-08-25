import subprocess
from pathlib import Path

import pytest

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


def test_init_without_providers_generates_all_provider_directories(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["railswitch", "init"])

    main()

    providers_path = tmp_path / "app" / "payments" / "providers"
    assert (providers_path / "paystack").is_dir()
    assert (providers_path / "bach").is_dir()
    assert (providers_path / "stripe").is_dir()


def test_init_with_stripe_generates_only_stripe_wiring_and_environment(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["railswitch", "init", "--providers", "stripe"])

    main()

    payments_path = tmp_path / "app" / "payments"
    providers_path = payments_path / "providers"
    assert (providers_path / "stripe").is_dir()
    assert not (providers_path / "paystack").exists()
    assert not (providers_path / "bach").exists()

    for generated_file in ("config.py", "dependencies.py"):
        content = (payments_path / generated_file).read_text()
        assert "stripe" in content
        assert "paystack" not in content
        assert "bach" not in content

    factory_content = (payments_path / "factory.py").read_text()
    assert "Provider.STRIPE" in factory_content
    assert "Provider.PAYSTACK" not in factory_content
    assert "Provider.BACH" not in factory_content

    env_content = (tmp_path / ".env.example").read_text()
    assert "STRIPE_SECRET_KEY=" in env_content
    assert "PAYSTACK_GH_SECRET_KEY=" not in env_content
    assert "BACH_API_KEY=" not in env_content


def test_init_with_paystack_and_stripe_generates_exactly_those_providers(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv", ["railswitch", "init", "--providers", "paystack", "stripe"]
    )

    main()

    payments_path = tmp_path / "app" / "payments"
    providers_path = payments_path / "providers"
    assert (providers_path / "paystack").is_dir()
    assert (providers_path / "stripe").is_dir()
    assert not (providers_path / "bach").exists()
    dependencies = (payments_path / "dependencies.py").read_text()
    assert "PaystackProvider" in dependencies
    assert "StripeProvider" in dependencies
    assert "BachProvider" not in dependencies
    assert "BachClient" not in dependencies


def test_init_rejects_an_unknown_provider(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv", ["railswitch", "init", "--providers", "not-a-provider"]
    )

    with pytest.raises(SystemExit) as error:
        main()

    assert error.value.code == 2


def test_init_preserves_existing_env_example_for_selected_providers(
    tmp_path: Path, monkeypatch
) -> None:
    (tmp_path / ".env.example").write_text(
        "DATABASE_URL=sqlite:///app.db\nSTRIPE_SECRET_KEY=existing-value\n"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["railswitch", "init", "--providers", "stripe"])

    main()

    content = (tmp_path / ".env.example").read_text()
    assert "DATABASE_URL=sqlite:///app.db" in content
    assert content.count("STRIPE_SECRET_KEY=") == 1
    assert "STRIPE_SUCCESS_URL=" in content
    assert "PAYSTACK_GH_SECRET_KEY=" not in content


def test_init_deduplicates_duplicate_providers(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        ["railswitch", "init", "--providers", "stripe", "stripe", "paystack"],
    )
    monkeypatch.setattr(
        cli,
        "install_generated_dependencies",
        lambda project_root: DependencyInstallStatus.SKIPPED,
    )

    main()

    providers_path = tmp_path / "app" / "payments" / "providers"
    assert (providers_path / "stripe").is_dir()
    assert (providers_path / "paystack").is_dir()
    assert not (providers_path / "bach").exists()
    # ensure exactly two provider dirs plus __init__.py
    provider_dirs = {
        p.name
        for p in providers_path.iterdir()
        if p.is_dir() and p.name != "__pycache__"
    }
    assert provider_dirs == {"stripe", "paystack"}


def test_init_with_paystack_ghana_generates_only_ghana_configuration(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        ["railswitch", "init", "--providers", "paystack", "--countries", "GH"],
    )

    main()

    payments_path = tmp_path / "app" / "payments"
    config = (payments_path / "config.py").read_text()
    dependencies = (payments_path / "dependencies.py").read_text()
    factory = (payments_path / "factory.py").read_text()
    env_example = (tmp_path / ".env.example").read_text()
    assert "paystack_gh_secret_key" in config
    assert "paystack_callback_url" in config
    assert "paystack_za_secret_key" not in config
    assert "Country.GHANA: settings.paystack_gh_secret_key" in dependencies
    assert "SOUTH_AFRICA" not in dependencies
    assert "Country.GHANA: {Provider.PAYSTACK}" in factory
    assert "SOUTH_AFRICA" not in factory
    assert "PAYSTACK_GH_SECRET_KEY=" in env_example
    assert "PAYSTACK_CALLBACK_URL=" in env_example
    assert "PAYSTACK_ZA_SECRET_KEY=" not in env_example


def test_init_with_paystack_south_africa_generates_only_za_configuration(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        ["railswitch", "init", "--providers", "paystack", "--countries", "ZA"],
    )

    main()

    payments_path = tmp_path / "app" / "payments"
    config = (payments_path / "config.py").read_text()
    factory = (payments_path / "factory.py").read_text()
    assert "paystack_za_secret_key" in config
    assert "paystack_gh_secret_key" not in config
    assert "Country.SOUTH_AFRICA: {Provider.PAYSTACK}" in factory
    assert "Country.GHANA" not in factory


def test_init_with_both_paystack_countries_generates_both_capabilities(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "railswitch",
            "init",
            "--providers",
            "paystack",
            "--countries",
            "GH",
            "ZA",
        ],
    )

    main()

    payments_path = tmp_path / "app" / "payments"
    config = (payments_path / "config.py").read_text()
    factory = (payments_path / "factory.py").read_text()
    assert "paystack_gh_secret_key" in config
    assert "paystack_za_secret_key" in config
    assert "Country.GHANA: {Provider.PAYSTACK}" in factory
    assert "Country.SOUTH_AFRICA: {Provider.PAYSTACK}" in factory


def test_init_accepts_stripe_canada_and_rejects_stripe_ghana(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv", ["railswitch", "init", "--providers", "stripe", "--countries", "CA"]
    )
    main()
    assert (
        "Country.CANADA: {Provider.STRIPE}"
        in (tmp_path / "app" / "payments" / "factory.py").read_text()
    )

    monkeypatch.setattr(
        "sys.argv", ["railswitch", "init", "--providers", "stripe", "--countries", "GH"]
    )
    with pytest.raises(SystemExit) as error:
        main()

    assert error.value.code == 2
    assert "do not support countries: GH" in capsys.readouterr().err


def test_init_with_multiple_providers_and_countries_generates_capabilities(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "railswitch",
            "init",
            "--providers",
            "paystack",
            "stripe",
            "--countries",
            "GH",
            "CA",
        ],
    )

    main()

    payments_path = tmp_path / "app" / "payments"
    providers_path = payments_path / "providers"
    assert (providers_path / "paystack").is_dir()
    assert (providers_path / "stripe").is_dir()
    assert not (providers_path / "bach").exists()
    config = (payments_path / "config.py").read_text()
    env_example = (tmp_path / ".env.example").read_text()
    factory = (payments_path / "factory.py").read_text()
    assert "paystack_gh_secret_key" in config
    assert "paystack_za_secret_key" not in config
    assert "BACH_API_KEY=" not in env_example
    assert "PAYSTACK_ZA_SECRET_KEY=" not in env_example
    assert "Country.GHANA: {Provider.PAYSTACK}" in factory
    assert "Country.CANADA: {Provider.STRIPE}" in factory
    assert "SOUTH_AFRICA" not in factory
    assert "UNITED_STATES" not in factory


def test_init_deduplicates_duplicate_countries(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "railswitch",
            "init",
            "--providers",
            "paystack",
            "--countries",
            "GH",
            "GH",
        ],
    )

    main()

    dependencies = (tmp_path / "app" / "payments" / "dependencies.py").read_text()
    assert dependencies.count("Country.GHANA: settings.paystack_gh_secret_key") == 1


def test_init_paystack_gh_only_comment_reflects_selected_country(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        ["railswitch", "init", "--providers", "paystack", "--countries", "GH"],
    )

    main()

    config = (tmp_path / "app" / "payments" / "config.py").read_text()
    assert "# Paystack - Ghana" in config
    assert "# Paystack - Ghana and South Africa" not in config


def test_init_paystack_gh_za_comment_reflects_both_countries(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "railswitch",
            "init",
            "--providers",
            "paystack",
            "--countries",
            "GH",
            "ZA",
        ],
    )

    main()

    config = (tmp_path / "app" / "payments" / "config.py").read_text()
    assert "# Paystack - Ghana and South Africa" in config


def test_init_countries_gh_infers_paystack(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["railswitch", "init", "--countries", "GH"])

    main()

    providers_path = tmp_path / "app" / "payments" / "providers"
    assert (providers_path / "paystack").is_dir()
    assert not (providers_path / "bach").exists()
    assert not (providers_path / "stripe").exists()
    config = (tmp_path / "app" / "payments" / "config.py").read_text()
    assert "# Paystack - Ghana" in config


def test_init_countries_ng_infers_bachs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["railswitch", "init", "--countries", "NG"])

    main()

    providers_path = tmp_path / "app" / "payments" / "providers"
    assert (providers_path / "bach").is_dir()
    assert not (providers_path / "paystack").exists()
    assert not (providers_path / "stripe").exists()


def test_init_countries_ca_infers_stripe(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["railswitch", "init", "--countries", "CA"])

    main()

    providers_path = tmp_path / "app" / "payments" / "providers"
    assert (providers_path / "stripe").is_dir()
    assert not (providers_path / "paystack").exists()
    assert not (providers_path / "bach").exists()
    config = (tmp_path / "app" / "payments" / "config.py").read_text()
    assert "stripe_secret_key" in config
    factory = (tmp_path / "app" / "payments" / "factory.py").read_text()
    assert "Country.CANADA: {Provider.STRIPE}" in factory


def test_init_factory_routes_are_indented(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        ["railswitch", "init", "--providers", "paystack", "--countries", "GH"],
    )

    main()

    factory = (tmp_path / "app" / "payments" / "factory.py").read_text()
    assert "ROUTES = {\n    Country.GHANA: {Provider.PAYSTACK},\n}" in factory
