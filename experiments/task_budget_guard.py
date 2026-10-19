
"""Experimental cumulative budget guard for agent tasks."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from threading import RLock


class BudgetExceeded(ValueError):
    """Raised when a task's cumulative budget would be exceeded."""


class IdempotencyConflict(ValueError):
    """Raised when an idempotency key is reused inconsistently."""


@dataclass(frozen=True)
class Reservation:
    task_id: str
    key: str
    amount: Decimal
    status: str


class TaskBudgetGuard:
    """Thread-safe, in-memory prototype; not a production ledger."""

    def __init__(self):
        self._tasks = {}
        self._lock = RLock()

    @staticmethod
    def _amount(value):
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, ValueError):
            raise ValueError("Amount must be a valid decimal") from None
        if not amount.is_finite() or amount <= 0:
            raise ValueError("Amount must be finite and greater than zero")
        return amount

    def reserve(self, task_id, key, amount, budget):
        if not task_id or not key:
            raise ValueError("task_id and key are required")

        amount = self._amount(amount)
        budget = self._amount(budget)

        with self._lock:
            task = self._tasks.get(task_id)

            if task is None:
                task = {"budget": budget, "reservations": {}}
                self._tasks[task_id] = task
            elif task["budget"] != budget:
                raise IdempotencyConflict(
                    "A task's budget cannot change between reservations"
                )

            existing = task["reservations"].get(key)
            if existing is not None:
                if existing.amount != amount:
                    raise IdempotencyConflict(
                        "Idempotency key reused with a different amount"
                    )
                return existing

            used = sum(
                (r.amount for r in task["reservations"].values()
                 if r.status in ("RESERVED", "COMMITTED")),
                Decimal("0"),
            )

            if used + amount > budget:
                raise BudgetExceeded(
                    f"Task budget exceeded: {used} + {amount} > {budget}"
                )

            reservation = Reservation(task_id, key, amount, "RESERVED")
            task["reservations"][key] = reservation
            return reservation

    def settle(self, task_id, key, outcome):
        if outcome not in ("COMMITTED", "RELEASED"):
            raise ValueError("outcome must be COMMITTED or RELEASED")

        with self._lock:
            task = self._tasks.get(task_id)
            if task is None or key not in task["reservations"]:
                raise KeyError("Unknown task reservation")

            current = task["reservations"][key]

            if current.status == outcome:
                return current

            if current.status != "RESERVED":
                raise IdempotencyConflict(
                    "A finalized reservation cannot change outcome"
                )

            updated = Reservation(
                current.task_id, current.key, current.amount, outcome
            )
            task["reservations"][key] = updated
            return updated

    def used(self, task_id):
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return Decimal("0")

            return sum(
                (r.amount for r in task["reservations"].values()
                 if r.status in ("RESERVED", "COMMITTED")),
                Decimal("0"),
            )
