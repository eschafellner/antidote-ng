from concurrent.futures import ThreadPoolExecutor
from django.contrib.auth import get_user_model
from django.db import connection, connections
from django.test import TransactionTestCase, TestCase

from tracker.models import Project
from tracker.services.keys import IssueKeyService

User = get_user_model()


class IssueKeyServiceSequentialTests(TestCase):
    """Test sequential issue key generation in single-threaded context."""

    def setUp(self) -> None:
        self.owner = User.objects.create_user(username="owner", password="password123")
        self.project = Project.objects.create(name="Project Alpha", key="ALPHA", owner=self.owner)

    def test_sequential_key_generation(self) -> None:
        """Verify that sequential calls produce incrementing numbers and keys without gaps."""
        num1, key1 = IssueKeyService.generate_next_number_and_key(self.project.id)
        num2, key2 = IssueKeyService.generate_next_number_and_key(self.project.id)
        num3, key3 = IssueKeyService.generate_next_number_and_key(self.project.id)

        self.assertEqual(num1, 1)
        self.assertEqual(key1, "ALPHA-1")
        self.assertEqual(num2, 2)
        self.assertEqual(key2, "ALPHA-2")
        self.assertEqual(num3, 3)
        self.assertEqual(key3, "ALPHA-3")

        self.project.refresh_from_db()
        self.assertEqual(self.project.issue_counter, 3)


class IssueKeyServiceConcurrencyTests(TransactionTestCase):
    """Test concurrent issue key generation under simulated multi-threaded load."""

    def setUp(self) -> None:
        self.owner = User.objects.create_user(username="concurrent_owner", password="password123")
        self.project = Project.objects.create(
            name="Concurrent Project",
            key="CONC",
            owner=self.owner,
        )

    def tearDown(self) -> None:
        connections.close_all()

    def test_concurrent_key_generation_uniqueness(self) -> None:
        """
        Verify that parallel workers generating keys simultaneously produce strictly unique,
        gapless sequential keys without collisions or race conditions.
        """
        total_requests = 20
        project_id = self.project.id

        def worker(_: int) -> tuple[int, str]:
            connections.close_all()
            return IssueKeyService.generate_next_number_and_key(project_id)

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(worker, range(total_requests)))

        numbers = [num for num, _ in results]
        keys = [k for _, k in results]

        # 1. Total count matches requested amount
        self.assertEqual(len(numbers), total_requests)

        # 2. Every generated number is strictly unique
        self.assertEqual(len(set(numbers)), total_requests)

        # 3. Every generated key is strictly unique
        self.assertEqual(len(set(keys)), total_requests)

        # 4. Numbers span exactly from 1 to total_requests
        self.assertEqual(sorted(numbers), list(range(1, total_requests + 1)))

        # 5. Expected key format
        expected_keys = [f"CONC-{i}" for i in range(1, total_requests + 1)]
        self.assertEqual(sorted(keys), sorted(expected_keys))

        # 6. Counter on project matches final number
        self.project.refresh_from_db()
        self.assertEqual(self.project.issue_counter, total_requests)
