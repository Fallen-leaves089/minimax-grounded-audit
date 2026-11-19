#!/usr/bin/env python3
"""Install minimax-grounded-audit as a standalone MiniMax Code skill."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from install_common import SKILL_NAME, InstallError, install_to


def personal_skills_dir() -> Path:
    return Path.home() / ".agents" / "skills"


def destination_for(
    scope: str | None,
    project: Path | None,
    skills_dir: Path | None,
) -> Path:
    if skills_dir is not None:
        if scope is not None or project is not None:
            raise InstallError("--skills-dir cannot be combined with --scope or --project")
        return skills_dir.expanduser() / SKILL_NAME

    if scope == "project":
        if project is None:
            raise InstallError("--project is required with --scope project")
        project = project.expanduser().resolve()
        if not project.is_dir():
            raise InstallError(f"project directory does not exist: {project}")
        return project / ".minimax" / "skills" / SKILL_NAME

    if project is not None:
        raise InstallError("--project is only valid with --scope project")
    return personal_skills_dir() / SKILL_NAME


def install(
    scope: str | None,
    project: Path | None,
    skills_dir: Path | None,
    force: bool,
    dry_run: bool,
) -> Path:
    return install_to(destination_for(scope, project, skills_dir), force, dry_run)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install project-health-audit as a standalone MiniMax Code skill."
    )
    parser.add_argument(
        "--scope",
        choices=("personal", "project"),
        default=None,
        help="personal installs under ~/.agents/skills; project installs under <repo>/.minimax/skills.",
    )
    parser.add_argument(
        "--project",
        type=Path,
        help="Repository root for --scope project.",
    )
    parser.add_argument(
        "--skills-dir",
        type=Path,
        help="Explicit skill root, such as ~/.agents/skills or another configured root.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite runtime files in an existing installation; unrelated files are preserved.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the destination and files without writing.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.skills_dir is not None and (args.scope is not None or args.project is not None):
        print("error: --skills-dir cannot be combined with --scope or --project", file=sys.stderr)
        return 2
    scope = args.scope or ("project" if args.project else "personal")
    if args.scope == "personal" and args.project:
        print("error: --project requires --scope project", file=sys.stderr)
        return 2
    try:
        destination = install(
            None if args.skills_dir else scope,
            args.project,
            args.skills_dir,
            args.force,
            args.dry_run,
        )
    except InstallError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.dry_run:
        print("Dry run only; no files were written.")
        return 0

    print(f"Installed {SKILL_NAME} to {destination}")
    print(f"Invoke /{SKILL_NAME} in MiniMax Code; use /skills to confirm discovery.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
