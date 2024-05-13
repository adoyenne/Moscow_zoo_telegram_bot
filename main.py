import logging
import telebot
from quiz_module import Quiz
from config import TOKEN
from telebot.types import CallbackQuery
from error_handler import ErrorHandledClass, error_handler_decorator


import traceback

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Создание бота
bot = telebot.TeleBot(TOKEN)


# Создание экземпляра класса ErrorHandler
error_handler = ErrorHandledClass()



# Переменная для хранения объектов викторины в каждом чате
quiz_instances = {}


# Обработчик команды /start

@bot.message_handler(commands=['start'])
@error_handler_decorator
def start(message):
    user = message.from_user
    logger.info("User %s started the conversation.", user.first_name)
    welcome_message = (f"Добро пожаловать {message.from_user.first_name}😊 в Бот Московского Зоопарка!\n\n"
                      "Пройди викторину и ты узнаешь, какое у тебя тотемное животное:)\n\n"
                      "Готов начать? Введите /quiz чтобы посмотреть возможности бота, нажмите /help")
    bot.reply_to(message, welcome_message)


@bot.message_handler(commands=['help'])
@error_handler_decorator
def send_instructions(message):
        instructions = f"Здесь вы можете узнать список возможностей бота:!\n"
        instructions += " \n\n"
        instructions += "Чтобы запустить виктрину, введите /quiz."
        bot.reply_to(message, instructions)



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
        bot.reply_to(message, "Извини, я не понимаю эту команду😔, попробуйте ввести снова?😇")

# Add a handler for callback queries

@bot.callback_query_handler(func=lambda call: True)
@error_handler_decorator
def handle_callback_query(call: CallbackQuery):
    chat_id = call.message.chat.id  # Получаем chat_id для идентификации экземпляра викторины
    print(f"Received callback query from chat_id: {chat_id}")
    print("Received callback query data:", call.data)

    if chat_id in quiz_instances:
        # Pass the callback query to the Quiz instance for handling
        quiz_instances[chat_id].handle_callback_query(call)
    else:
        # Handle the case where the chat_id is not found in quiz_instances
        bot.send_message(chat_id, "Quiz instance not found. Please start a quiz first.")


# Запуск бота
@error_handler_decorator
def main():
    bot.polling()

if __name__ == '__main__':
    main()