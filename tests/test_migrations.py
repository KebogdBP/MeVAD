from pathlib import Path

import pytest
from sqlalchemy import Engine, create_engine
from sqlalchemy.pool import StaticPool

from mevad.exceptions import MigrationError
from mevad.migrations import MigrationRunner


def test_migration_runner_applies_ordered_files_once(tmp_path: Path) -> None:
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "0001_create_items.sql").write_text(
        "CREATE TABLE items (value TEXT NOT NULL);",
        encoding="utf-8",
    )
    (migrations / "0002_seed_items.sql").write_text(
        "INSERT INTO items (value) VALUES ('one;two');",
        encoding="utf-8",
    )
    engine = _engine()
    runner = MigrationRunner(engine, migrations)

    assert runner.run() == 2
    assert runner.run() == 0
    with engine.connect() as connection:
        values = connection.exec_driver_sql("SELECT value FROM items").scalars().all()
        versions = (
            connection.exec_driver_sql("SELECT version FROM schema_migrations ORDER BY version")
            .scalars()
            .all()
        )

    assert values == ["one;two"]
    assert versions == ["0001", "0002"]
    runner.close()


def test_migration_runner_rejects_changed_applied_file(tmp_path: Path) -> None:
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    migration = migrations / "0001_create_items.sql"
    migration.write_text("CREATE TABLE items (value TEXT);", encoding="utf-8")
    runner = MigrationRunner(_engine(), migrations)
    assert runner.run() == 1

    migration.write_text("CREATE TABLE changed (value TEXT);", encoding="utf-8")

    with pytest.raises(MigrationError, match="checksum has changed"):
        runner.run()
    runner.close()


def test_migration_batch_rolls_back_on_failure(tmp_path: Path) -> None:
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "0001_create_items.sql").write_text(
        "CREATE TABLE items (value TEXT);",
        encoding="utf-8",
    )
    engine = _engine()
    runner = MigrationRunner(engine, migrations)
    assert runner.run() == 1
    (migrations / "0002_seed_items.sql").write_text(
        "INSERT INTO items (value) VALUES ('pending');",
        encoding="utf-8",
    )
    (migrations / "0003_invalid.sql").write_text(
        "THIS IS NOT SQL;",
        encoding="utf-8",
    )

    with pytest.raises(MigrationError, match="migration failed"):
        runner.run()

    with engine.connect() as connection:
        values = connection.exec_driver_sql("SELECT value FROM items").scalars().all()
        versions = (
            connection.exec_driver_sql("SELECT version FROM schema_migrations ORDER BY version")
            .scalars()
            .all()
        )
    assert values == []
    assert versions == ["0001"]
    runner.close()


def test_migration_runner_requires_contiguous_valid_versions(tmp_path: Path) -> None:
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "0001_first.sql").write_text("SELECT 1;", encoding="utf-8")
    (migrations / "0003_third.sql").write_text("SELECT 3;", encoding="utf-8")

    runner = MigrationRunner(_engine(), migrations)

    with pytest.raises(MigrationError, match="contiguous"):
        runner.discover()
    runner.close()


def test_repository_migrations_are_discoverable() -> None:
    runner = MigrationRunner(_engine(), Path("migrations"))

    discovered = runner.discover()

    assert [migration.version for migration in discovered] == [
        "0001",
        "0002",
        "0003",
        "0004",
        "0005",
        "0006",
    ]
    runner.close()


def _engine() -> Engine:
    return create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
