from pathlib import Path

from railswitch_cli.cli import GENERATED_RUNTIME_DEPENDENCIES, main, update_env_example

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
