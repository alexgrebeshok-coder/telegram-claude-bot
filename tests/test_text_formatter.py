"""Тесты для утилиты форматирования текста."""
import sys
import os

# Добавляем путь к модулю bot
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.utils.text_formatter import strip_markdown, format_code_blocks


class TestStripMarkdown:
    """Тесты для функции strip_markdown."""

    def test_empty_string(self):
        """Пустая строка возвращается без изменений."""
        assert strip_markdown("") == ""
        assert strip_markdown(None) is None

    def test_plain_text(self):
        """Обычный текст без разметки не изменяется."""
        text = "Просто текст без разметки"
        assert strip_markdown(text) == text

    def test_remove_headers(self):
        """Заголовки удаляются."""
        assert strip_markdown("# Заголовок") == "Заголовок"
        assert strip_markdown("## Подзаголовок") == "Подзаголовок"
        assert strip_markdown("### Третий уровень") == "Третий уровень"

    def test_remove_bold(self):
        """Жирный текст очищается."""
        assert strip_markdown("**жирный**") == "жирный"
        assert strip_markdown("__жирный__") == "жирный"

    def test_remove_italic(self):
        """Курсив очищается."""
        assert strip_markdown("*курсив*") == "курсив"
        assert strip_markdown("_курсив_") == "курсив"

    def test_remove_code_inline(self):
        """Инлайновый код очищается."""
        assert strip_markdown("`код`") == "код"
        assert strip_markdown("текст `код` текст") == "текст код текст"

    def test_remove_code_block(self):
        """Код блоки очищаются."""
        text = "```python\nprint('hello')\n```"
        result = strip_markdown(text)
        assert "```" not in result
        assert "print('hello')" in result

    def test_remove_links(self):
        """Ссылки заменяются на текст."""
        assert strip_markdown("[текст](https://example.com)") == "текст"

    def test_remove_blockquotes(self):
        """Блокквоты очищаются."""
        assert strip_markdown("> цитата") == "цитата"

    def test_convert_lists(self):
        """Маркеры списков преобразуются."""
        assert "•" in strip_markdown("- элемент")
        assert "•" in strip_markdown("* элемент")

    def test_complex_text(self, sample_markdown_text, expected_clean_text):
        """Комплексный тест с разными элементами разметки."""
        result = strip_markdown(sample_markdown_text)
        # Проверяем ключевые элементы
        assert "# Заголовок" not in result
        assert "**" not in result
        assert "*" not in result or "•" in result  # * может остаться как bullet
        assert "```" not in result
        assert "[Ссылка]" not in result


class TestFormatCodeBlocks:
    """Тесты для функции format_code_blocks."""

    def test_empty_string(self):
        """Пустая строка возвращается без изменений."""
        assert format_code_blocks("") == ""
        assert format_code_blocks(None) is None

    def test_inline_code(self):
        """Инлайновый код заменяется на кавычки."""
        assert format_code_blocks("`код`") == '"код"'

    def test_code_block(self):
        """Код блоки получают метку."""
        text = "```python\ncode\n```"
        result = format_code_blocks(text)
        assert "📝 Код:" in result
