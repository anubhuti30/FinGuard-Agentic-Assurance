
import unittest
from decimal import Decimal

from task_budget_guard import (
    BudgetExceeded,
    IdempotencyConflict,
    TaskBudgetGuard,
)


class TaskBudgetGuardTests(unittest.TestCase):
    def setUp(self):
        self.guard = TaskBudgetGuard()

    def test_cumulative_actions_cannot_exceed_budget(self):
        self.guard.reserve("task1", "a", "4000", "10000")
        self.guard.reserve("task1", "b", "4000", "10000")

        with self.assertRaises(BudgetExceeded):
            self.guard.reserve("task1", "c", "3000", "10000")

        self.assertEqual(self.guard.used("task1"), Decimal("8000"))

    def test_retry_with_same_key_is_idempotent(self):
        first = self.guard.reserve("task1", "a", "4000", "10000")
        retry = self.guard.reserve("task1", "a", "4000", "10000")

        self.assertEqual(first, retry)
        self.assertEqual(self.guard.used("task1"), Decimal("4000"))

    def test_reusing_key_for_different_amount_is_rejected(self):
        self.guard.reserve("task1", "a", "4000", "10000")

        with self.assertRaises(IdempotencyConflict):
            self.guard.reserve("task1", "a", "5000", "10000")

    def test_released_reservation_returns_capacity(self):
        self.guard.reserve("task1", "a", "7000", "10000")
        self.guard.settle("task1", "a", "RELEASED")
        self.guard.reserve("task1", "b", "9000", "10000")

        self.assertEqual(self.guard.used("task1"), Decimal("9000"))

    def test_committed_reservation_still_counts(self):
        self.guard.reserve("task1", "a", "7000", "10000")
        self.guard.settle("task1", "a", "COMMITTED")

        with self.assertRaises(BudgetExceeded):
            self.guard.reserve("task1", "b", "4000", "10000")


if __name__ == "__main__":
    unittest.main()
## Experimental contribution: Agent Task Budget Guard

This fork adds a standalone Python prototype for cumulative task-level
budget reservations across multiple agent actions.

It demonstrates cumulative budget enforcement, idempotency-key consistency,
and reservation release/commit semantics. Five unit tests cover these
behaviors.

**Limitations:** This is an in-memory prototype, not a durable financial
ledger. It is not integrated into EXORYN's authorization pipeline and is
not suitable for production financial execution. The upstream project
and its existing implementation retain their original attribution.