import time
from unittest.mock import patch

from app.circuit_breaker import (
    CircuitBreaker, STATE_CLOSED, STATE_OPEN, STATE_HALF_OPEN,
)


def test_starts_closed():
    cb = CircuitBreaker("test")
    assert cb.state == STATE_CLOSED
    assert cb.can_execute() is True


def test_opens_after_threshold():
    cb = CircuitBreaker("test", failure_threshold=3)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == STATE_CLOSED
    cb.record_failure()
    assert cb.state == STATE_OPEN


def test_blocks_when_open():
    cb = CircuitBreaker("test", failure_threshold=1)
    cb.record_failure()
    assert cb.state == STATE_OPEN
    assert cb.can_execute() is False


def test_half_open_after_timeout():
    cb = CircuitBreaker("test", failure_threshold=1, reset_timeout=1)
    cb.record_failure()
    assert cb.state == STATE_OPEN
    assert cb.can_execute() is False

    # Simulate time passing past the reset timeout
    cb.last_failure_time = time.time() - 2
    assert cb.can_execute() is True
    assert cb.state == STATE_HALF_OPEN


def test_closes_on_success_after_half_open():
    cb = CircuitBreaker("test", failure_threshold=1, reset_timeout=1)
    cb.record_failure()
    cb.last_failure_time = time.time() - 2
    cb.can_execute()  # transitions to HALF_OPEN
    assert cb.state == STATE_HALF_OPEN

    cb.record_success()
    assert cb.state == STATE_CLOSED
    assert cb.failure_count == 0
    assert cb.can_execute() is True


def test_reopens_on_failure_in_half_open():
    cb = CircuitBreaker("test", failure_threshold=1, reset_timeout=1)
    cb.record_failure()
    cb.last_failure_time = time.time() - 2
    cb.can_execute()  # transitions to HALF_OPEN

    cb.record_failure()
    assert cb.state == STATE_OPEN
