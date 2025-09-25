import telebot
from telebot import types
import random
import string
from datetime import datetime  # Для дат в тикетах

bot = telebot.TeleBot("8320945675:AAGodPII1I5IBOKYBx_adZFecYsv9-sw1d4")  # Токен основного бота

# КОНФИГУРАЦИЯ АДМИНИСТРАТОРА
ADMIN_IDS = [7339590336]  # ЗАМЕНИТЕ НА ВАШ ТЕЛЕГРАМ ID

# Токен support-бота (замени на реальный от @BotFather для @TradeSupportBot)
SUPPORT_BOT_TOKEN = "8286157115:AAF7JNApuvIO2L9603NfBu9vgzcIgXL7ZF0"  # Создай отдельного бота!

# Базы данных в памяти
users_balance = {}  # Балансы пользователей: user_id -> balance
deals_db = {}  # Активные сделки: deal_id -> deal_info
user_states = {}  # Состояния пользователей: user_id -> state_data
support_tickets = {}  # Для поддержки: user_id -> list of {'type': str, 'content': str, 'date': str}

def is_admin(user_id):
    return user_id in ADMIN_IDS

def generate_deal_id():
    return ''.join(random.choices(string.digits, k=6))

def generate_deal_link(deal_id):
    bot_username = bot.get_me().username
    return f"https://t.me/{bot_username}?start=deal_{deal_id}"

