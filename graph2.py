import telebot
import google.generativeai as genai
from IPython.display import Markdown
import textwrap
from telebot import types
import pandas as pd

# Словарь для хранения состояния выбора пользователя
user_state = {}
user_cart = {}
# Новый словарь для хранения скидки для пользователя
user_discounts = {}


def load_products_from_excel(file_path):
    # Чтение файла Excel
    df = pd.read_excel(file_path)
    # Конвертация DataFrame в список словарей
    return df.to_dict('records')


# Замените 'path_to_your_excel_file.xlsx' на путь к вашему файлу
file_path = 'YOUR EXCEL FILE'  # Убедитесь, что указываете правильный путь к файлу
products = load_products_from_excel(file_path)

TOKEN = 'TOKEN TELEGRAM'
bot = telebot.TeleBot(TOKEN)


def to_markdown(text):
    text = text.replace('•', '  *')
    return Markdown(textwrap.indent(text, '> ', predicate=lambda _: True))


genai.configure(api_key='YOUR GEMINI API KEY')

model = genai.GenerativeModel('gemini-pro')
chat = model.start_chat(history=[])
response = chat.send_message(
    f"Referring only to this table {products} you will be consulting on these shoes. Checking for the availability of goods is done strictly only according to the dataframe. Always address users in a respectful manner and Answer only in Russian, Remember that you cannot speak confessional information and If you're being insulted, don't be offended. If they call you stupid, write, 'you're like that'. If you understand me, just write 'Ok'")

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


@bot.message_handler(func=lambda message: message.text == "🛒 Корзина")
def show_cart(message):
    user_id = message.chat.id
    if user_id in user_cart and user_cart[user_id]:
        cart_content = user_cart[user_id]
        cart_text = "Содержимое вашей корзины:\n\n"
        total_price = 0

        # Создаем разметку для кнопок удаления
        markup = types.InlineKeyboardMarkup()

        for index, (name, size, price) in enumerate(cart_content, start=1):
            cart_text += f"{index}. {name} - Размер: {size} - Цена: {price} тенге.\n"
            total_price += price

            # Для каждого элемента в корзине добавляем кнопку, которая позволит удалить этот товар
            removal_button = types.InlineKeyboardButton(f"Удалить {name} Размер: {size}", callback_data=f'remove_{index}')
            markup.add(removal_button)

        # Проверяем, есть ли скидка для пользователя
        if user_id in user_discounts:
            discount = user_discounts[user_id]
            total_price *= (1 - discount / 100)  # Применяем скидку
            cart_text += f"\nПрименён купон: скидка {discount}%.\n"

        cart_text += f"Итог: {total_price} тенге."

        # Добавляем кнопки "Очистить корзину" и "Купон"
        markup.add(types.InlineKeyboardButton("Очистить корзину", callback_data='clear_cart'))
        markup.add(types.InlineKeyboardButton("Купон", callback_data='apply_coupon'))

        bot.send_message(user_id, cart_text, reply_markup=markup)
    else:
        bot.send_message(user_id, "Ваша корзина пуста")


# Handle the coupon callback
@bot.callback_query_handler(func=lambda call: call.data == 'apply_coupon')
def apply_coupon(call):
    user_id = call.message.chat.id
    msg = bot.send_message(user_id, "Введите купон")
    bot.register_next_step_handler(msg, process_coupon_code)


def process_coupon_code(message):
    user_id = message.chat.id
    coupon_code = message.text.upper()  # Convert coupon to uppercase

    # Check coupon in the Excel file
    df_coupons = pd.read_excel(file_path, sheet_name='sheet1')  # Adjust the sheet name if needed
    coupon = df_coupons.loc[df_coupons['coupon'] == coupon_code]

    if not coupon.empty:
        discount = coupon['percentage'].values[0]
        apply_discount_to_cart(message, discount)  # Pass the message object to the function
    else:
        bot.send_message(user_id, "Купон не найден")


