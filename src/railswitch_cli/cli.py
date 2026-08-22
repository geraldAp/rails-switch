import argparse
import shutil
import subprocess
import tomllib
from enum import StrEnum
from pathlib import Path

ENV_SECTIONS = (
    (
        "Paystack",
        "Ghana and South Africa",
        (
            "PAYSTACK_GH_SECRET_KEY=",
            "PAYSTACK_ZA_SECRET_KEY=",
            "PAYSTACK_CALLBACK_URL=",
        ),
    ),
    (
        "Bachs",
        "Nigeria",
        (
            "BACH_API_KEY=",
            "BACH_BASE_URL=https://sandbox-api.bachs.io",
        ),
    ),
    (
        "Stripe",
        "United States and Canada",
        (
            "STRIPE_SECRET_KEY=",
            "STRIPE_SUCCESS_URL=",
            "STRIPE_CANCEL_URL=",
        ),
    ),
)

GENERATED_RUNTIME_DEPENDENCIES = (
    "httpx2",
    "pydantic-settings",
)


class DependencyInstallStatus(StrEnum):
    INSTALLED = "installed"
    ALREADY_INSTALLED = "already_installed"
    SKIPPED = "skipped"
    FAILED = "failed"


def update_env_example(env_path: Path) -> bool:
    """Append missing RailSwitch environment variables to env_path."""

    existing_content = env_path.read_text() if env_path.exists() else ""

    existing_variables = {
        line.split("=", maxsplit=1)[0].strip()
        for line in existing_content.splitlines()
        if "=" in line and line.split("=", maxsplit=1)[0].strip().isidentifier()
    }

    sections_to_add = []

    for provider, countries, variables in ENV_SECTIONS:
        missing_variables = [
            variable
            for variable in variables
            if variable.split("=", maxsplit=1)[0] not in existing_variables
        ]

        if missing_variables:
            sections_to_add.append(
                "\n".join(
                    (
                        "# ------------------------------------------------",
                        f"# RailSwitch - {provider}",
                        f"# {countries}",
                        "# ------------------------------------------------",
                        *missing_variables,
                    )
                )
            )

    if not sections_to_add:
        return False

    addition = "\n\n".join(sections_to_add) + "\n"

    if existing_content:
        separator = "\n" if existing_content.endswith("\n") else "\n\n"
        env_path.write_text(existing_content + separator + addition)
    else:
        env_path.write_text(addition)

    return True


def install_generated_dependencies(
    project_root: Path,
) -> DependencyInstallStatus:
    pyproject_path = project_root / "pyproject.toml"

    if not pyproject_path.exists():
        return DependencyInstallStatus.SKIPPED

    with pyproject_path.open("rb") as file:
        pyproject = tomllib.load(file)

    project_dependencies = pyproject.get("project", {}).get("dependencies", [])

    all_installed = all(
        any(dependency.startswith(name) for dependency in project_dependencies)
        for name in GENERATED_RUNTIME_DEPENDENCIES
    )

    if all_installed:
        return DependencyInstallStatus.ALREADY_INSTALLED

    uv_path = shutil.which("uv")

    if uv_path is None:
        return DependencyInstallStatus.SKIPPED

    try:
        subprocess.run(
            [
                uv_path,
                "add",
                *GENERATED_RUNTIME_DEPENDENCIES,
            ],
            cwd=project_root,
            check=True,
        )
    except subprocess.CalledProcessError:
        return DependencyInstallStatus.FAILED

    return DependencyInstallStatus.INSTALLED


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="railswitch",
        description="RailSwitch payment scaffolding CLI",
    )

    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser(
        "init",
        help="Initialize RailSwitch in a project",
    )

    init_parser.add_argument(
        "--path",
        default="app/payments",
        help="Target path for the generated RailSwitch module",
    )

    args = parser.parse_args()

    if args.command == "init":
        target_path = Path(args.path)

        print(f"Initializing RailSwitch at: {target_path}")
        print(f"Absolute path: {target_path.resolve()}")

        if target_path.exists():
            print(f"Cannot initialize RailSwitch: {target_path} already exists.")
            return

        template_path = Path(__file__).parent / "templates" / "payments"

        shutil.copytree(
            template_path,
            target_path,
        )

        print(f"RailSwitch initialized at: {target_path}")

        if update_env_example(Path(".env.example")):
            print("Updated .env.example with RailSwitch environment variables.")
        else:
            print(".env.example already contains all RailSwitch variables.")

        dependency_status = install_generated_dependencies(Path.cwd())

        match dependency_status:
            case DependencyInstallStatus.INSTALLED:
                print("Installed required RailSwitch dependencies.")

            case DependencyInstallStatus.ALREADY_INSTALLED:
                print("All required RailSwitch dependencies are already installed.")

            case DependencyInstallStatus.FAILED:
                print("RailSwitch was scaffolded, but dependency installation failed.")
                print("Run: uv add " + " ".join(GENERATED_RUNTIME_DEPENDENCIES))

            case DependencyInstallStatus.SKIPPED:
                print("\nInstall required dependencies:")
                print("  uv add " + " ".join(GENERATED_RUNTIME_DEPENDENCIES))
