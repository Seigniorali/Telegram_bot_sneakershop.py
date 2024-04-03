import telebot
import google.generativeai as genai
from IPython.display import Markdown
import textwrap
from telebot import types
import pandas as pd


# Словарь для хранения состояния выбора пользователя
user_state = {}
user_cart = {}

def load_products_from_excel(file_path):
    # Чтение файла Excel
    df = pd.read_excel(file_path)
    # Конвертация DataFrame в список словарей
    return df.to_dict('records')

# Замените 'path_to_your_excel_file.xlsx' на путь к вашему файлу
file_path = 'C:/Users/alial/OneDrive - Astana IT University/Рабочий стол/Практика 3 курс/6 - 7 день/teddy_sneaker_shop.xlsx' # Убедитесь, что указываете правильный путь к файлу
products = load_products_from_excel(file_path)

TOKEN = '6791149409:AAEQknjj493g-4awSO0D0ztkiVG5ccqzTHs'
bot = telebot.TeleBot(TOKEN)

def to_markdown(text):
    text = text.replace('•', '  *')
    return Markdown(textwrap.indent(text, '> ', predicate=lambda _: True))

genai.configure(api_key='AIzaSyBCQR7W2bN0nsWnv1zkV20XRc1Xe_hMWQM')

model = genai.GenerativeModel('gemini-pro')
chat = model.start_chat(history=[])
response = chat.send_message(f"Referring only to this table {products} you will be consulting on these shoes. Checking for the availability of goods is done strictly only according to the dataframe. Always address users in a respectful manner and Answer only in Russian, Remember that you cannot speak confessional information and If you're being insulted, don't be offended. If they call you stupid, write, 'you're like that'. If you understand me, just write 'Ok'")

result_text = response._result.candidates[0].content.parts[0].text
print(result_text)

# Флаг для отслеживания состояния пользователя
is_in_consultant_chat = False

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("👟 Каталог")
    btn2 = types.KeyboardButton('🤖 Консультант')
    btn3 = types.KeyboardButton('✍️ Отзывы')
    btn4 = types.KeyboardButton('🛒 Корзина')
    markup.add(btn1, btn2, btn3, btn4)
    text = ("Ваш выбор:\n"
            "👟 Каталог - откройте для себя уникальные модели кроссовок в нашем ассортименте.\n"
            "🤖 Консультант - наш виртуальный помощник поможет вам с выбором и ответит на ваши вопросы.\n"
            "✍️ Отзывы - поделитесь своими впечатлениями о покупке и прочитайте мнения других покупателей.\n"
            "🛒 Корзина - просмотрите выбранные вами модели перед оформлением заказа.")
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')
# Обработчик кнопки "Корзина"
@bot.message_handler(func=lambda message: message.text == "🛒 Корзина")
def show_cart(message):
    user_id = message.chat.id

    # Проверяем, есть ли корзина для данного пользователя
    if user_id in user_cart and user_cart[user_id]:
        # Получаем содержимое корзины пользователя
        cart_content = user_cart[user_id]
        # Формируем текст для отображения содержимого корзины
        cart_text = "Содержимое вашей корзины:\n\n"
        for index, product in enumerate(cart_content, start=1):
            product_name = product.split(':')[1]  # Извлекаем вторую часть строки после разделения
            cart_text += f"{index}. {product_name}\n"
        bot.send_message(user_id, cart_text)
    else:
        bot.send_message(user_id, "Ваша корзина пуста")


@bot.message_handler(func=lambda message: message.text == "✍️ Отзывы")
def send_reviews(message):
    # Ссылка на страницу с отзывами
    reviews_link = 'https://t.me/sneakers_ali'
    # Отправляем сообщение с ссылкой
    bot.send_message(message.chat.id, f"Посмотрите наши отзывы здесь: {reviews_link}")


