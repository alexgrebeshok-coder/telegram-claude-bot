"""
Утилита для очистки Markdown-разметки из текста.
Преобразует MD-текст в обычный текст для красивого отображения в Telegram.
"""
import re


def strip_markdown(text: str) -> str:
    """
    Убрать все Markdown-символы из текста.
    
    Удаляет:
    - Заголовки (# ## ### и т.д.)
    - Полужирный (**text**, __text__)
    - Курсив (*text*, _text_)
    - Код блоки (```code``` и `code`)
    - Списки (- , * , 1. )
    - Ссылки ([text](url))
    - Горизонтальные линии (---, ***)
    - Блокквоты (> )
    
    Args:
        text: Текст с Markdown-разметкой
        
    Returns:
        Текст без Markdown-символов
    """
    if not text:
        return text
    
    result = text
    
    # 1. Убрать заголовки (# ## ### и т.д.) в начале строки
    # Удаляет символы # в начале строк и следующие за ними пробелы
    result = re.sub(r'^#{1,6}\s+', '', result, flags=re.MULTILINE)
    
    # 2. Убрать полужирный (**text** и __text__)
    result = re.sub(r'\*\*(.+?)\*\*', r'\1', result)  # **text**
    result = re.sub(r'__(.+?)__', r'\1', result)      # __text__
    
    # 3. Убрать курсив (*text* и _text_)
    # Важно: делаем после полужирного, чтобы не нарушить его
    result = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'\1', result)  # *text* (не внутри **)
    result = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'\1', result)        # _text_ (не внутри __)
    
    # 4. Убрать инлайновый код (`code`)
    result = re.sub(r'`([^`]+)`', r'\1', result)
    
    # 5. Убрать код блоки (```code```)
    # Удаляет теги ``` и оставляет только код
    result = re.sub(r'```[\w]*\n?', '', result)  # Начало блока
    result = re.sub(r'```\s*$', '', result)      # Конец блока
    
    # 6. Убрать ссылки [text](url) -> text
    result = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', result)
    
    # 7. Убрать горизонтальные линии (---, ***, ___)
    result = re.sub(r'^(-{3,}|\*{3,}|_{3,})\s*$', '', result, flags=re.MULTILINE)
    
    # 8. Убрать блокквоты (> )
    result = re.sub(r'^>\s+', '', result, flags=re.MULTILINE)
    
    # 9. Убрать маркеры списков в начале строки (- , * , + , 1. , 1) )
    result = re.sub(r'^(\s*)([-*+])\s+', r'\1• ', result, flags=re.MULTILINE)
    result = re.sub(r'^(\s*)(\d+\.)\s+', r'\1', result, flags=re.MULTILINE)
    
    # 10. Убрать лишние пустые строки (более 2 подряд)
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    # 11. Убрать пробелы в начале и конце строк
    result = '\n'.join(line.rstrip() for line in result.split('\n'))
    
    return result.strip()


def format_code_blocks(text: str) -> str:
    """
    Альтернативная функция: убрать только код блоки, остальное оставить.
    
    Полезно, если хотите сохранить заголовки, жирный текст и т.д.
    
    Args:
        text: Текст с Markdown-разметкой
        
    Returns:
        Текст без код блоков (остальное сохранено)
    """
    if not text:
        return text
    
    result = text
    
    # Заменить код блоки на обычный текст
    result = re.sub(r'```[\w]*\n?', '📝 Код:', result)
    result = re.sub(r'```\s*$', '', result)
    
    # Заменить инлайновый код на кавычки
    result = re.sub(r'`([^`]+)`', r'"\1"', result)
    
    return result
