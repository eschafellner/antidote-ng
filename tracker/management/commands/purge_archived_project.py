from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from tracker.models.project import Project
from tracker.services.projects import ProjectService


class Command(BaseCommand):
    help = "Löscht ein archiviertes Projekt samt Issues, Verlauf und Anhängen endgültig."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("slug", help="Slug des archivierten Projekts")

    def handle(self, *args: Any, **options: Any) -> None:
        slug = options["slug"]
        try:
            ProjectService.purge_archived_project(slug)
        except Project.DoesNotExist as exc:
            raise CommandError("Kein archiviertes Projekt mit diesem Slug gefunden.") from exc
        except OSError as exc:
            raise CommandError(f"Die Dateibereinigung ist fehlgeschlagen. Der Befehl kann wiederholt werden. {exc}") from exc
        self.stdout.write(self.style.SUCCESS(f"Archiviertes Projekt '{slug}' endgültig gelöscht."))
