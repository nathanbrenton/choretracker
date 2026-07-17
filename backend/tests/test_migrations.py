"""Smoke tests for the ChoreTracker migration environment."""

from pathlib import Path


def test_alembic_configuration_files_exist() -> None:
    """The project should retain its migration configuration and scripts."""

    project_root = Path(__file__).resolve().parents[2]

    assert (project_root / "alembic.ini").is_file()
    assert (project_root / "backend" / "migrations" / "env.py").is_file()
    assert (project_root / "backend" / "migrations" / "versions").is_dir()
