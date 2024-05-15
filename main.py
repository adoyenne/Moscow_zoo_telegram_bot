import logging
import telebot
from flask import Flask, request, jsonify
from quiz_module import Quiz
from config import TOKEN
from telebot.types import CallbackQuery
from error_handler import ErrorHandledClass, error_handler_decorator
import threading
import time

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Создание бота
bot = telebot.TeleBot(TOKEN, threaded=False)  # Используем режим long polling


# Создание экземпляра класса ErrorHandler
error_handler = ErrorHandledClass()


# Переменная для хранения объектов викторины в каждом чате
quiz_instances = {}

# Переменная для хранения кода авторизации
authorization_code = None

# Инициализация Flask-приложения
app = Flask(__name__)

# Обработчик промежуточного URL для авторизации VK
@app.route('/auth/vk/callback', methods=['GET'])
@error_handler_decorator
def vk_callback():
    global authorization_code
    code = request.args.get('code')
    if code:
        # Сохранение кода авторизации в переменную
        authorization_code = code

        # Создаем экземпляр класса Quiz
        quiz_instance = Quiz(bot, None, None)

        # Вызов метода handle_vk_authorization для обработки кода авторизации и последубщей публикацией рез викторины в VK
        quiz_instance.handle_vk_authorization(code)

        return jsonify({"ok": True, "code": code})
    else:
        return jsonify({"error": "No code found"}), 400

# Обработчик команды /start
@bot.message_handler(commands=['start'])
@error_handler_decorator
def start(message):
    # Открываем файл с изображением
    with open('hello.jpg', 'rb') as photo:
        # Формируем приветственное сообщение
        welcome_message = (f"Добро пожаловать {message.from_user.first_name} 😊, мы рады приветствовать Вас в боте Московского Зоопарка!\n\n"
                           "Пройдите викторину и Вы узнаете, какое у Вас тотемное животное:)\n\n"
                           "Готовы начать?😇\n\n"
                           "Введите /quiz для начала викторины\n\n"
                           "Введите /help, чтобы посмотреть возможности бота\n\n"
                           "Удачного путешествия в мир животных 😊")

        # Отправляем изображение и приветственное сообщение
        bot.send_photo(message.chat.id, photo, caption=welcome_message)


@bot.message_handler(commands=['help'])
@error_handler_decorator
def send_instructions(message):
    # Открываем файл с изображением
    with open('help.jpg', 'rb') as photo:
        instructions = f"Здесь Вы можете узнать список возможностей бота:\n"
        instructions += " \n"
        instructions += "1. Пройдите викторину и узнаете своё тотемное животное"
        instructions += " \n\n"
        instructions += "2. Делитесь результатами с близкими и друзьями в соцсетях (на данный момент поддерживается VK)"
        instructions += " \n\n"
        instructions += "3. Не забудьте оставить отзыв и пожелание, нам будет безумно приятно😊"
        instructions += " \n\n"
        instructions += "4. Напишите сотруднику зоопарка, чтобы узнать больше"
        instructions += " \n\n"
        instructions += "Введите /quiz для начала викторины\n\n"

        bot.send_photo(message.chat.id, photo, caption=instructions)



# Обработчик команды /quiz

@bot.message_handler(commands=['quiz'])
@error_handler_decorator
def start_quiz_command(message):
    user_id = message.from_user.id
    chat_id = message.chat.id  # Получаем ID чата
    if chat_id not in quiz_instances:
        quiz_instance = Quiz(bot, message, user_id)  # Создаем экземпляр класса Quiz
        quiz_instances[chat_id] = quiz_instance  # Добавляем экземпляр в словарь quiz_instances
        quiz_instance.start_quiz()  # Запускаем викторину

# Обработчик ввода сообщения

@bot.message_handler(func=lambda message: True)
@error_handler_decorator
def handle_message(message):
    user = message.from_user
    text_received = message.text
    logger.info("User %s sent message: %s", user.first_name, text_received)

    # Если экземпляр Quiz существует для данного чата, обрабатываем ответ на вопрос
    if message.chat.id in quiz_instances:
        quiz_instances[message.chat.id].handle_answer(text_received)
    else:
        bot.reply_to(message, "Извините, я не понимаю эту команду😔, попробуйте ввести снова😇")

# Add a handler for callback queries

@bot.callback_query_handler(func=lambda call: True)
@error_handler_decorator
def handle_callback_query(call: CallbackQuery):
    chat_id = call.message.chat.id  # Получаем chat_id для идентификации экземпляра викторины

    if chat_id in quiz_instances:
        # Pass the callback query to the Quiz instance for handling
        quiz_instances[chat_id].handle_callback_query(call)
    else:
        # Handle the case where the chat_id is not found in quiz_instances
        bot.send_message(chat_id, "Quiz instance not found. Please start a quiz first.")

# Обработчик POST-запросов
@app.route('/', methods=['POST'])
def handle_post_request():
    # Обработка POST-запроса
    return 'OK', 200


# Запуск бота
@error_handler_decorator
def main():
    bot.remove_webhook()  # Удаляем вебхук перед запуском бота в режиме long polling
    print("Webhook removed successfully.")  # Выводим сообщение об успешном удалении вебхука

    # Запуск бота в режиме long polling
    bot_polling_thread = threading.Thread(target=bot_polling)
    bot_polling_thread.start()

    app.run(port=5001)  # Запуск Flask-приложения на порту 5001


def bot_polling():
    while True:
        try:
            bot.infinity_polling(none_stop=True)
        except Exception as e:
            logger.error("Polling exception: {}".format(e))
            time.sleep(5)


if __name__ == '__main__':
    main()

