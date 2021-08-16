"""Custom exceptions raised by the ``bank`` application."""


class CmdError(Exception):
    """Raised when a piped command writes to STDERR in the underlying shell"""