# Функция для отображения главного меню
def show_main_menu(chat_id, user_id):
    first_name = bot.get_chat(user_id).first_name
    welcome_text = (
        f"🌟 <b>Привет</b>, {first_name}!\n"
        "<b>Добро пожаловать</b> в гарант-сервис для безопасных сделок!\n"
        "<b>Trade Guarantor</b> — сервис, который предоставляет возможность <b>безопасно</b> продавать и покупать любые товары. Мы обеспечиваем <b>защиту обеих сторон</b>, прозрачные условия и <b>быстрые выплаты</b>.\n"
        "➖➖➖➖➖➖➖➖➖➖➖➖\n"
        "<b>💼 Что можно сделать:</b>\n"
        "▫️ Создавать сделки и делиться ссылками\n"
        "▫️ Покупать товары с подтверждением оплаты\n"
        "▫️ Проверять баланс и выводить средства\n"
        "▫️ Получать помощь через поддержку\n"
        "➖➖➖➖➖➖➖➖➖➖➖➖\n"
        "Нажмите кнопки ниже, чтобы начать!"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton('🛒 Активные сделки', callback_data='active_deals')
    btn2 = types.InlineKeyboardButton('➕ Создать сделку', callback_data='create_deal')
    btn3 = types.InlineKeyboardButton('📊 Мой профиль', callback_data='my_profile')
    btn4 = types.InlineKeyboardButton('ℹ️ Помощь', callback_data='help')
    btn_support = types.InlineKeyboardButton('🆘 Поддержка', url='https://t.me/TradeGuarantorSupportBot')
    markup.add(btn1, btn2, btn3, btn4, btn_support)

    try:
        with open('welcome_image.jpg', 'rb') as photo:
            bot.send_photo(
                chat_id=chat_id,
                photo=photo,
                caption=welcome_text,
                reply_markup=markup,
                parse_mode='HTML'
            )
    except FileNotFoundError:
        bot.send_message(
            chat_id,
            "⚠️ Картинка не найдена. " + welcome_text,
            reply_markup=markup,
            parse_mode='HTML'
        )

# Обработчики callback_query
@bot.callback_query_handler(func=lambda call: call.data == 'active_deals')
def process_active_deals(call):
    show_active_deals(call.message.chat.id, call.from_user.id)

@bot.callback_query_handler(func=lambda call: call.data == 'create_deal')
def process_create_deal(call):
    create_deal_start(call.message.chat.id, call.from_user.id)

@bot.callback_query_handler(func=lambda call: call.data == 'my_profile')
def process_my_profile(call):
    show_profile(call.message.chat.id, call.from_user.id)

@bot.callback_query_handler(func=lambda call: call.data == 'help')
def process_help(call):
    show_help(call.message.chat.id, call.from_user.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('currency_'))
def handle_currency_selection(call):
    user_id = call.from_user.id
    currency = call.data.split('_')[1]

    if user_id not in user_states or 'description' not in user_states[user_id]:
        bot.answer_callback_query(call.id, "❌ Сессия создания сделки устарела")
        return

    deal_id = generate_deal_id()
    deals_db[deal_id] = {
        "description": user_states[user_id]['description'],
        "amount": user_states[user_id]['amount'],
        "currency": currency,
        "status": "active",
        "seller_id": user_id,
        "buyer_id": None
    }

    del user_states[user_id]

    deal_link = generate_deal_link(deal_id)
    deal_info = (
        "✅ СДЕЛКА СОЗДАНА!\n\n"
        f"▫️ Товар: {deals_db[deal_id]['description']}\n"
        f"▫️ Сумма: {deals_db[deal_id]['amount']} {currency}\n"
        "➖➖➖➖➖➖➖➖➖➖➖➖\n"
        "🔗 Ссылка для покупателя:\n"
        f"{deal_link}\n\n"
        "Поделитесь этой ссылкой с покупателем"
    )

    markup = types.InlineKeyboardMarkup()
    back_btn = types.InlineKeyboardButton('🏠 Назад в меню', callback_data='back_to_menu')
    markup.add(back_btn)
    bot.send_message(call.message.chat.id, deal_info, reply_markup=markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('pay_'))
def handle_payment_confirmation(call):
    deal_id = call.data.split('_')[1]
    user_id = call.from_user.id

    if deal_id not in deals_db:
        bot.answer_callback_query(call.id, "❌ Сделка не найдена")
        return

    deal = deals_db[deal_id]

    if deal['status'] != 'active':
        bot.answer_callback_query(call.id, "⚠️ Сделка уже завершена")
        return

    deal['status'] = 'waiting_delivery'
    deal['buyer_id'] = user_id

    try:
        bot.send_message(
            deal['seller_id'],
            f"💰 ПОКУПАТЕЛЬ ОПЛАТИЛ СДЕЛКУ #{deal_id}\n\n"
            f"▫️ Товар: {deal['description']}\n"
            f"▫️ Сумма: {deal['amount']} {deal['currency']}\n\n"
            "✅ Пожалуйста, отправьте товар покупателю"
        )
    except:
        pass

    markup = types.InlineKeyboardMarkup()
    received_btn = types.InlineKeyboardButton(
        text="📦 Я получил заказ",
        callback_data=f"received_{deal_id}"
    )
    back_btn = types.InlineKeyboardButton('🏠 Назад в меню', callback_data='back_to_menu')
    markup.add(received_btn, back_btn)

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=call.message.text + "\n\n✅ Вы подтвердили оплату. Ожидайте доставку",
        reply_markup=markup
    )
    bot.answer_callback_query(call.id, "✅ Продавец уведомлен об оплате")

