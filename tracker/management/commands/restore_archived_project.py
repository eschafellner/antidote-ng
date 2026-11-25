from typing import Any

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError, CommandParser

from tracker.models.project import Project
from tracker.services.projects import ProjectService


class Command(BaseCommand):
    help = "Stellt ein archiviertes Projekt samt Verlauf und Mitgliedschaften wieder her."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("slug", help="Slug des archivierten Projekts")

    def handle(self, *args: Any, **options: Any) -> None:
        slug = options["slug"]
        try:
            ProjectService.restore_archived_project(slug)
        except Project.DoesNotExist as exc:
            raise CommandError("Kein archiviertes Projekt mit diesem Slug gefunden.") from exc
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages)) from exc
        self.stdout.write(self.style.SUCCESS(f"Archiviertes Projekt '{slug}' wiederhergestellt."))