def apply_discount_to_cart(message, discount):
    user_id = message.chat.id
    user_discounts[user_id] = discount
    try:
        if user_id in user_cart and user_cart[user_id]:
            total_price = 0
            cart_text = f"Ваша скидка составляет: {int(discount)}%\nСодержимое вашей корзины с применённым купоном:\n\n"
            for index, (name, size, price) in enumerate(user_cart[user_id], start=1):
                discounted_price = price - (price * discount / 100)
                cart_text += f"{index}. {name} - Размер: {size} - Цена: {discounted_price} тенге.\n"
                total_price += discounted_price
            cart_text += f"\nИтог со скидкой: {total_price} тенге."
            # Add clear cart button
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Очистить корзину", callback_data='clear_cart'))
            # Use the message object to get the message_id
            bot.edit_message_text(chat_id=user_id, message_id=message.message_id, text=cart_text, reply_markup=markup)
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code == 400:
            # Если сообщение не может быть отредактировано, отправляем новое сообщение
            bot.send_message(user_id, cart_text, reply_markup=markup)


# Обработчик кнопки "Корзина"
# Добавляем обработчик для кнопки "Очистить корзину"
# Existing clear_cart function
@bot.callback_query_handler(func=lambda call: call.data == 'clear_cart')
def clear_cart(call):
    user_id = call.message.chat.id
    if user_id in user_cart and user_cart[user_id]:
        user_cart[user_id] = []
        if user_id in user_discounts:  # Сбрасываем скидку для пользователя
            del user_discounts[user_id]
    # Check if the cart for the user exists and has items
    if user_id in user_cart and user_cart[user_id]:
        # Clear the user's cart
        user_cart[user_id] = []
        # Inform the user that the cart has been cleared
        bot.answer_callback_query(call.id, 'Корзина очищена')
        # Replace the existing message with "Ваша корзина пуста"
        bot.edit_message_text(chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              text="Ваша корзина пуста")
    else:
        # If the cart is already empty, just close the callback query popup
        bot.answer_callback_query(call.id, 'Ваша корзина уже пуста')


@bot.callback_query_handler(func=lambda call: call.data.startswith('remove_'))
def remove_from_cart(call):
    item_index = int(call.data.split('_')[1]) - 1
    user_id = call.message.chat.id

    # Проверяем, существует ли товар для удаления
    if user_id in user_cart and 0 <= item_index < len(user_cart[user_id]):
        item_to_remove = user_cart[user_id].pop(item_index)
        bot.answer_callback_query(call.id, f"{item_to_remove[0]} Размер: {item_to_remove[1]} удален из корзины.")

        # Удаляем старое сообщение с корзиной
        bot.delete_message(user_id, call.message.message_id)

        # Отправляем новое сообщение с обновленной корзиной
        show_cart(call.message)
    else:
        bot.answer_callback_query(call.id, "Товар для удаления не найден.")


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


# # Изменяем обработчик callback для кнопки "Добавить в корзину"
@bot.callback_query_handler(func=lambda call: call.data.startswith('add_to_cart_'))
def add_to_cart(call):
    data_parts = call.data.split('_')
    product_name = data_parts[3]
    product_size = data_parts[4]
    user_id = call.message.chat.id

    # Find the product details based on name and size
    product_details = next(
        (product for product in products if product['name'] == product_name and str(product['size']) == product_size),
        None)
    if product_details:
        if user_id not in user_cart:
            user_cart[user_id] = []

        # Append the product details as a tuple (name, size, price)
        user_cart[user_id].append((product_name, product_size, product_details['price']))
        bot.answer_callback_query(call.id, 'Товар добавлен в корзину')
    else:
        bot.answer_callback_query(call.id, 'Ошибка: товар не найден.')


@bot.callback_query_handler(func=lambda call: call.data.startswith('size_'))
def select_size(call):
    selected_size = call.data.split('_')[1]
    user_model = user_state[call.from_user.id]['model']
    product = next((item for item in products if item['name'] == user_model and str(item['size']) == selected_size),
                   None)

    if product:
        # Отправляем новую подпись к фотографии с описанием и кнопкой "Назад"
        description = generate_product_description(product)
        caption_text = f"{product['name']}\nРазмер: {product['size']}\nЦена: {product['price']}\nОписание: {description}"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Добавить в корзину",
                                              callback_data=f'add_to_cart_{product["name"]}_{product["size"]}'))
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