@bot.callback_query_handler(func=lambda call: call.data.startswith('received_'))
def handle_goods_received(call):
    deal_id = call.data.split('_')[1]
    user_id = call.from_user.id

    if deal_id not in deals_db:
        bot.answer_callback_query(call.id, "❌ Сделка не найдена")
        return

    deal = deals_db[deal_id]

    if deal['status'] != 'waiting_delivery':
        bot.answer_callback_query(call.id, "⚠️ Статус сделки изменился")
        return

    if user_id != deal['buyer_id']:
        bot.answer_callback_query(call.id, "❌ Вы не покупатель в этой сделке")
        return

    deal['status'] = 'completed'

    if user_id not in users_balance:
        users_balance[user_id] = 0
    users_balance[deal['seller_id']] += deal['amount']

    seller_info = bot.get_chat(deal['seller_id'])
    seller_name = f"@{seller_info.username}" if seller_info.username else seller_info.first_name or str(deal['seller_id'])
    buyer_info = bot.get_chat(user_id)
    buyer_name = f"@{buyer_info.username}" if buyer_info.username else buyer_info.first_name or str(user_id)

    try:
        bot.send_message(
            deal['seller_id'],
            f"🎉 ПОКУПАТЕЛЬ ПОЛУЧИЛ ТОВАР ПО СДЕЛКЕ #{deal_id}\n\n"
            f"▫️ Товар: {deal['description']}\n"
            f"▫️ Сумма: {deal['amount']} {deal['currency']}\n"
            f"▫️ Баланс пополнен: +{deal['amount']} {deal['currency']}\n"
            f"💳 Текущий баланс: {users_balance[deal['seller_id']]} {deal['currency']}"
        )
    except:
        pass

    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(
                admin_id,
                f"🔔 НОВАЯ ЗАВЕРШЁННАЯ СДЕЛКА #{deal_id}\n\n"
                f"▫️ Товар: {deal['description']}\n"
                f"▫️ Сумма: {deal['amount']} {deal['currency']}\n"
                f"▫️ Продавец: {seller_name}\n"
                f"▫️ Покупатель: {buyer_name}\n"
                f"▫️ Статус: Завершена"
            )
        except:
            pass

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=call.message.text + "\n\n✅ Вы подтвердили получение товара. Спасибо за сделку!",
        reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('🏠 Назад в меню', callback_data='back_to_menu'))
    )
    bot.answer_callback_query(call.id, "✅ Продавец уведомлен о получении")

@bot.callback_query_handler(func=lambda call: call.data == 'back_to_menu')
def process_back_to_menu(call):
    show_main_menu(call.message.chat.id, call.from_user.id)
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    if len(message.text.split()) > 1:
        deal_param = message.text.split()[1]
        if deal_param.startswith('deal_'):
            deal_id = deal_param.split('_')[1]
            if deal_id in deals_db:
                show_deal_info(message, deal_id)
                return
    show_main_menu(message.chat.id, user_id)

def show_deal_info(message, deal_id):
    if deal_id not in deals_db:
        bot.reply_to(message, "❌ Сделка не найдена или уже завершена")
        return

    deal = deals_db[deal_id]
    user_id = message.from_user.id

    if deal['status'] == 'completed':
        bot.reply_to(message, "✅ Эта сделка уже успешно завершена")
        return

    if user_id != deal['seller_id']:
        payment_info = (
            f"🛒 СДЕЛКА #{deal_id}\n\n"
            f"▫️ Товар: {deal['description']}\n"
            f"▫️ Сумма: {deal['amount']} {deal['currency']}\n"
            f"▫️ Продавец: скрыт для безопасности\n"
            "➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
            "💳 Реквизиты для оплаты:\n"
            "2200 7342 8532 5543\nСбербанк\nКрачко А.Д.\n\n"
            "⚠️ После оплаты нажмите кнопку подтверждения"
        )

        markup = types.InlineKeyboardMarkup()
        pay_btn = types.InlineKeyboardButton(
            text="✅ Я оплатил",
            callback_data=f"pay_{deal_id}"
        )
        back_btn = types.InlineKeyboardButton('🏠 Назад в меню', callback_data='back_to_menu')
        markup.add(pay_btn, back_btn)

        bot.send_message(
            message.chat.id,
            payment_info,
            reply_markup=markup
        )
    else:
        status_text = "🟢 Активна" if deal['status'] == 'active' else "🟡 Ожидает получения"
        deal_info = (
            f"📦 ВАША СДЕЛКА #{deal_id}\n\n"
            f"▫️ Товар: {deal['description']}\n"
            f"▫️ Сумма: {deal['amount']} {deal['currency']}\n"
            f"▫️ Статус: {status_text}\n"
            "➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
            "🔗 Ссылка для покупателя:\n"
            f"{generate_deal_link(deal_id)}\n\n"
            "Поделитесь этой ссылкой с покупателем"
        )

        markup = types.InlineKeyboardMarkup()
        back_btn = types.InlineKeyboardButton('🏠 Назад в меню', callback_data='back_to_menu')
        markup.add(back_btn)
        bot.send_message(message.chat.id, deal_info, reply_markup=markup)

