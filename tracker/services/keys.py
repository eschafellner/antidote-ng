from typing import Tuple
from tracker.models.project import Project
from tracker.services.transactions import run_write_transaction


class IssueKeyService:
    """
    Service responsible for generating sequential, race-condition-safe issue keys (e.g. 'PROJ-1', 'PROJ-42').

    It uses row-level locking (`select_for_update`) on the corresponding `Project` row inside
    an atomic transaction. This guarantees that concurrent issue creation requests for the same project
    never produce duplicate numbers or key collisions, without relying on counting existing issues.
    """

    @classmethod
    def generate_next_number_and_key(cls, project_id: int, max_retries: int = 8) -> Tuple[int, str]:
        """Reserviert atomar die nächste laufende Nummer eines aktiven Projekts."""
        def advance_counter() -> Tuple[int, str]:
            project = Project.objects.select_for_update().get(pk=project_id, archived_at__isnull=True)
            project.issue_counter += 1
            project.save(update_fields=["issue_counter"])
            return project.issue_counter, f"{project.key}-{project.issue_counter}"

        return run_write_transaction(advance_counter, attempts=max_retries)
