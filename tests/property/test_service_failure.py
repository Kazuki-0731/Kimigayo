"""
Property 25: Service Failure Handling

Verifies that the init system properly logs failures and attempts recovery.
Testing requirement 7.3.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from datetime import datetime

from src.init.logging import (
    LogLevel,
    ErrorCategory,
    LogEntry,
    ServiceError,
    LoggerConfig,
    Logger,
    RecoveryPolicy,
    ErrorHandler,
)


@pytest.mark.property
class TestServiceFailureHandling:
    """Test property 25: Service failures are logged and recovery is attempted"""

    @given(
        st.text(min_size=1, max_size=50),
        st.sampled_from(list(ErrorCategory)),
        st.text(min_size=1, max_size=200)
    )
    @settings(max_examples=50)
    def test_errors_are_logged(self, service, category, message):
        """
        Property: All service errors must be logged
        """
        config = LoggerConfig()
        logger = Logger(config)

        # Log an error
        logger.error(service, message, category=category)

        # Verify error was logged
        errors = logger.get_errors(service=service)
        assert len(errors) > 0

        error = errors[-1]
        assert error.service == service
        assert error.category == category
        assert error.message == message
        assert not error.resolved

    @given(
        st.text(min_size=1, max_size=50),
        st.sampled_from(list(LogLevel)),
        st.text(min_size=1, max_size=200)
    )
    @settings(max_examples=50)
    def test_log_entries_created(self, service, level, message):
        """
        Property: Log entries are created for all log calls
        """
        config = LoggerConfig(min_level=LogLevel.DEBUG)
        logger = Logger(config)

        # Log message
        logger.log(level, service, message)

        # Verify entry was created
        entries = logger.get_entries(service=service, level=level)
        assert len(entries) > 0

        entry = entries[-1]
        assert entry.service == service
        assert entry.level == level
        assert entry.message == message

    @given(st.integers(min_value=1, max_value=10))
    @settings(max_examples=50)
    def test_recovery_retry_limit(self, max_attempts):
        """
        Property: Recovery attempts respect maximum retry limit
        """
        config = LoggerConfig()
        logger = Logger(config)
        handler = ErrorHandler(logger)

        service = "test_service"
        policy = RecoveryPolicy(
            restart_on_failure=True,
            max_restart_attempts=max_attempts
        )
        handler.set_recovery_policy(service, policy)

        # Simulate failures up to max attempts
        for i in range(max_attempts):
            should_retry = handler.handle_error(
                service,
                ErrorCategory.CRASHED,
                f"Crash {i+1}"
            )
            assert should_retry

        # Next attempt should not retry
        should_retry = handler.handle_error(
            service,
            ErrorCategory.CRASHED,
            f"Crash {max_attempts+1}"
        )
        assert not should_retry

    @given(st.integers(min_value=1, max_value=10), st.integers(min_value=1, max_value=60))
    @settings(max_examples=50)
    def test_exponential_backoff(self, attempt, base_delay):
        """
        Property: Exponential backoff increases delay with each attempt
        """
        policy = RecoveryPolicy(
            restart_on_failure=True,
            restart_delay_seconds=base_delay,
            use_exponential_backoff=True,
            max_backoff_seconds=300
        )

        # Get delays for consecutive attempts
        delay1 = policy.get_restart_delay(attempt)
        delay2 = policy.get_restart_delay(attempt + 1)

        # Second delay should be >= first delay
        assert delay2 >= delay1

        # For exponential backoff, delay should double (unless hitting max)
        if delay1 < policy.max_backoff_seconds / 2:
            assert delay2 == delay1 * 2

    @given(st.integers(min_value=1, max_value=60))
    @settings(max_examples=50)
    def test_linear_backoff(self, base_delay):
        """
        Property: Linear backoff maintains constant delay
        """
        policy = RecoveryPolicy(
            restart_on_failure=True,
            restart_delay_seconds=base_delay,
            use_exponential_backoff=False
        )

        # All delays should be the same
        for attempt in range(1, 6):
            delay = policy.get_restart_delay(attempt)
            assert delay == base_delay

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=50)
    def test_successful_recovery_resets_counter(self, service):
        """
        Property: Successful recovery resets retry counter
        """
        config = LoggerConfig()
        logger = Logger(config)
        handler = ErrorHandler(logger)

        policy = RecoveryPolicy(
            restart_on_failure=True,
            max_restart_attempts=3
        )
        handler.set_recovery_policy(service, policy)

        # Simulate some failures
        handler.handle_error(service, ErrorCategory.CRASHED, "Crash 1")
        handler.handle_error(service, ErrorCategory.CRASHED, "Crash 2")
        assert handler.get_retry_count(service) == 2

        # Simulate successful recovery
        handler.handle_success(service)

        # Counter should be reset
        assert handler.get_retry_count(service) == 0

    @given(
        st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=10, unique=True),
        st.sampled_from(list(ErrorCategory))
    )
    @settings(max_examples=50)
    def test_error_filtering_by_service(self, services, category):
        """
        Property: Error filtering by service returns only that service's errors
        """
        config = LoggerConfig()
        logger = Logger(config)

        # Log errors for each service
        for service in services:
            logger.error(service, f"Error in {service}", category=category)

        # Verify filtering works for each service
        for service in services:
            errors = logger.get_errors(service=service)
            assert len(errors) >= 1
            assert all(e.service == service for e in errors)

    @given(
        st.text(min_size=1, max_size=50),
        st.lists(st.sampled_from(list(ErrorCategory)), min_size=2, max_size=5)
    )
    @settings(max_examples=50)
    def test_error_filtering_by_category(self, service, categories):
        """
        Property: Error filtering by category returns only errors of that category
        """
        config = LoggerConfig()
        logger = Logger(config)

        # Log errors with different categories
        for category in categories:
            logger.error(service, f"Error: {category.value}", category=category)

        # Verify filtering works for each category
        for category in categories:
            errors = logger.get_errors(category=category)
            assert len(errors) >= 1
            assert all(e.category == category for e in errors)

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=50)
    def test_unresolved_errors_filtered(self, service):
        """
        Property: Unresolved filter returns only unresolved errors
        """
        config = LoggerConfig()
        logger = Logger(config)

        # Create some errors
        logger.error(service, "Error 1", ErrorCategory.CRASHED)
        logger.error(service, "Error 2", ErrorCategory.CONFIG_ERROR)
        logger.error(service, "Error 3", ErrorCategory.DEPENDENCY_FAILED)

        # Resolve one error
        errors = logger.get_errors(service=service)
        logger.mark_error_resolved(errors[0], "Fixed manually")

        # Get unresolved errors
        unresolved = logger.get_errors(service=service, unresolved_only=True)

        # Should have 2 unresolved errors
        assert len(unresolved) == 2
        assert all(not e.resolved for e in unresolved)

    @given(st.integers(min_value=0, max_value=100))
    @settings(max_examples=50)
    def test_log_entry_limit(self, limit):
        """
        Property: Log entry limit returns at most N entries
        """
        config = LoggerConfig()
        logger = Logger(config)

        service = "test_service"

        # Create more entries than limit
        num_entries = limit + 10 if limit > 0 else 10
        for i in range(num_entries):
            logger.info(service, f"Message {i}")

        # Get limited entries
        if limit > 0:
            entries = logger.get_entries(limit=limit)
            assert len(entries) <= limit
        else:
            # Limit of 0 should return all entries
            entries = logger.get_entries(limit=None)
            assert len(entries) == num_entries

    @given(
        st.text(min_size=1, max_size=50),
        st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=50)
    def test_error_summary_accuracy(self, service, num_errors):
        """
        Property: Error summary accurately reflects logged errors
        """
        config = LoggerConfig()
        logger = Logger(config)

        categories = list(ErrorCategory)

        # Log errors
        for i in range(num_errors):
            category = categories[i % len(categories)]
            logger.error(service, f"Error {i}", category=category)

        summary = logger.get_error_summary()

        # Verify total count
        assert summary["total_errors"] == num_errors
        assert summary["unresolved_errors"] == num_errors

        # Verify service count
        assert summary["errors_by_service"][service] == num_errors

    @given(st.booleans())
    @settings(max_examples=50)
    def test_recovery_policy_restart_flag(self, restart_enabled):
        """
        Property: Recovery policy respects restart_on_failure flag
        """
        policy = RecoveryPolicy(
            restart_on_failure=restart_enabled,
            max_restart_attempts=3
        )

        should_retry = policy.should_retry(attempt=1)
        assert should_retry == restart_enabled

    @given(st.integers(min_value=1, max_value=300))
    @settings(max_examples=50)
    def test_max_backoff_limit(self, max_backoff):
        """
        Property: Backoff delay never exceeds maximum
        """
        policy = RecoveryPolicy(
            restart_on_failure=True,
            restart_delay_seconds=10,
            use_exponential_backoff=True,
            max_backoff_seconds=max_backoff
        )

        # Test various attempts
        for attempt in range(1, 20):
            delay = policy.get_restart_delay(attempt)
            assert delay <= max_backoff

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=50)
    def test_services_in_recovery_tracked(self, service):
        """
        Property: Services in recovery are tracked
        """
        config = LoggerConfig()
        logger = Logger(config)
        handler = ErrorHandler(logger)

        policy = RecoveryPolicy(restart_on_failure=True, max_restart_attempts=3)
        handler.set_recovery_policy(service, policy)

        # No services in recovery initially
        assert len(handler.get_services_in_recovery()) == 0

        # Trigger error
        handler.handle_error(service, ErrorCategory.CRASHED, "Error")

        # Service should be in recovery
        assert service in handler.get_services_in_recovery()

        # After success, should not be in recovery
        handler.handle_success(service)
        assert service not in handler.get_services_in_recovery()

    @given(st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=5, unique=True))
    @settings(max_examples=50)
    def test_multiple_services_recovery(self, services):
        """
        Property: Multiple services can be in recovery simultaneously
        """
        config = LoggerConfig()
        logger = Logger(config)
        handler = ErrorHandler(logger)

        # Set up recovery policies
        for service in services:
            policy = RecoveryPolicy(restart_on_failure=True, max_restart_attempts=3)
            handler.set_recovery_policy(service, policy)

        # Trigger errors for all services
        for service in services:
            handler.handle_error(service, ErrorCategory.CRASHED, f"Error in {service}")

        # All services should be in recovery
        in_recovery = handler.get_services_in_recovery()
        assert len(in_recovery) == len(services)
        assert set(in_recovery) == set(services)

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=50)
    def test_log_level_filtering(self, service):
        """
        Property: Log entries below minimum level are not recorded
        """
        # Set minimum level to WARNING
        config = LoggerConfig(min_level=LogLevel.WARNING)
        logger = Logger(config)

        # Log messages at different levels
        logger.debug(service, "Debug message")
        logger.info(service, "Info message")
        logger.warning(service, "Warning message")
        logger.error(service, "Error message", ErrorCategory.UNKNOWN)

        # Only WARNING and ERROR should be recorded
        all_entries = logger.get_entries(service=service)
        assert len(all_entries) == 2

        levels = {entry.level for entry in all_entries}
        assert LogLevel.WARNING in levels
        assert LogLevel.ERROR in levels
        assert LogLevel.DEBUG not in levels
        assert LogLevel.INFO not in levels

    @given(st.text(min_size=1, max_size=200))
    @settings(max_examples=50)
    def test_error_resolution_message(self, resolution_msg):
        """
        Property: Resolved errors have resolution messages
        """
        config = LoggerConfig()
        logger = Logger(config)

        service = "test_service"
        logger.error(service, "Test error", ErrorCategory.CRASHED)

        # Get error and mark as resolved
        error = logger.get_errors(service=service)[0]
        logger.mark_error_resolved(error, resolution_msg)

        # Verify resolution
        assert error.resolved
        assert error.resolution_message == resolution_msg

    @given(st.integers(min_value=0, max_value=10))
    @settings(max_examples=50)
    def test_retry_count_accuracy(self, num_retries):
        """
        Property: Retry count accurately reflects number of attempts
        """
        config = LoggerConfig()
        logger = Logger(config)
        handler = ErrorHandler(logger)

        service = "test_service"
        policy = RecoveryPolicy(restart_on_failure=True, max_restart_attempts=10)
        handler.set_recovery_policy(service, policy)

        # Trigger errors
        for _ in range(num_retries):
            handler.handle_error(service, ErrorCategory.CRASHED, "Error")

        # Verify retry count
        assert handler.get_retry_count(service) == num_retries

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=50)
    def test_clear_logs_removes_entries(self, service):
        """
        Property: Clearing logs removes all entries
        """
        config = LoggerConfig()
        logger = Logger(config)

        # Create some log entries
        for i in range(5):
            logger.info(service, f"Message {i}")

        # Verify entries exist
        assert len(logger.get_entries()) > 0

        # Clear logs
        logger.clear_logs()

        # Verify entries are gone
        assert len(logger.get_entries()) == 0

    @given(st.text(min_size=1, max_size=50))
    @settings(max_examples=50)
    def test_clear_errors_removes_errors(self, service):
        """
        Property: Clearing errors removes all error records
        """
        config = LoggerConfig()
        logger = Logger(config)

        # Create some errors
        for i in range(5):
            logger.error(service, f"Error {i}", ErrorCategory.CRASHED)

        # Verify errors exist
        assert len(logger.get_errors()) > 0

        # Clear errors
        logger.clear_errors()

        # Verify errors are gone
        assert len(logger.get_errors()) == 0
