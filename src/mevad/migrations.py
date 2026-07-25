"""Checksum-verified SQL migration runner."""

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import (
    Column,
    DateTime,
    Engine,
    MetaData,
    String,
    Table,
    create_engine,
    insert,
    select,
)

from mevad.exceptions import MigrationError

_MIGRATION_NAME = re.compile(r"^(?P<version>\d{4})_[a-z0-9_]+\.sql$")
_POSTGRES_LOCK_ID = 556_382_641_833_992_513

metadata = MetaData()
schema_migrations = Table(
    "schema_migrations",
    metadata,
    Column("version", String(4), primary_key=True),
    Column("checksum", String(64), nullable=False),
    Column("applied_at", DateTime(timezone=True), nullable=False),
)


@dataclass(frozen=True, slots=True)
class Migration:
    version: str
    path: Path
    checksum: str
    sql: str


class MigrationRunner:
    """Apply ordered SQL files once and reject changed history."""

    def __init__(
        self,
        engine: Engine,
        migrations_directory: Path,
    ) -> None:
        self._engine = engine
        self._directory = migrations_directory

    @classmethod
    def from_url(
        cls,
        database_url: str,
        migrations_directory: Path = Path("migrations"),
    ) -> "MigrationRunner":
        return cls(
            create_engine(database_url, pool_pre_ping=True),
            migrations_directory,
        )

    def run(self) -> int:
        migrations = self.discover()
        metadata.create_all(self._engine, tables=[schema_migrations])
        applied_count = 0
        try:
            with self._engine.begin() as connection:
                if self._engine.dialect.name == "postgresql":
                    connection.exec_driver_sql(f"SELECT pg_advisory_xact_lock({_POSTGRES_LOCK_ID})")
                applied_rows = connection.execute(
                    select(
                        schema_migrations.c.version,
                        schema_migrations.c.checksum,
                    )
                ).all()
                applied: dict[str, str] = {
                    str(row.version): str(row.checksum) for row in applied_rows
                }
                known_versions = {migration.version for migration in migrations}
                unknown = sorted(set(applied) - known_versions)
                if unknown:
                    raise MigrationError(
                        f"Database contains unknown migration version {unknown[0]}."
                    )
                for migration in migrations:
                    previous_checksum = applied.get(migration.version)
                    if previous_checksum is not None:
                        if previous_checksum != migration.checksum:
                            raise MigrationError(
                                f"Migration {migration.version} checksum has changed."
                            )
                        continue
                    for statement in _split_sql(migration.sql):
                        connection.exec_driver_sql(statement)
                    connection.execute(
                        insert(schema_migrations).values(
                            version=migration.version,
                            checksum=migration.checksum,
                            applied_at=datetime.now(UTC),
                        )
                    )
                    applied_count += 1
        except MigrationError:
            raise
        except Exception as error:
            raise MigrationError("Database migration failed.") from error
        return applied_count

    def discover(self) -> tuple[Migration, ...]:
        if not self._directory.is_dir():
            raise MigrationError("Migrations directory does not exist.")
        migrations: list[Migration] = []
        for path in sorted(self._directory.iterdir()):
            if not path.is_file():
                continue
            match = _MIGRATION_NAME.fullmatch(path.name)
            if match is None:
                if path.suffix == ".sql":
                    raise MigrationError(f"Invalid migration filename: {path.name}.")
                continue
            sql = path.read_text(encoding="utf-8")
            migrations.append(
                Migration(
                    version=match.group("version"),
                    path=path,
                    checksum=hashlib.sha256(sql.encode("utf-8")).hexdigest(),
                    sql=sql,
                )
            )
        if not migrations:
            raise MigrationError("No SQL migrations were found.")
        expected = [f"{number:04d}" for number in range(1, len(migrations) + 1)]
        actual = [migration.version for migration in migrations]
        if actual != expected:
            raise MigrationError(
                "Migration versions must be unique, contiguous, and start at 0001."
            )
        return tuple(migrations)

    def close(self) -> None:
        self._engine.dispose()


def _split_sql(script: str) -> tuple[str, ...]:
    statements: list[str] = []
    current: list[str] = []
    quote: str | None = None
    index = 0
    while index < len(script):
        char = script[index]
        next_char = script[index + 1] if index + 1 < len(script) else ""
        if quote is None and char == "-" and next_char == "-":
            end = script.find("\n", index)
            index = len(script) if end == -1 else end
            continue
        if char in {"'", '"'}:
            if quote is None:
                quote = char
            elif quote == char:
                if next_char == char:
                    current.extend((char, next_char))
                    index += 2
                    continue
                quote = None
        if char == ";" and quote is None:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
        else:
            current.append(char)
        index += 1
    if quote is not None:
        raise MigrationError("Migration contains an unterminated SQL quote.")
    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    return tuple(statements)


def main() -> None:
    """Apply migrations configured for the current environment."""

    from mevad_api.config import Settings

    settings = Settings()
    runner = MigrationRunner.from_url(settings.database_url)
    try:
        applied = runner.run()
        print(f"Applied {applied} migration(s).")
    finally:
        runner.close()
