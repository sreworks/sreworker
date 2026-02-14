"""Tests for logger utility."""

import logging

from app.utils.logger import setup_logger, get_app_logger


class TestSetupLogger:
    """SUT: setup_logger"""

    def test_returns_logger(self):
        """Should return a Logger instance."""
        logger = setup_logger("test_logger_returns")
        assert isinstance(logger, logging.Logger)

    def test_with_level(self):
        """Setting DEBUG level should take effect."""
        logger = setup_logger("test_logger_level", log_level="DEBUG")
        assert logger.level == logging.DEBUG

    def test_no_duplicate_handlers(self):
        """Calling multiple times should not add duplicate handlers."""
        name = "test_logger_dup"
        logger1 = setup_logger(name)
        handler_count = len(logger1.handlers)
        logger2 = setup_logger(name)
        assert len(logger2.handlers) == handler_count
        assert logger1 is logger2


class TestGetAppLogger:
    """SUT: get_app_logger"""

    def test_default(self):
        """Should return a logger even when not explicitly initialized."""
        logger = get_app_logger()
        assert isinstance(logger, logging.Logger)
