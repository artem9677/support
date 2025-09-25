import telebot
from telebot import types
from datetime import datetime

# Токен support-бота (от @BotFather)
SUPPORT_BOT = telebot.TeleBot("8286157115:AAF7JNApuvIO2L9603NfBu9vgzcIgXL7ZF0")  # Замени!

# Админы (те же, что в основном боте)
ADMIN_IDS = [7339590336]

# База тикетов: user_id -> list of {'type': 'message/call', 'content': str, 'date': str, 'ticket_id': str}
support_tickets = {}
user_states = {}  # Состояния для шагов (например, ввод номера или ответа админа)

def is_admin(user_id):
    return user_id in ADMIN_IDS

def generate_ticket_id():
    return datetime.now().strftime("%Y%m%d%H%M%S") + str(hash(str(datetime.now())))[-6:]

def add_ticket(user_id, ticket_type, content):
    if user_id not in support_tickets:
        support_tickets[user_id] = []
    date = datetime.now().strftime("%d %B, %H:%M")
    ticket_id = generate_ticket_id()
    support_tickets[user_id].append({'type': ticket_type, 'content': content, 'date': date, 'ticket_id': ticket_id})
    
    # Получаем username или имя пользователя
    user_info = SUPPORT_BOT.get_chat(user_id)
    user_name = f"@{user_info.username}" if user_info.username else user_info.first_name or str(user_id)
    
    # Уведомляем админа с кнопкой "Ответить"
    for admin_id in ADMIN_IDS:
        text = f"🆘 Новое обращение от {user_name} (ID: {user_id}, Ticket: {ticket_id}):\nТип: {ticket_type}\nСодержание: {content}\nДата: {date}"
        markup = types.InlineKeyboardMarkup()
        reply_btn = types.InlineKeyboardButton('📩 Ответить', callback_data=f'reply_ticket_{ticket_id}_{user_id}')
        markup.add(reply_btn)
        SUPPORT_BOT.send_message(admin_id, text, reply_markup=markup)

