import logging
import os
import sys
import time
from http import HTTPStatus
from typing import List

import requests
from dotenv import load_dotenv
from requests.exceptions import RequestException
from telebot import TeleBot
from telebot.apihelper import ApiException

from exceptions import InvalidResponseError

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)


def check_tokens() -> bool:
    """Проверяет доступность переменных окружения."""
    required_tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    stop_reason = ''
    for token in required_tokens:
        if not token:
            stop_reason += f'Токен {token} отсутсвует'
            logger.critical(f'Отсутствует переменная окружения: {token}')
    if stop_reason:
        logger.critical(stop_reason)
        sys.exit(stop_reason)


def send_message(bot: TeleBot, message: str) -> bool:
    """Отправляет сообщение в Telegram-чат."""
    try:
        logger.debug('Начало отправки сообщения')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except (
        ApiException,
        RequestException,
    ) as error:
        logger.error(f'Ошибка при отправке сообщения: {error}')
        return False
    else:
        logger.debug('Сообщение отправлено успешно')
        return True


def get_api_answer(timestamp: int) -> dict:
    """Делает запрос к единственному эндпоинту API-сервиса."""
    params = {'from_date': timestamp}
    try:
        logger.debug('Начало запроса к API')
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            raise InvalidResponseError(
                f'API вернул некорректный статус код: {response.status_code}'
            )
        return response.json()
    except requests.RequestException as error:
        raise InvalidResponseError(f'Ошибка запроса к API: {error}')


def check_response(response: dict) -> List[dict]:
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('Ответ API должен быть словарем')
    if 'homeworks' not in response:
        raise KeyError('В ответе API отсутствует ключ homeworks')
    if not isinstance(response['homeworks'], list):
        raise TypeError('Значение ключа homeworks должно быть списком')
    return response['homeworks']


def parse_status(homework: dict) -> str:
    """Провеяет информации о статусе конкретной домашней работы."""
    if 'homework_name' not in homework or 'status' not in homework:
        raise KeyError('Отсутствуют необходимые ключи в ответе API')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError(
            f'Неизвестный статус домашней работы: '
            f'{homework_status}'
        )
    verdict = HOMEWORK_VERDICTS[homework_status]
    return (
        f'Изменился статус проверки работы "{homework_name}".'
        f'{verdict}'
    )


def main():
    """Основная логика работы бота."""
    current_error = ''
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    check_tokens()
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                status_message = parse_status(homeworks[0])
                message_sent = send_message(bot, status_message)
                if message_sent:
                    timestamp = response.get('current_date')
                    current_error = ''
            else:
                logger.debug('Нет новых статусов')
        except Exception as error:
            if current_error != error:
                message = f'Сбой в работе программы: {error}'
                logger.error(message)
                send_message(bot, message)
                current_error = error
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s - %(name)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('main.log', encoding='UTF-8')
        ]
    )

    main()