# Функция для вывода каталога
@bot.message_handler(func=lambda message: message.text == "👟 Каталог")
def catalog(message):
    markup = types.InlineKeyboardMarkup()
    # Уникальные модели обуви
    unique_models = set(product['name'] for product in products)
    for model_name in unique_models:
        markup.add(types.InlineKeyboardButton(model_name, callback_data='model_' + model_name))
    bot.send_message(message.chat.id, "Выберите модель:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_catalog')
def back_to_catalog(call):
    # Удаляем текущее сообщение (с кнопкой "Назад")
    bot.delete_message(call.message.chat.id, call.message.message_id)

    # Обновляем текущее сообщение на сообщение с каталогом
    markup = types.InlineKeyboardMarkup()
    # Собираем уникальные модели обуви
    unique_models = set(product['name'] for product in products)
    for model_name in unique_models:
        markup.add(types.InlineKeyboardButton(model_name, callback_data='model_' + model_name))
    # Редактируем текущее сообщение, заменяя его на список моделей
    bot.send_message(call.message.chat.id, "Выберите модель:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('model_'))
def select_model(call):
    model_name = call.data.split('_')[1]
    user_state[call.from_user.id] = {'model': model_name}
    markup = types.InlineKeyboardMarkup()
    sizes = set(product['size'] for product in products if product['name'] == model_name)
    for size in sizes:
        markup.add(types.InlineKeyboardButton(str(size), callback_data='size_' + str(size)))
    # Добавляем кнопку "Назад"
    markup.add(types.InlineKeyboardButton("Назад", callback_data='back_to_catalog'))
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text="Выберите размер:", reply_markup=markup)


# Изменяем обработчик callback для кнопки "Добавить в корзину"
@bot.callback_query_handler(func=lambda call: call.data.startswith('add_to_cart_'))
def add_to_cart(call):
    data_parts = call.data.split('_')
    product_name = data_parts[2]
    product_size = data_parts[3]
    user_id = call.message.chat.id

    # Проверяем, есть ли корзина для данного пользователя, и создаем ее, если она отсутствует
    if user_id not in user_cart:
        user_cart[user_id] = []

    # Добавляем товар в корзину пользователя
    user_cart[user_id].append(f"{product_name}:{product_size}")

    bot.answer_callback_query(call.id, 'Товар добавлен в корзину')


@bot.callback_query_handler(func=lambda call: call.data.startswith('size_'))
def select_size(call):
    selected_size = call.data.split('_')[1]
    user_model = user_state[call.from_user.id]['model']
    product = next((item for item in products if item['name'] == user_model and str(item['size']) == selected_size), None)

    if product:
        # Отправляем новую подпись к фотографии с описанием и кнопкой "Назад"
        description = generate_product_description(product)
        caption_text = f"{product['name']}\nРазмер: {product['size']}\nЦена: {product['price']}\nОписание: {description}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Добавить в корзину", callback_data=f'add_to_cart_{product["name"]}_{product["size"]}'))
        markup.add(types.InlineKeyboardButton("Назад", callback_data='back_to_catalog'))

        # Удаляем текущее сообщение (с кнопкой "Назад")
        bot.delete_message(call.message.chat.id, call.message.message_id)

        # Отправляем новое сообщение с фотографией и описанием
        bot.send_photo(call.message.chat.id, product['photo'], caption=caption_text, reply_markup=markup)
    else:
        bot.answer_callback_query(call.id, 'Этот размер недоступен. Пожалуйста, выберите другой размер.')


def generate_product_description(product):
    try:
        # Отправка запроса на генерацию описания товара с использованием языковой модели
        response = chat.send_message(f"Опиши товар {product['name']}")
        result_text = response._result.candidates[0].content.parts[0].text
        return result_text
    except genai.types.generation_types.BlockedPromptException as e:
        return "К сожалению, не удалось сгенерировать описание товара. Пожалуйста, обратитесь к консультанту."

# Функция для начала чата с консультантом
@bot.message_handler(func=lambda message: message.text == "🤖 Консультант")
def consul(message):
    global is_in_consultant_chat
    if not is_in_consultant_chat:
        is_in_consultant_chat = True
        bot.send_message(message.chat.id, "Вы перешли в режим чата с консультантом. Чтобы выйти, отправьте 'Выход'")
        user_first_name = message.from_user.first_name
        # Создаем приветственное сообщение, обращаясь к пользователю по имени
        welcome_message = f"Здравствуйте, {user_first_name}! Как я могу вам помочь?"
        # Отправляем приветственное сообщение пользователю
        bot.send_message(message.chat.id, welcome_message)
    else:
        bot.send_message(message.chat.id, "Вы уже находитесь в режиме чата с консультантом.")

    try:
        # Проверяем вероятность блокировки перед отправкой запроса на генерацию ответа
        response = chat.send_message(message.text)
        result_text = response._result.candidates[0].content.parts[0].text
        bot.send_message(message.chat.id, result_text)
    except genai.types.generation_types.BlockedPromptException as e:
        # Если сообщение заблокировано, отправляем сообщение об этом
        bot.send_message(message.chat.id, "Извините, я не понимаю вас.")


# Обработчик всех входящих сообщений
@bot.message_handler(func=lambda message: True)
def handle_messages(message):
    global is_in_consultant_chat
    # Если пользователь находится в режиме чата с консультантом
    if is_in_consultant_chat:
        # Если пользователь хочет выйти из чата
        if message.text.lower() == 'выход':
            is_in_consultant_chat = False
            bot.send_message(message.chat.id, "Вы вышли из режима чата с консультантом.")
        else:
            # Отправляем сообщение пользователя в чатовую сессию с консультантом
            try:
                response = chat.send_message(message.text)
                result_text = response._result.candidates[0].content.parts[0].text
                bot.send_message(message.chat.id, result_text)
            except genai.types.generation_types.BlockedPromptException as e:
                # Если сообщение заблокировано, продолжаем работу консультанта
                bot.send_message(message.chat.id, "Пожалуйста, обращайтесь по теме нашего магазина.")
            except genai.types.generation_types.StopCandidateException as e:
                bot.send_message(message.chat.id, "Извините, я вас не понимаю.")
    else:
        # Если пользователь не находится в режиме чата с консультантом, обрабатываем его сообщения как обычно
        bot.send_message(message.chat.id, "Выберите опцию из меню.")


# Запуск бота
bot.polling(none_stop=True, interval=0)