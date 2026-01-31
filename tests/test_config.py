"""Тесты для модуля конфигурации."""
import os
import sys
import pytest


def reload_config():
    """Удалить закэшированный модуль config для перезагрузки."""
    modules_to_remove = [m for m in sys.modules if m.startswith("bot")]
    for m in modules_to_remove:
        del sys.modules[m]


class TestConfigValidation:
    """Тесты валидации конфигурации."""

    def test_admin_ids_must_be_numeric(self, monkeypatch):
        """ADMIN_IDS должен содержать числовые ID."""
        reload_config()
        monkeypatch.setenv("BOT_TOKEN", "test_token")
        monkeypatch.setenv("ADMIN_IDS", "not_a_number")

        with pytest.raises(ValueError, match="некорректные значения"):
            import bot.config

    def test_valid_config(self, monkeypatch):
        """Валидная конфигурация загружается без ошибок."""
        reload_config()
        monkeypatch.setenv("BOT_TOKEN", "valid_token")
        monkeypatch.setenv("ADMIN_IDS", "123456789,987654321")

        import bot.config

        assert bot.config.BOT_TOKEN == "valid_token"
        assert 123456789 in bot.config.ADMIN_IDS
        assert 987654321 in bot.config.ADMIN_IDS

    def test_default_values(self, monkeypatch):
        """Проверка значений по умолчанию."""
        reload_config()
        monkeypatch.setenv("BOT_TOKEN", "test_token")
        monkeypatch.setenv("ADMIN_IDS", "123")

        import bot.config

        assert bot.config.CLAUDE_TIMEOUT == 600
        assert bot.config.LOG_LEVEL == "INFO"

    def test_multiple_admin_ids(self, monkeypatch):
        """Несколько ADMIN_IDS парсятся корректно."""
        reload_config()
        monkeypatch.setenv("BOT_TOKEN", "test_token")
        monkeypatch.setenv("ADMIN_IDS", "111, 222, 333")

        import bot.config

        assert len(bot.config.ADMIN_IDS) == 3
        assert 111 in bot.config.ADMIN_IDS
        assert 222 in bot.config.ADMIN_IDS
        assert 333 in bot.config.ADMIN_IDS