def create_deal_start(chat_id, user_id):
    user_states[user_id] = {"step": "deal_description"}
    bot.send_message(
        chat_id,
        "📝 Введите описание товара или услуги для сделки:"
    )

@bot.message_handler(func=lambda message: message.text == '➕ Создать сделку')
def create_deal_start_old(message):
    user_id = message.from_user.id
    user_states[user_id] = {"step": "deal_description"}
    bot.send_message(
        message.chat.id,
        "📝 Введите описание товара или услуги для сделки:"
    )

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get('step') == 'deal_description')
def handle_deal_description(message):
    user_id = message.from_user.id
    description = message.text

    user_states[user_id] = {
        "step": "deal_amount",
        "description": description
    }

    bot.send_message(
        message.chat.id,
        "💵 Введите сумму сделки (только цифры):\n\n"
        "Пример: 15000"
    )

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get('step') == 'deal_amount')
def handle_deal_amount(message):
    user_id = message.from_user.id

    try:
        amount = float(message.text)
        if amount <= 0:
            raise ValueError

        user_states[user_id]['amount'] = amount

        markup = types.InlineKeyboardMarkup(row_width=3)
        btn_rub = types.InlineKeyboardButton("RUB", callback_data="currency_RUB")
        btn_kzt = types.InlineKeyboardButton("KZT", callback_data="currency_KZT")
        btn_uah = types.InlineKeyboardButton("UAH", callback_data="currency_UAH")
        markup.add(btn_rub, btn_kzt, btn_uah)

        bot.send_message(
            message.chat.id,
            "💰 Выберите валюту для сделки:",
            reply_markup=markup
        )

    except:
        bot.reply_to(message, "❌ Некорректная сумма. Введите число больше нуля")

def show_profile(chat_id, user_id):
    user_info = bot.get_chat(user_id)
    first_name = user_info.first_name
    if user_id not in users_balance:
        users_balance[user_id] = 0

    user_deals_as_seller = sum(1 for d in deals_db.values() if d.get('seller_id') == user_id and d.get('status') == 'completed')
    user_deals_as_buyer = sum(1 for d in deals_db.values() if d.get('buyer_id') == user_id and d.get('status') == 'completed')

    info_text = (
        f"👤 ПРОФИЛЬ: {first_name}\n\n"
        f"▫️ Ваш ID: {user_id}\n"
        f"▫️ Баланс: {users_balance[user_id]} RUB\n"
        "➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
        f"📦 Сделок как продавец: {user_deals_as_seller}\n"
        f"🛒 Сделок как покупатель: {user_deals_as_buyer}\n"
        "➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
        "💸 Для вывода средств используйте /withdraw"
    )

    markup = types.InlineKeyboardMarkup()
    back_btn = types.InlineKeyboardButton('🏠 Назад в меню', callback_data='back_to_menu')
    markup.add(back_btn)
    bot.send_message(chat_id, info_text, reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '📊 Мой профиль')