@SUPPORT_BOT.message_handler(commands=['start'])
def support_start(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton('📝 Написать сообщение', callback_data='write_message')
    btn2 = types.InlineKeyboardButton('📚 Инструкции', callback_data='instructions')
    if is_admin(user_id):
        btn3 = types.InlineKeyboardButton('👑 Админ', callback_data='admin_panel')
    else:
        btn3 = types.InlineKeyboardButton('🔧 Настройки', callback_data='settings')
    markup.add(btn1, btn2, btn3)
    text = f"🆘 <b>Привет, {first_name}!</b>\n\nЭто чат поддержки Trade Guarantor. Выберите действие ниже."
    sent_message = SUPPORT_BOT.send_message(message.chat.id, text, reply_markup=markup, parse_mode='HTML')
    print(f"Отправлено меню пользователю {user_id} в чате {message.chat.id} с сообщением ID {sent_message.message_id}")

@SUPPORT_BOT.message_handler(commands=['tickets'])
def show_tickets(message):
    user_id = message.from_user.id
    if user_id not in support_tickets or not support_tickets[user_id]:
        SUPPORT_BOT.reply_to(message, "ℹ️ У вас нет активных обращений.")
        return
    text = "📋 <b>Ваша история обращений:</b>\n\n"
    for ticket in support_tickets[user_id][-5:]:  # Последние 5
        text += f"• {ticket['date']} ({ticket['type']}): {ticket['content'][:50]}...\n"
    SUPPORT_BOT.reply_to(message, text, parse_mode='HTML')

@SUPPORT_BOT.callback_query_handler(func=lambda call: True)
def support_callback(call):
    user_id = call.from_user.id
    print(f"Обработан callback от {user_id} с данными: {call.data}")
    if call.data == 'write_message':
        user_states[user_id] = {'step': 'write_message'}
        SUPPORT_BOT.answer_callback_query(call.id, "📝 Введите ваше сообщение:")
        SUPPORT_BOT.edit_message_text("📝 Ожидаю ваше сообщение...", call.message.chat.id, call.message.message_id)
    elif call.data == 'instructions':
        text = "📚 <b>Инструкции по использованию поддержки Trade Guarantor:</b>\n\n" \
               "1. <b>Написать сообщение:</b> Нажмите '📝 Написать сообщение', введите текст и отправьте. Поддержка ответит вам.\n" \
               "3. <b>Проверить историю:</b> Используйте команду /tickets, чтобы увидеть свои обращения.\n" \
               "4. <b>Для админов:</b> Нажмите '👑 Админ', чтобы увидеть список обращений и ответить.\n\n" \
               "ℹ️ Ожидайте ответа в течение 24 часов. Если проблема срочная, укажите это в сообщении!"
        markup = types.InlineKeyboardMarkup()
        back_btn = types.InlineKeyboardButton('🔙 Назад', callback_data='back_to_menu')
        markup.add(back_btn)
        SUPPORT_BOT.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='HTML')
    elif call.data == 'settings' and not is_admin(user_id):
        text = "🔧 <b>Настройки:</b>\n\n• Уведомления: Включены.\n• Язык: Русский."
        markup = types.InlineKeyboardMarkup()
        back_btn = types.InlineKeyboardButton('🔙 Назад', callback_data='back_to_menu')
        markup.add(back_btn)
        SUPPORT_BOT.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='HTML')
    elif call.data == 'admin_panel' and is_admin(user_id):
        all_tickets = []
        for uid, tickets in support_tickets.items():
            for ticket in tickets:
                user_info = SUPPORT_BOT.get_chat(uid)
                user_name = f"@{user_info.username}" if user_info.username else user_info.first_name or str(uid)
                all_tickets.append((uid, ticket['ticket_id'], ticket['type'], ticket['content'], ticket['date'], user_name))

        if not all_tickets:
            SUPPORT_BOT.edit_message_text("ℹ️ Нет активных обращений.", call.message.chat.id, call.message.message_id)
            return

        markup = types.InlineKeyboardMarkup()
        for uid, ticket_id, ticket_type, content, date, user_name in all_tickets[-10:]:  # Последние 10 тикетов
            btn = types.InlineKeyboardButton(f"{user_name} ({ticket_type}, {date[:5]})", callback_data=f"reply_{ticket_id}_{uid}")
            markup.add(btn)

        text = "📋 <b>Список последних обращений:</b>\nВыберите обращение для ответа."
        SUPPORT_BOT.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='HTML')
    elif call.data == 'back_to_menu':
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn1 = types.InlineKeyboardButton('📝 Написать сообщение', callback_data='write_message')
        btn2 = types.InlineKeyboardButton('📚 Инструкции', callback_data='instructions')
        if is_admin(user_id):
            btn3 = types.InlineKeyboardButton('👑 Админ', callback_data='admin_panel')
        else:
            btn3 = types.InlineKeyboardButton('🔧 Настройки', callback_data='settings')
        markup.add(btn1, btn2, btn3)
        text = f"🆘 <b>Привет, {call.from_user.first_name}!</b>\n\nЭто чат поддержки Trade Guarantor. Выберите действие ниже."
        SUPPORT_BOT.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode='HTML')
        if user_id in user_states:
            del user_states[user_id]  # Очищаем состояние при возврате
    elif call.data.startswith('reply_ticket_'):
        if not is_admin(user_id):
            SUPPORT_BOT.answer_callback_query(call.id, "❌ Доступ только для администраторов.")
            return
        _, ticket_id, user_to_reply = call.data.split('_')[1:]
        user_states[user_id] = {'step': 'admin_reply', 'ticket_id': ticket_id, 'user_id': user_to_reply}
        SUPPORT_BOT.answer_callback_query(call.id, "📝 Введите ответ:")
        SUPPORT_BOT.edit_message_text("📝 Ожидаю ваш ответ...", call.message.chat.id, call.message.message_id)
    elif call.data.startswith('reply_'):
        if not is_admin(user_id):
            SUPPORT_BOT.answer_callback_query(call.id, "❌ Доступ только для администраторов.")
            return
        _, ticket_id, user_to_reply = call.data.split('_')
        user_states[user_id] = {'step': 'admin_reply', 'ticket_id': ticket_id, 'user_id': user_to_reply}
        SUPPORT_BOT.answer_callback_query(call.id, "📝 Введите ответ:")
        SUPPORT_BOT.edit_message_text("📝 Ожидаю ваш ответ...", call.message.chat.id, call.message.message_id)

@SUPPORT_BOT.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get('step') == 'write_message')
def handle_support_message(message):
    user_id = message.from_user.id
    content = message.text
    add_ticket(user_id, 'message', content)
    del user_states[user_id]
    SUPPORT_BOT.reply_to(message, "✅ Сообщение отправлено в поддержку! Ожидайте ответа.")

@SUPPORT_BOT.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get('step') == 'admin_reply')
def handle_admin_response(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        SUPPORT_BOT.reply_to(message, "❌ Доступ только для администраторов.")
        return

    state = user_states[user_id]
    response = message.text
    user_to_reply = state['user_id']

    # Отправляем ответ пользователю
    SUPPORT_BOT.send_message(user_to_reply, f"📩 <b>Ответ от поддержки:</b>\n{response}", parse_mode='HTML')

    # Уведомляем админа об отправке
    SUPPORT_BOT.reply_to(message, f"✅ Ответ отправлен пользователю (ID: {user_to_reply}).")

    # Очищаем состояние
    del user_states[user_id]

# Обработчик неизвестных сообщений
@SUPPORT_BOT.message_handler(func=lambda m: True)
def handle_other_support(m):
    SUPPORT_BOT.reply_to(m, "ℹ️ Выберите действие из меню. Используйте /start, чтобы увидеть меню.")

if __name__ == "__main__":
    print("🆘 Support-бот запущен...")
    SUPPORT_BOT.infinity_polling()
