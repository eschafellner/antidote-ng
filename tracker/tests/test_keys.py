from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.contrib.auth import get_user_model
from django.db import connections
from django.test import RequestFactory, TransactionTestCase, TestCase
from django.urls import resolve, reverse

from tracker.models import ActivityAction, ActivityLog, Issue, IssueStatus, Project
from tracker.services.issues import IssueService
from tracker.services.keys import IssueKeyService
from tracker.services.projects import ProjectService

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
        self.project = ProjectService.create_project(self.owner, "Concurrent Project", "CONC")

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
            try:
                return IssueKeyService.generate_next_number_and_key(project_id)
            finally:
                connections.close_all()

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

    def test_parallel_issue_requests_create_gapless_keys_with_activity(self) -> None:
        request_count = 8
        url = reverse("issue_create", kwargs={"slug": self.project.slug})
        match = resolve(url)
        ready = Barrier(request_count)

        def create_issue(index: int) -> int:
            try:
                request = RequestFactory().post(url, {"title": f"Issue {index}"})
                # Die Middleware hat den Benutzer am Eintritt in die View bereits geladen.
                request.user = self.owner
                ready.wait(timeout=15)
                return match.func(request, **match.kwargs).status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=request_count) as executor:
            statuses = list(executor.map(create_issue, range(request_count)))

        self.assertEqual(statuses, [302] * request_count)
        self.assertEqual(
            list(Issue.objects.filter(project=self.project).order_by("number").values_list("key", flat=True)),
            [f"CONC-{number}" for number in range(1, request_count + 1)],
        )
        self.assertEqual(ActivityLog.objects.filter(issue__project=self.project).count(), request_count)

    def test_parallel_opposing_moves_preserve_order_and_activity(self) -> None:
        first = IssueService.create_issue(self.project, self.owner, "First", status=IssueStatus.TODO)
        second = IssueService.create_issue(self.project, self.owner, "Second", status=IssueStatus.REVIEW)
        ready = Barrier(2)

        def move(issue: Issue, status: str) -> None:
            try:
                ready.wait(timeout=15)
                IssueService.move_issue(issue, self.owner, status, 0)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            first_move = executor.submit(move, first, IssueStatus.REVIEW)
            second_move = executor.submit(move, second, IssueStatus.TODO)
            first_move.result(timeout=20)
            second_move.result(timeout=20)

        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual((first.status, first.position), (IssueStatus.REVIEW, 0))
        self.assertEqual((second.status, second.position), (IssueStatus.TODO, 0))
        self.assertCountEqual(
            ActivityLog.objects.filter(issue__project=self.project, action=ActivityAction.STATUS_CHANGED)
            .values_list("old_value", "new_value"),
            [(IssueStatus.TODO, IssueStatus.REVIEW), (IssueStatus.REVIEW, IssueStatus.TODO)],
        )