def show_profile_old(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    if user_id not in users_balance:
        users_balance[user_id] = 0

    user_deals_as_seller = sum(1 for d in deals_db.values() if d.get('seller_id') == user_id and d.get('status') == 'completed')
    user_deals_as_buyer = sum(1 for d in deals_db.values() if d.get('buyer_id') == user_id and d.get('status') == 'completed')

    info_text = (
        f"👤 ПРОФИЛЬ: {first_name}\n\n"
        f"▫️ Ваш ID: {user_id}\n"
        f"▫️ Баланс: {users_balance[user_id]} RUB\n"
        "➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
        f"📦 Сделок как продавец: {user_deals_as_seller}\n"
        f"🛒 Сделок как покупатель: {user_deals_as_buyer}\n"
        "➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
        "💸 Для вывода средств используйте /withdraw"
    )

    markup = types.InlineKeyboardMarkup()
    back_btn = types.InlineKeyboardButton('🏠 Назад в меню', callback_data='back_to_menu')
    markup.add(back_btn)
    bot.send_message(message.chat.id, info_text, reply_markup=markup)

def show_active_deals(chat_id, user_id):
    active = []
    for deal_id, deal in deals_db.items():
        if deal['status'] in ['active', 'waiting_delivery']:
            status = "🟢 Активна" if deal['status'] == 'active' else "🟡 Ожидает получения"
            active.append(f"▫️ #{deal_id} - {deal['description']} - {deal['amount']} {deal['currency']} ({status})")

    if not active:
        bot.send_message(chat_id, "ℹ️ Сейчас нет активных сделок", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('🏠 Назад в меню', callback_data='back_to_menu')))
        return

    deals_text = (
            "🆕 АКТИВНЫЕ СДЕЛКИ\n\n" +
            "\n".join(active) +
            "\n➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
            "Для участия в сделке перейдите по ссылке от продавца"
    )

    bot.send_message(chat_id, deals_text, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('🏠 Назад в меню', callback_data='back_to_menu')))

@bot.message_handler(func=lambda message: message.text == '🛒 Активные сделки')
def show_active_deals_old(message):
    active = []
    for deal_id, deal in deals_db.items():
        if deal['status'] in ['active', 'waiting_delivery']:
            status = "🟢 Активна" if deal['status'] == 'active' else "🟡 Ожидает получения"
            active.append(f"▫️ #{deal_id} - {deal['description']} - {deal['amount']} {deal['currency']} ({status})")

    if not active:
        bot.reply_to(message, "ℹ️ Сейчас нет активных сделок", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('🏠 Назад в меню', callback_data='back_to_menu')))
        return

    deals_text = (
            "🆕 АКТИВНЫЕ СДЕЛКИ\n\n" +
            "\n".join(active) +
            "\n➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
            "Для участия в сделке перейдите по ссылке от продавца"
    )

    bot.send_message(message.chat.id, deals_text, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('🏠 Назад в меню', callback_data='back_to_menu')))

@bot.message_handler(commands=['withdraw'])
def handle_withdraw(message):
    user_id = message.from_user.id
    if user_id not in users_balance:
        users_balance[user_id] = 0

    if users_balance[user_id] <= 0:
        bot.reply_to(message, "❌ На вашем балансе недостаточно средств для вывода", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('🏠 Назад в меню', callback_data='back_to_menu')))
        return

    user_states[user_id] = {"step": "withdraw_details", "amount": users_balance[user_id]}
    bot.send_message(
        message.chat.id,
        f"💳 Введите реквизиты для вывода {users_balance[user_id]} RUB:\n\n"
        "Пример: Сбербанк 2200 7000 8000 5500"
    )

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get('step') == 'withdraw_details')
def handle_withdraw_details(message):
    user_id = message.from_user.id
    details = message.text

    amount = user_states[user_id]['amount']
    users_balance[user_id] = 0

    bot.send_message(
        message.chat.id,
        f"✅ ЗАПРОС НА ВЫВОД {amount} RUB ОТПРАВЛЕН!\n\n"
        f"▫️ Реквизиты: {details}\n"
        "➖➖➖➖➖➖➖➖➖➖➖➖➖\n"
        "⚠️ Вывод средств будет выполнен в течение 2 рабочих дней\n\n"
        "Спасибо за использование нашего сервиса!",
        reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('🏠 Назад в меню', callback_data='back_to_menu'))
    )

    del user_states[user_id]

