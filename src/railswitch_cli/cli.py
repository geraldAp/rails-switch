import argparse
import shutil
from pathlib import Path


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
            print(
                f"Cannot initialize RailSwitch: "
                f"{target_path} already exists."
            )
            return

        template_path = Path(__file__).parent / "templates" / "payments"

        shutil.copytree(
            template_path,
            target_path,
        )

        print(f"RailSwitch initialized at: {target_path}")