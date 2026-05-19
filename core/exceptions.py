"""Custom exceptions for the application."""


class PulseException(Exception):
    """Base exception for Pulse application."""

    pass


class RuleNotFoundError(PulseException):
    """Raised when a rule is not found."""

    pass


class InvalidRuleConfigError(PulseException):
    """Raised when rule configuration is invalid."""

    pass


class AlertDeliveryError(PulseException):
    """Raised when alert delivery fails."""

    pass
