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
    tokens = True
    required_tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    for token in required_tokens:
        if not token:
            logger.critical(f'Отсутствует переменная окружения: {token}')
            tokens = False
    return tokens


def send_message(bot: TeleBot, message: str) -> None:
    """Отправляет сообщение в Telegram-чат."""
    try:
        logger.debug('Начало отправки сообщения')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except (
        ApiException,
        RequestException,
    ) as error:
        logger.error(f'Ошибка при отправке сообщения: {error}')
    else:
        logger.debug('Сообщение отправлено успешно')


def get_api_answer(timestamp: int) -> dict:
    """Делает запрос к единственному эндпоинту API-сервиса."""
    params = {'from_date': timestamp}
    try:
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
    if not check_tokens():
        sys.exit('Отсутсвуют токены')
    last_message = ''
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if not homeworks:
                logger.debug('Нет новых статусов')
                continue
            status_message = parse_status(homeworks[0])
            if status_message != last_message:
                if send_message(bot, status_message):
                    last_message = status_message
                    timestamp = response.get('current_date', timestamp)
        except Exception as error:
            error_message = f'Сбой в работе программы: {error}'
            if last_message != error_message:
                logger.error(error_message)
                send_message(bot, error_message)
                last_message = error_message
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
