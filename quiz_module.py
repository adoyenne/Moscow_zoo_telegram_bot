import logging
import random
import vk_api
import requests
from questionnaire import questions, animals_descriptions, animals
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from error_handler import ErrorHandledClass, error_handler_decorator
from urllib.parse import urlencode
from config import vk_app_id, vk_secure_key, vk_service_key

error_handler = ErrorHandledClass()

logger = logging.getLogger(__name__)


import json
@error_handler_decorator
class UserData:
    def __init__(self, file_path):
        self.file_path = file_path
        self.data = {}

    def load(self):
        try:
            with open(self.file_path, 'r') as file:
                self.data = json.load(file)
        except FileNotFoundError:
            # If the file doesn't exist, initialize an empty dictionary
            self.data = {}

    def save(self):
        with open(self.file_path, 'w') as file:
            json.dump(self.data, file)

    # Define getter and setter methods for individual attributes
    @property
    def current_question_index(self):
        return self.data.get("current_question_index", 0)

    @current_question_index.setter
    def current_question_index(self, value):
        self.data["current_question_index"] = value

    @property
    def correct_answers_count(self):
        return self.data.get("correct_answers_count", 0)

    @correct_answers_count.setter
    def correct_answers_count(self, value):
        self.data["correct_answers_count"] = value


    @property
    def animals(self):
        return self.data.get("animals", animals)

    @animals.setter
    def animals(self, value):
        self.data["animals"] = value

