# homework_bot
python telegram bot
# Описание.

Telegram-бот, который обращается к API сервиса Практикум Домашка и узнает статус вашей домашней работы.

Статусы:

_Нет новых статусов._

_Работа взята на проверку ревьюером._

_Работа проверена: у ревьюера есть замечания._

_Работа проверена: ревьюеру всё понравилось. Ура!_


## Технологии:

    Python 3.9.13
    pyTelegramBotAPI 4.14.1
    python-dotenv 0.20.0


## Инструкция для пользователей Git Bash

1.Клонировать репозиторий и перейти в папку **homework_bot**:

        git clone git@github.com:Rodomir117/homework_bot.git
        cd homework_bot

2.Cоздать и активировать виртуальное окружение:

        py -m venv venv
        source venv/Scripts/activate

3.Установить зависимости из файла requirements.txt:

        pip install -r requirements.txt

4.Создать файл _.env_ и записать в него переменные окружения согласно файлу **.env.example**:

        touch .env

5.Запустить проект:

        python homework.py