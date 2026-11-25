import shutil
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import connection


class Command(BaseCommand):
    help = "Sichert die SQLite-Datenbank und Anhänge in einem neuen Verzeichnis."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("destination", type=Path, help="Neues Zielverzeichnis")

    def handle(self, *args: Any, **options: Any) -> None:
        if connection.vendor != "sqlite":
            raise CommandError("Für PostgreSQL sind pg_dump und eine separate Sicherung der Anhänge vorgesehen.")
        database = Path(connection.settings_dict["NAME"]).resolve()
        if not database.is_file():
            raise CommandError("Die konfigurierte SQLite-Datenbankdatei wurde nicht gefunden.")
        media = Path(settings.MEDIA_ROOT).resolve()
        destination = options["destination"].expanduser().resolve()
        if destination.is_relative_to(media):
            raise CommandError("Das Sicherungsziel muss außerhalb des Upload-Verzeichnisses liegen.")
        try:
            destination.mkdir(mode=0o700)
        except OSError as exc:
            raise CommandError(f"Das Sicherungsziel konnte nicht neu angelegt werden. {exc}") from exc

        try:
            with (
                closing(sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True)) as source,
                closing(sqlite3.connect(destination / "db.sqlite3")) as backup,
            ):
                source.backup(backup)
            if media.is_dir():
                shutil.copytree(media, destination / "media")
            else:
                (destination / "media").mkdir()
        except (OSError, sqlite3.Error) as exc:
            shutil.rmtree(destination)
            raise CommandError(f"Die Sicherung ist fehlgeschlagen. {exc}") from exc
        self.stdout.write(self.style.SUCCESS(f"Datenbank und Anhänge gesichert in {destination}."))