@bot.message_handler(commands=['add_balance'])
def handle_add_balance(message):
    user_id = message.from_user.id

    if not is_admin(user_id):
        bot.reply_to(message, "❌ Эта команда доступна только администраторам", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('🏠 Назад в меню', callback_data='back_to_menu')))
        return

    try:
        parts = message.text.split()
        if len(parts) < 3:
            raise ValueError

        target_user_id = int(parts[1])
        amount = float(parts[2])

        if target_user_id not in users_balance:
            users_balance[target_user_id] = 0

        users_balance[target_user_id] += amount

        bot.reply_to(message, f"✅ Баланс пользователя {target_user_id} пополнен на {amount} RUB", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('🏠 Назад в меню', callback_data='back_to_menu')))

    except:
        bot.reply_to(message, "❌ Неверный формат команды. Используйте: /add_balance <user_id> <amount>", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('🏠 Назад в меню', callback_data='back_to_menu')))

def show_help(chat_id, user_id):
    help_text = (
        "ℹ️ КОМАНДЫ И ИНСТРУКЦИЯ\n\n"
        "▫️ /start - Главное меню\n"
        "▫️ /withdraw - Вывод средств\n"
        "▫️ -----------------------)\n\n"
        "🛒 Как создать сделку:\n"
        "1. Нажмите 'Создать сделку'\n"
        "2. Введите описание товара\n"
        "3. Введите сумму\n"
        "4. Выберите валюту\n"
        "5. Поделитесь ссылкой с покупателем\n\n"
        "💰 Как купить товар:\n"
        "1. Перейдите по ссылке от продавца\n"
        "2. Оплатите товар по реквизитам\n"
        "3. Нажмите 'Я оплатил'\n"
        "4. После получения товара нажмите 'Я получил заказ'\n\n"
        "💸 Вывод средств осуществляется в течение 2 рабочих дней"
    )

    bot.send_message(chat_id, help_text, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('🏠 Назад в меню', callback_data='back_to_menu')))

@bot.message_handler(func=lambda message: message.text == 'ℹ️ Помощь')
def show_help_old(message):
    help_text = (
        "ℹ️ КОМАНДЫ И ИНСТРУКЦИЯ\n\n"
        "▫️ /start - Главное меню\n"
        "▫️ /withdraw - Вывод средств\n"
        "▫️ -----------------------)\n\n"
        "🛒 Как создать сделку:\n"
        "1. Нажмите 'Создать сделку'\n"
        "2. Введите описание товара\n"
        "3. Введите сумму\n"
        "4. Выберите валюту\n"
        "5. Поделитесь ссылкой с покупателем\n\n"
        "💰 Как купить товар:\n"
        "1. Перейдите по ссылке от продавца\n"
        "2. Оплатите товар по реквизитам\n"
        "3. Нажмите 'Я оплатил'\n"
        "4. После получения товара нажмите 'Я получил заказ'\n\n"
        "💸 Вывод средств осуществляется в течение 2 рабочих дней"
    )

    bot.reply_to(message, help_text, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('🏠 Назад в меню', callback_data='back_to_menu')))

@bot.message_handler(func=lambda m: True)
def handle_other(message):
    text = message.text.lower()

    if text in ['привет', 'hi', 'hello']:
        bot.reply_to(message, f"👋 Привет, {message.from_user.first_name}!", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('🏠 Назад в меню', callback_data='back_to_menu')))
    else:
        bot.reply_to(message, "ℹ️ Используйте кнопки меню для навигации", reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton('🏠 Назад в меню', callback_data='back_to_menu')))

if __name__ == "__main__":
    print("⚡ Бот запущен...")
    print(f"Администраторы: {ADMIN_IDS}")
    bot.infinity_polling()
