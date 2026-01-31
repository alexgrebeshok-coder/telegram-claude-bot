"""Pytest fixtures для тестов."""
import os
import pytest

# Устанавливаем тестовые переменные окружения ДО импорта config
os.environ.setdefault("BOT_TOKEN", "test_token_123")
os.environ.setdefault("ADMIN_IDS", "123456789")


@pytest.fixture
def temp_db(tmp_path):
    """Создать временную базу данных для тестов."""
    db_path = tmp_path / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    return db_path


@pytest.fixture
def sample_markdown_text():
    """Пример текста с Markdown-разметкой."""
    return """# Заголовок

**Жирный текст** и *курсив*.

```python
def hello():
    print("Hello")
```

- Элемент списка 1
- Элемент списка 2

[Ссылка](https://example.com)
"""


@pytest.fixture
def expected_clean_text():
    """Ожидаемый результат после очистки Markdown."""
    return """Заголовок

Жирный текст и курсив.

def hello():
    print("Hello")

• Элемент списка 1
• Элемент списка 2

Ссылка"""
