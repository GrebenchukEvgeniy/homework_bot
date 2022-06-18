class APIAnswerError(Exception):
    """Кастомная ошибка при незапланированной работе API."""

    pass


class CheckResponseException(Exception):
    """Исключение неверного формата ответа API."""

    pass
