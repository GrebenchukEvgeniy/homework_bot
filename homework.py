import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

import exceptions

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
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


def send_message(bot, message):
    """Отправляет сообщения."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Отправлено сообщение: "{message}"')
    except telegram.error.TelegramError as error:
        message = f'Cбой отправки сообщения, ошибка: {error}'
        raise exceptions.APIAnswerError(message)


def get_api_answer(current_timestamp):
    """Запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception:
        message = 'Ошибка API'
        raise exceptions.APIAnswerError(message)
    if response.status_code != HTTPStatus.OK:
        message = 'Код энпоинта не 200'
        raise exceptions.APIAnswerError(message)
    return response.json()


def check_response(response):
    """Проверяет полученный ответ на корректность."""
    msg = 'Начало проверки ответа сервера'
    logger.info(msg)
    if not isinstance(response, dict):
        msg = 'Ответ API не словарь'
        raise TypeError(msg)
    homeworks_list = response['homeworks']
    if 'homeworks' not in response:
        msg = 'Ошибка доступа по ключу homeworks'
        logger.error(msg)
        raise KeyError(msg)
    if homeworks_list is None:
        msg = 'В ответе API нет словаря с ДЗ'
        logger.error(msg)
        raise exceptions.CheckResponseException(msg)
    if len(homeworks_list) == 0:
        msg = 'За последнее время нет изменения домашки'
        logger.error(msg)
        raise exceptions.CheckResponseException(msg)
    if not isinstance(homeworks_list, list):
        msg = 'В ответе API домашки представлены не списком'
        logger.error(msg)
        raise exceptions.CheckResponseException(msg)
    return homeworks_list


def parse_status(homework):
    """Формирует сообщение с обновленным статусом для отправки."""
    homework_name = homework.get('homework_name')
    if 'homework_name' not in homework:
        msg = 'Ошибка доступа по ключу homework_name'
        logger.error(msg)
        raise KeyError(msg)
    homework_status = homework.get('status')
    if 'status' not in homework:
        msg = 'Ошибка доступа по ключу status'
        logger.error(msg)
        raise exceptions.CheckResponseException(msg)
    try:
        if homework_status in HOMEWORK_VERDICTS:
            verdict = HOMEWORK_VERDICTS.get(homework_status)
        else:
            message = 'Статус ответа не известен'
            raise exceptions.CheckResponseException(message)
    except KeyError:
        msg = 'Неизвестный статус домашки'
        raise exceptions.CheckResponseException(msg)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PRACTICUM_TOKEN])


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    check_result = check_tokens()
    if not check_result:
        message = 'Проблемы с переменными окружения'
        logger.critical(message)
        raise sys.exit(message)

    while True:
        try:
            response = get_api_answer(current_timestamp)
            if 'current_date' in response:
                current_timestamp = response['current_date']
            homework = check_response(response)
            if homework is not None:
                message = parse_status(*homework)
                if message is not None:
                    send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.exception(message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