@error_handler_decorator
class Quiz:
    def __init__(self, bot, message, user_id):
        self.bot = bot
        self.bot_username = "https://t.me/Zoo_quiz_bot"
        self.message = message
        self.photo = []
        self.user_id = user_id
        self.user_data = UserData("user_data.json")
        self.user_data.load()

        # Initialize or reset user data attributes
        self.user_data.used_questions = set()
        self.user_data.current_question_index = 0
        self.user_data.correct_answers_count = 0
        self.user_data.animals = animals
        self.user_data.totem_animal = None
        self.user_data.current_question = None
        self.user_data.question_message = None

        #Вопросы
        self.questions=questions


        # Список фраз
        self.phrases = [
            "Это был классный ответ!",
            "Круто! Продолжайте в том же духе!",
            "Здорово! Вы молодец!",
            "Узнаём о вас всё больше и больше! Продолжайте!",
            "О, как интересно!",
            "Ого, не знал!",

        ]

        # Словарь с описаниями каждого животного
        self.animals_descriptions = animals_descriptions

        # Информация о программе опеки
        self.program_info = (
            "Наша программа по опеке о природе и животных призвана сохранять и защищать биоразнообразие нашей планеты. "
            "Мы предоставляем помощь и уход за животными, а также осуществляем проекты по сохранению их естественных местообитаний. "
            "Присоединяйтесь к нам и станьте частью этого важного движения!"
        )

        # URL сайта Московского зоопарка
        self.zoo_website_url = "https://www.moscowzoo.ru/my-zoo/become-a-guardian/"

        # Путь к папке с фотографиями животных
        self.animals_folder = "animals"

        #поддержка соцсетей:
        self.vk_app_id = vk_app_id
        self.vk_secure_key = vk_secure_key
        self.vk_service_key = vk_service_key
        self.vk_redirect_url = "https://d474-145-108-246-137.ngrok-free.app/auth/vk/callback"  #d474-145-108-246-137.ngrok-free.app получен с помощью сервиса ngrok!


    def start_quiz(self):
        logger.info("User %s started the quiz.", self.message.from_user.first_name)
        self.send_question()

    def send_question(self):
        if not self.user_data.current_question:
            unused_questions = list(set(self.questions.keys()) - self.user_data.used_questions)
            if not unused_questions:
                self.finish_quiz()
                return
            self.user_data.current_question = random.choice(unused_questions)

        options = self.questions[self.user_data.current_question]
        self.user_data.question_message = f"{self.user_data.current_question}\n\n"
        for option in options:
            self.user_data.question_message += f"{option}. {options[option]['text']}\n"
        self.bot.send_message(self.message.chat.id, self.user_data.question_message)

    def handle_answer(self, user_answer):
        question_text = self.user_data.current_question
        if user_answer not in self.questions[question_text]:
            self.bot.send_message(self.message.chat.id, "К сожалению, вы ввели неправильный вариант. Попробуйте снова.")
            self.bot.send_message(self.message.chat.id, self.user_data.question_message)
            return

        animal = self.questions[question_text][user_answer]['animal']
        self.user_data.animals[animal] = self.user_data.animals.get(animal, 0) + 1
        self.user_data.used_questions.add(question_text)

        # Выводим случайную фразу
        random_phrase = random.choice(list(self.phrases))
        self.bot.send_message(self.message.chat.id, random_phrase)

        self.user_data.current_question = None
        self.send_question()

    def restart_quiz(self, message, user_id=None):
        if message.text.lower() == 'да':
            # Обновляем данные пользователя перед началом новой викторины
            self.user_data.used_questions = set()
            self.user_data.current_question_index = 0
            self.user_data.correct_answers_count = 0
            self.user_data.animals = animals
            self.start_quiz()
        elif message.text.lower() == 'нет':
            bye_message = "Спасибо за участие! До новых встреч и ждём Вас снова!😊"
            # Открываем файл с изображением
            with open('bye.jpg', 'rb') as photo:
                self.bot.send_photo(self.message.chat.id, photo, caption=bye_message)
        else:
            self.bot.send_message(self.message.chat.id, "Начинаем заново? Введите 'Да' или 'Нет', пожалуйста.")
            self.bot.register_next_step_handler(message, self.restart_quiz)  # Убрали user_id из лямбда-функции

    # Изменяем сигнатуру метода finish_quiz, чтобы принимал аргумент code
    def finish_quiz(self):
        animals = self.user_data.animals
        self.user_data.totem_animal = max(animals, key=animals.get)
        message_text = f"Поздравляем! Викторина завершена. Ваше тотемное животное: {self.user_data.totem_animal}. "
        # Добавляем описание выбранного животного, если оно доступно
        if self.user_data.totem_animal in self.animals_descriptions:
            message_text += f"{self.animals_descriptions[self.user_data.totem_animal]}"

        # Проверяем наличие фотографии выбранного животного
        photo_path = os.path.join(self.animals_folder, f"{self.user_data.totem_animal}.jpg")
        if os.path.exists(photo_path):
            with open(photo_path, "rb") as photo:
                self.photo = self.bot.send_photo(self.message.chat.id, photo, caption=message_text)

        else:
            self.bot.send_message(self.message.chat.id,
                                  message_text + "К сожалению, фотография этого животного сейчас не доступна😔")


        self.user_data.save()  # Сохраняем их обратно в файл

        # Добавляем информацию о программе опеки и кнопку-ссылку для авторизации в VK
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("Хотите узнать больше об опеке?", url=self.zoo_website_url))
        #keyboard.add(InlineKeyboardButton("Поддержка социальных сетей", callback_data='social_network_post', url=self.vk_authorization_url))
        # Add a button for social network support
        keyboard.add(InlineKeyboardButton("Поддержка социальных сетей", callback_data='social_network_support'))

        keyboard.add(InlineKeyboardButton("Связаться с сотрудником зоопарка", callback_data='forward_results'))
        keyboard.add(InlineKeyboardButton("Оставить отзыв", callback_data='leave_feedback'))
        keyboard.add(InlineKeyboardButton("Хотите попробовать викторину снова?", callback_data='restart_quiz'))

        self.bot.send_message(self.message.chat.id, self.program_info, reply_markup=keyboard)



    def get_authorization_url(self, client_id, redirect_uri):
        params = {
                "client_id": self.vk_app_id,
                "redirect_uri": self.vk_redirect_url,
                "scope": "wall",
                "response_type": "code",
                "display": "page"
        }
        url = f"https://oauth.vk.com/authorize?{urlencode(params)}"
        return url


    def handle_callback_query(self, call: CallbackQuery):

        if call.data == 'restart_quiz':
            # Restart the quiz
            self.restart_quiz(call.message)
        elif call.data == 'leave_feedback':
            self.bot.send_message(call.from_user.id, "Пожалуйста, оставьте ваш отзыв:")
            self.bot.register_next_step_handler(call.message, self.process_feedback)

        if call.data == 'forward_results':  # Если нажата кнопка "Связаться с сотрудником зоопарка"

            # Отправляем пользователю запрос на написание сообщения
            self.bot.send_message(call.message.chat.id, "Пожалуйста, напишите ваше сообщение для сотрудника зоопарка:")

            # Ожидаем следующее сообщение от пользователя, чтобы передать его сотруднику зоопарка
            self.bot.register_next_step_handler(call.message, self.send_message_to_zoo_employee)



        elif call.data == 'social_network_support':
            # Здесь используем метод для создания промежуточного URL
            auth_url = self.get_authorization_url(self.vk_app_id, self.vk_redirect_url)
            # Создаем InlineKeyboardButton с промежуточным URL
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("VK", url=auth_url))

            # Отправляем сообщение с кнопкой в бот
            self.bot.send_message(call.message.chat.id, "Нажмите сюда, для авторизации через VK:",
                                  reply_markup=keyboard)



    def handle_vk_authorization(self, code):
        try:
            print("Handling VK authorization...")
            # Обмен кода авторизации на токен доступа
            access_token = self.exchange_code_for_access_token(code)
            print("Received access token.")
            # Использование access token для публикации результатов викторины на стене VK
            self.publish_quiz_results(access_token)
        except RuntimeError as e:
            logger.error(f"Failed VK authorization: {e}")
            self.bot.send_message(self.message.chat.id, "Failed to authorize with VK. Please try again later.")

    def exchange_code_for_access_token(self, code):
        token_url = "https://oauth.vk.com/access_token"
        params = {
            "client_id": self.vk_app_id,
            "client_secret": self.vk_secure_key,
            "redirect_uri": self.vk_redirect_url,
            "code": code
        }
        response = requests.get(token_url, params=params)
        if response.status_code == 200:
            data = response.json()
            access_token = data.get("access_token")
            if access_token:
                return access_token
            else:
                raise ValueError("Access token not found in the response.")
        else:
            raise RuntimeError("Failed to exchange authorization code for access token.")

    def publish_quiz_results(self, access_token):
        try:
            print("Publishing quiz results on VKontakte...")
            vk_session = vk_api.VkApi(token=access_token)
            vk = vk_session.get_api()

            message = f"Я прошел викторину и мое тотемное животное: {self.user_data.totem_animal}. Попробуйте викторину сами в {self.bot_username}."
            print("Message to be posted on VK:", message)
            vk.wall.post(owner_id=self.user_id, message=message)

            print("Successfully posted quiz results on VKontakte.")
        except vk_api.VkApiError as error_msg:
            raise RuntimeError(f"Failed to post quiz results on VKontakte: {error_msg}")


    def process_feedback(self, message):
        # Здесь вы можете обработать полученный отзыв, например, записать его в файл или базу данных
        feedback = message.text
        user_id = message.from_user.id
        # Запишите отзыв и идентификатор пользователя в файл или базу данных
        with open("feedback_from_users_zoo_bot.txt", "a") as file:
            file.write(f"User ID: {user_id}, Feedback: {feedback}\n")
        self.bot.send_message(user_id, "Спасибо за ваш отзыв!")

    def send_message_to_zoo_employee(self,message):
        # Получаем текст сообщения от пользователя
        user_message = message.text

        # Получаем имя пользователя
        user_name = message.from_user.username

        # Формируем сообщение для отправки менеджеру, добавляя имя пользователя
        message_to_manager = (
            f"Здравствуйте! Меня зовут @{user_name}. Я прошёл викторину и моё тотемное животное - {self.user_data.totem_animal}. Я хочу передать следующее сообщение: {user_message}")

        # Никнейм сотрудника зоопарка:
        zoo_employee_username = "1382756222"  # замените на фактический никнейм сотрудника зоопарка

        # Отправка сообщения от пользователя к менеджеру
        self.bot.send_message(zoo_employee_username, message_to_manager)


        # Отправка пользователю уведомления о том, что сообщение было отправлено
        self.bot.send_message(message.chat.id, f"Ваше сообщение было успешно отправлено сотруднику зоопарка 😇. Текст сообщения: {message_to_manager}")



