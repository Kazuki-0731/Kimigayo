"""
Logging and Error Handling for Kimigayo OS Init System

Provides structured logging, error tracking, and service failure recovery.
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
import json


class LogLevel(Enum):
    """Log severity levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ErrorCategory(Enum):
    """Categories of service errors"""
    DEPENDENCY_FAILED = "dependency_failed"
    START_TIMEOUT = "start_timeout"
    CRASHED = "crashed"
    CONFIG_ERROR = "config_error"
    RESOURCE_ERROR = "resource_error"
    UNKNOWN = "unknown"


@dataclass
class LogEntry:
    """A single log entry"""
    timestamp: datetime
    level: LogLevel
    service: str
    message: str
    category: Optional[ErrorCategory] = None
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary"""
        entry = {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "service": self.service,
            "message": self.message
        }

        if self.category:
            entry["category"] = self.category.value

        if self.details:
            entry["details"] = self.details

        return entry

    def to_json(self) -> str:
        """Convert log entry to JSON string"""
        return json.dumps(self.to_dict())

    def __str__(self) -> str:
        """Format log entry as string"""
        timestamp_str = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        msg = f"[{timestamp_str}] {self.level.value:8s} {self.service:20s} {self.message}"

        if self.category:
            msg += f" (category: {self.category.value})"

        return msg


@dataclass
class ServiceError:
    """Information about a service error"""
    service: str
    category: ErrorCategory
    message: str
    timestamp: datetime
    retry_count: int = 0
    resolved: bool = False
    resolution_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary"""
        return {
            "service": self.service,
            "category": self.category.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "retry_count": self.retry_count,
            "resolved": self.resolved,
            "resolution_message": self.resolution_message
        }


class LoggerConfig:
    """Configuration for logging system"""

    def __init__(
        self,
        log_file: Path = Path("/var/log/init.log"),
        console_output: bool = True,
        min_level: LogLevel = LogLevel.INFO,
        max_log_size_mb: int = 10,
        max_log_files: int = 5,
        json_format: bool = False
    ):
        self.log_file = log_file
        self.console_output = console_output
        self.min_level = min_level
        self.max_log_size_mb = max_log_size_mb
        self.max_log_files = max_log_files
        self.json_format = json_format


