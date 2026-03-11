import time
import logging

logger = logging.getLogger(__name__)

STATE_CLOSED = "CLOSED"
STATE_OPEN = "OPEN"
STATE_HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    def __init__(self, name, failure_threshold=3, reset_timeout=60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.state = STATE_CLOSED
        self.failure_count = 0
        self.last_failure_time = None

    def can_execute(self):
        if self.state == STATE_CLOSED:
            return True
        if self.state == STATE_OPEN:
            if time.time() - self.last_failure_time >= self.reset_timeout:
                self.state = STATE_HALF_OPEN
                logger.info("Circuit %s → HALF_OPEN", self.name)
                return True
            return False
        # HALF_OPEN — allow one test request
        return True

    def record_success(self):
        self.failure_count = 0
        self.state = STATE_CLOSED
        logger.info("Circuit %s → CLOSED (success)", self.name)

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = STATE_OPEN
            logger.warning(
                "Circuit %s → OPEN after %d failures",
                self.name, self.failure_count
            )
