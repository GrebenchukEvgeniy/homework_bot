import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    handlers=[logging.StreamHandler()],
    level=logging.INFO,
    format='%(asctime)s, %(levelname)s, %(message)s'
)
logger = logging.getLogger(__name__)


class APIAnswerError(Exception):
    """Кастомная ошибка при незапланированной работе API."""

    pass


def send_message(bot, message):
    """Отправляет сообщения."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Отправлено сообщение: "{message}"')
    except Exception as error:
        logging.error(f'Cбой отправки сообщения, ошибка: {error}')


def get_api_answer(current_timestamp):
    """Запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception:
        message = 'Ошибка API'
        raise APIAnswerError(message)
    try:
        if response.status_code != HTTPStatus.OK:
            message = 'Код энпоинта не 200'
            raise Exception(message)
    except Exception:
        message = 'Ошибка API'
        raise APIAnswerError(message)
    return response.json()


def check_response(response):
    """Проверяет полученный ответ на корректность."""
    try:
        homeworks_list = response['homeworks']
        print(len(homeworks_list))
    except KeyError as e:
        msg = f'Ошибка доступа по ключу homeworks: {e}'
        logger.error(msg)
        raise Exception(msg)
    if homeworks_list is None:
        msg = 'В ответе API нет словаря с ДЗ'
        logger.error(msg)
        raise Exception(msg)
    if len(homeworks_list) == 0:
        msg = 'За последнее время нет изменения домашки'
        logger.error(msg)
        raise Exception(msg)
    if not isinstance(homeworks_list, list):
        msg = 'В ответе API домашки представлены не списком'
        logger.error(msg)
        raise Exception(msg)
    return homeworks_list


def parse_status(homework):
    """Формирует сообщение с обновленным статусом для отправки."""
    try:
        homework_name = homework.get('homework_name')
    except KeyError as e:
        msg = f'Ошибка доступа по ключу homework_name: {e}'
        logger.error(msg)
    try:
        homework_status = homework.get('status')
    except KeyError as e:
        msg = f'Ошибка доступа по ключу status: {e}'
        logger.error(msg)

    verdict = HOMEWORK_STATUSES[homework_status]
    if verdict is None:
        msg = 'Неизвестный статус домашки'
        logger.error(msg)
        raise Exception(msg)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PRACTICUM_TOKEN])


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    check_result = check_tokens()
    if check_result is False:
        message = 'Проблемы с переменными окружения'
        logger.critical(message)
        raise SystemExit(message)

    while True:
        try:
            response = get_api_answer(current_timestamp)
            print(response)
            if 'current_date' in response:
                current_timestamp = response['current_date']
            homework = check_response(response)
            if homework is not None:
                message = parse_status(*homework)
                if message is not None:
                    send_message(bot, message)
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