class Logger:
    """Logging system for init services"""

    def __init__(self, config: LoggerConfig):
        self.config = config
        self.entries: List[LogEntry] = []
        self.errors: List[ServiceError] = []

    def log(
        self,
        level: LogLevel,
        service: str,
        message: str,
        category: Optional[ErrorCategory] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log a message.

        Args:
            level: Log severity level
            service: Service name
            message: Log message
            category: Optional error category
            details: Optional additional details
        """
        # Check if level meets minimum threshold
        level_order = [LogLevel.DEBUG, LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR, LogLevel.CRITICAL]
        if level_order.index(level) < level_order.index(self.config.min_level):
            return

        # Create log entry
        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            service=service,
            message=message,
            category=category,
            details=details
        )

        # Store entry
        self.entries.append(entry)

        # Write to outputs (mock implementation)
        self._write_entry(entry)

    def _write_entry(self, entry: LogEntry):
        """Write log entry to configured outputs"""
        # In real implementation, would write to file and/or console
        pass

    def debug(self, service: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Log debug message"""
        self.log(LogLevel.DEBUG, service, message, details=details)

    def info(self, service: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Log info message"""
        self.log(LogLevel.INFO, service, message, details=details)

    def warning(self, service: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Log warning message"""
        self.log(LogLevel.WARNING, service, message, details=details)

    def error(
        self,
        service: str,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log error message"""
        self.log(LogLevel.ERROR, service, message, category=category, details=details)

        # Track error
        error = ServiceError(
            service=service,
            category=category,
            message=message,
            timestamp=datetime.now()
        )
        self.errors.append(error)

    def critical(
        self,
        service: str,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log critical message"""
        self.log(LogLevel.CRITICAL, service, message, category=category, details=details)

        # Track error
        error = ServiceError(
            service=service,
            category=category,
            message=message,
            timestamp=datetime.now()
        )
        self.errors.append(error)

    def get_entries(
        self,
        service: Optional[str] = None,
        level: Optional[LogLevel] = None,
        limit: Optional[int] = None
    ) -> List[LogEntry]:
        """
        Get log entries with optional filtering.

        Args:
            service: Filter by service name
            level: Filter by log level
            limit: Maximum number of entries to return

        Returns:
            Filtered list of log entries
        """
        entries = self.entries

        if service:
            entries = [e for e in entries if e.service == service]

        if level:
            entries = [e for e in entries if e.level == level]

        if limit:
            entries = entries[-limit:]

        return entries

    def get_errors(
        self,
        service: Optional[str] = None,
        category: Optional[ErrorCategory] = None,
        unresolved_only: bool = False
    ) -> List[ServiceError]:
        """
        Get service errors with optional filtering.

        Args:
            service: Filter by service name
            category: Filter by error category
            unresolved_only: Only return unresolved errors

        Returns:
            Filtered list of service errors
        """
        errors = self.errors

        if service:
            errors = [e for e in errors if e.service == service]

        if category:
            errors = [e for e in errors if e.category == category]

        if unresolved_only:
            errors = [e for e in errors if not e.resolved]

        return errors

    def mark_error_resolved(self, error: ServiceError, resolution_message: str):
        """Mark an error as resolved"""
        error.resolved = True
        error.resolution_message = resolution_message

        self.info(
            error.service,
            f"Error resolved: {resolution_message}",
            details={"original_error": error.message}
        )

    def clear_logs(self):
        """Clear all log entries"""
        self.entries.clear()

    def clear_errors(self):
        """Clear all error records"""
        self.errors.clear()

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors"""
        total_errors = len(self.errors)
        unresolved_errors = len([e for e in self.errors if not e.resolved])

        category_counts = {}
        for error in self.errors:
            category = error.category.value
            category_counts[category] = category_counts.get(category, 0) + 1

        service_counts = {}
        for error in self.errors:
            service = error.service
            service_counts[service] = service_counts.get(service, 0) + 1

        return {
            "total_errors": total_errors,
            "unresolved_errors": unresolved_errors,
            "errors_by_category": category_counts,
            "errors_by_service": service_counts
        }


@dataclass
class RecoveryPolicy:
    """Policy for recovering from service failures"""

    # Restart settings
    restart_on_failure: bool = False
    max_restart_attempts: int = 3
    restart_delay_seconds: int = 5

    # Backoff strategy
    use_exponential_backoff: bool = True
    max_backoff_seconds: int = 300  # 5 minutes

    # Dependency handling
    stop_dependents_on_failure: bool = True
    restart_dependents_on_recovery: bool = False

    def get_restart_delay(self, attempt: int) -> int:
        """
        Calculate restart delay for a given attempt.

        Args:
            attempt: Current restart attempt number

        Returns:
            Delay in seconds before next restart
        """
        if not self.use_exponential_backoff:
            return self.restart_delay_seconds

        # Exponential backoff: delay * 2^(attempt-1)
        delay = self.restart_delay_seconds * (2 ** (attempt - 1))
        return min(delay, self.max_backoff_seconds)

    def should_retry(self, attempt: int) -> bool:
        """
        Determine if another restart attempt should be made.

        Args:
            attempt: Current restart attempt number

        Returns:
            True if retry should be attempted
        """
        if not self.restart_on_failure:
            return False

        return attempt < self.max_restart_attempts


class ErrorHandler:
    """Handles service errors and recovery"""

    def __init__(self, logger: Logger):
        self.logger = logger
        self.recovery_policies: Dict[str, RecoveryPolicy] = {}
        self.retry_counts: Dict[str, int] = {}

    def set_recovery_policy(self, service: str, policy: RecoveryPolicy):
        """Set recovery policy for a service"""
        self.recovery_policies[service] = policy

    def get_recovery_policy(self, service: str) -> Optional[RecoveryPolicy]:
        """Get recovery policy for a service"""
        return self.recovery_policies.get(service)

    def handle_error(
        self,
        service: str,
        category: ErrorCategory,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Handle a service error.

        Args:
            service: Service name
            category: Error category
            message: Error message
            details: Optional error details

        Returns:
            True if recovery was attempted, False otherwise
        """
        # Log the error
        self.logger.error(service, message, category=category, details=details)

        # Get recovery policy
        policy = self.recovery_policies.get(service)
        if not policy:
            return False

        # Check if we should attempt recovery
        current_attempts = self.retry_counts.get(service, 0)

        if policy.should_retry(current_attempts):
            # Increment retry count
            self.retry_counts[service] = current_attempts + 1

            # Calculate delay
            delay = policy.get_restart_delay(current_attempts + 1)

            # Log recovery attempt
            self.logger.info(
                service,
                f"Attempting recovery (attempt {current_attempts + 1}/{policy.max_restart_attempts})",
                details={"delay_seconds": delay}
            )

            return True
        else:
            self.logger.warning(
                service,
                f"Max restart attempts ({policy.max_restart_attempts}) reached, giving up",
                details={"total_attempts": current_attempts}
            )
            return False

    def handle_success(self, service: str):
        """
        Handle successful service start/restart.
        Resets retry counters.

        Args:
            service: Service name
        """
        # Reset retry count
        if service in self.retry_counts:
            attempts = self.retry_counts[service]
            del self.retry_counts[service]

            self.logger.info(
                service,
                f"Service recovered successfully after {attempts} attempts"
            )

            # Mark any unresolved errors as resolved
            for error in self.logger.get_errors(service=service, unresolved_only=True):
                self.logger.mark_error_resolved(error, "Service recovered")

    def get_retry_count(self, service: str) -> int:
        """Get current retry count for a service"""
        return self.retry_counts.get(service, 0)

    def reset_retry_count(self, service: str):
        """Reset retry count for a service"""
        if service in self.retry_counts:
            del self.retry_counts[service]

    def get_services_in_recovery(self) -> List[str]:
        """Get list of services currently in recovery"""
        return list(self.retry_counts.keys())
