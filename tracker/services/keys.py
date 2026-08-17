import random
import time
from typing import Tuple
from django.db import transaction, OperationalError
from tracker.models.project import Project


class IssueKeyService:
    """
    Service responsible for generating sequential, race-condition-safe issue keys (e.g. 'PROJ-1', 'PROJ-42').

    It uses row-level locking (`select_for_update`) on the corresponding `Project` row inside
    an atomic transaction. This guarantees that concurrent issue creation requests for the same project
    never produce duplicate numbers or key collisions, without relying on counting existing issues.
    """

    @classmethod
    def generate_next_number_and_key(cls, project_id: int, max_retries: int = 25) -> Tuple[int, str]:
        """
        Atomically increments the project's `issue_counter` and returns the next sequential
        number and formatted key string (e.g., (1, 'PROJ-1')).

        :param project_id: Primary key of the Project.
        :param max_retries: Maximum retry attempts in case of database-level lock contention.
        :return: A tuple of (sequential_number, formatted_key).
        :raises Project.DoesNotExist: If no project with project_id exists.
        """
        for attempt in range(max_retries):
            try:
                with transaction.atomic():
                    project = Project.objects.select_for_update().get(pk=project_id)
                    project.issue_counter += 1
                    project.save(update_fields=["issue_counter"])
                    key = f"{project.key}-{project.issue_counter}"
                    return project.issue_counter, key
            except OperationalError as exc:
                if "locked" in str(exc).lower() and attempt < max_retries - 1:
                    time.sleep(0.02 * (1.3 ** attempt) + random.uniform(0.005, 0.03))
                    continue
                raise


