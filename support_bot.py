import telebot
from telebot import types
from datetime import datetime
import logging

# Настройка логирования для отладки
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен support-бота (замените на реальный токен)
SUPPORT_BOT = telebot.TeleBot("8286157115:AAF7JNApuvIO2L9603NfBu9vgzcIgXL7ZF0")

# Админы (те же, что в основном боте)
ADMIN_IDS = [7339590336]

# База данных (в памяти - для продакшена нужно использовать БД)
support_tickets = {}
user_states = {}

def is_admin(user_id):
    return user_id in ADMIN_IDS

def generate_ticket_id():
    return datetime.now().strftime("%Y%m%d%H%M%S") + str(abs(hash(str(datetime.now()))))[-6:]

def add_ticket(user_id, ticket_type, content):
    try:
        if user_id not in support_tickets:
            support_tickets[user_id] = []
        
        date = datetime.now().strftime("%d %B, %H:%M")
        ticket_id = generate_ticket_id()
        
        support_tickets[user_id].append({
            'type': ticket_type, 
            'content': content, 
            'date': date, 
            'ticket_id': ticket_id
        })
        
        # Получаем информацию о пользователе с обработкой ошибок
        try:
            user_info = SUPPORT_BOT.get_chat(user_id)
            user_name = f"@{user_info.username}" if user_info.username else user_info.first_name or str(user_id)
        except Exception as e:
            logger.error(f"Ошибка получения информации о пользователе {user_id}: {e}")
            user_name = str(user_id)
        
        # Уведомляем админов
        for admin_id in ADMIN_IDS:
            text = (f"🆘 Новое обращение от {user_name} (ID: {user_id}, Ticket: {ticket_id}):\n"
                   f"Тип: {ticket_type}\nСодержание: {content}\nДата: {date}")
            
            markup = types.InlineKeyboardMarkup()
            reply_btn = types.InlineKeyboardButton(
                '📩 Ответить', 
                callback_data=f'reply_ticket_{ticket_id}_{user_id}'
            )
            markup.add(reply_btn)
            
            try:
                SUPPORT_BOT.send_message(admin_id, text, reply_markup=markup)
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения админу {admin_id}: {e}")
    
    except Exception as e:
        logger.error(f"Ошибка в add_ticket: {e}")

@SUPPORT_BOT.message_handler(commands=['start'])
def support_start(message):
    try:
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
        
        text = (f"🆘 <b>Привет, {first_name}!</b>\n\n"
               "Это чат поддержки Trade Guarantor. Выберите действие ниже.")
        
        SUPPORT_BOT.send_message(
            message.chat.id, 
            text, 
            reply_markup=markup, 
            parse_mode='HTML'
        )
        logger.info(f"Меню отправлено пользователю {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка в support_start: {e}")

@SUPPORT_BOT.message_handler(commands=['tickets'])
def show_tickets(message):
    try:
        user_id = message.from_user.id
        
        if user_id not in support_tickets or not support_tickets[user_id]:
            SUPPORT_BOT.reply_to(message, "ℹ️ У вас нет активных обращений.")
            return
        
        text = "📋 <b>Ваша история обращений:</b>\n\n"
        for ticket in support_tickets[user_id][-5:]:
            text += f"• {ticket['date']} ({ticket['type']}): {ticket['content'][:50]}...\n"
        
        SUPPORT_BOT.reply_to(message, text, parse_mode='HTML')
    
    except Exception as e:
        logger.error(f"Ошибка в show_tickets: {e}")

@SUPPORT_BOT.callback_query_handler(func=lambda call: True)
def support_callback(call):
    try:
        user_id = call.from_user.id
        logger.info(f"Callback от {user_id}: {call.data}")
        
        if call.data == 'write_message':
            user_states[user_id] = {'step': 'write_message'}
            SUPPORT_BOT.answer_callback_query(call.id, "📝 Введите ваше сообщение:")
            SUPPORT_BOT.edit_message_text(
                "📝 Ожидаю ваше сообщение...", 
                call.message.chat.id, 
                call.message.message_id
            )
            
        elif call.data == 'instructions':
            text = ("📚 <b>Инструкции по использованию поддержки Trade Guarantor:</b>\n\n"
                   "1. <b>Написать сообщение:</b> Нажмите '📝 Написать сообщение', введите текст и отправьте. Поддержка ответит вам.\n"
                   "3. <b>Проверить историю:</b> Используйте команду /tickets, чтобы увидеть свои обращения.\n"
                   "4. <b>Для админов:</b> Нажмите '👑 Админ', чтобы увидеть список обращений и ответить.\n\n"
                   "ℹ️ Ожидайте ответа в течение 24 часов. Если проблема срочная, укажите это в сообщении!")
            
            markup = types.InlineKeyboardMarkup()
            back_btn = types.InlineKeyboardButton('🔙 Назад', callback_data='back_to_menu')
            markup.add(back_btn)
            
            SUPPORT_BOT.edit_message_text(
                text, 
                call.message.chat.id, 
                call.message.message_id, 
                reply_markup=markup, 
                parse_mode='HTML'
            )
            
        elif call.data == 'settings' and not is_admin(user_id):
            text = "🔧 <b>Настройки:</b>\n\n• Уведомления: Включены.\n• Язык: Русский."
            
            markup = types.InlineKeyboardMarkup()
            back_btn = types.InlineKeyboardMarkup('🔙 Назад', callback_data='back_to_menu')
            markup.add(back_btn)
            
            SUPPORT_BOT.edit_message_text(
                text, 
                call.message.chat.id, 
                call.message.message_id, 
                reply_markup=markup, 
                parse_mode='HTML'
            )
            
        elif call.data == 'admin_panel' and is_admin(user_id):
            all_tickets = []
            for uid, tickets in support_tickets.items():
                for ticket in tickets:
                    try:
                        user_info = SUPPORT_BOT.get_chat(uid)
                        user_name = f"@{user_info.username}" if user_info.username else user_info.first_name or str(uid)
                    except:
                        user_name = str(uid)
                    
                    all_tickets.append((uid, ticket['ticket_id'], ticket['type'], 
                                      ticket['content'], ticket['date'], user_name))
            
            if not all_tickets:
                SUPPORT_BOT.edit_message_text(
                    "ℹ️ Нет активных обращений.", 
                    call.message.chat.id, 
                    call.message.message_id
                )
                return
            
            markup = types.InlineKeyboardMarkup()
            for uid, ticket_id, ticket_type, content, date, user_name in all_tickets[-10:]:
                btn = types.InlineKeyboardButton(
                    f"{user_name} ({ticket_type}, {date[:10]})", 
                    callback_data=f"reply_{ticket_id}_{uid}"
                )
                markup.add(btn)
            
            text = "📋 <b>Список последних обращений:</b>\nВыберите обращение для ответа."
            SUPPORT_BOT.edit_message_text(
                text, 
                call.message.chat.id, 
                call.message.message_id, 
                reply_markup=markup, 
                parse_mode='HTML'
            )
            
        elif call.data == 'back_to_menu':
            markup = types.InlineKeyboardMarkup(row_width=2)
            btn1 = types.InlineKeyboardButton('📝 Написать сообщение', callback_data='write_message')
            btn2 = types.InlineKeyboardButton('📚 Инструкции', callback_data='instructions')
            
            if is_admin(user_id):
                btn3 = types.InlineKeyboardButton('👑 Админ', callback_data='admin_panel')
            else:
                btn3 = types.InlineKeyboardButton('🔧 Настройки', callback_data='settings')
            
            markup.add(btn1, btn2, btn3)
            
            text = (f"🆘 <b>Привет, {call.from_user.first_name}!</b>\n\n"
                   "Это чат поддержки Trade Guarantor. Выберите действие ниже.")
            
            SUPPORT_BOT.edit_message_text(
                text, 
                call.message.chat.id, 
                call.message.message_id, 
                reply_markup=markup, 
                parse_mode='HTML'
            )
            
            if user_id in user_states:
                del user_states[user_id]
                
        elif call.data.startswith('reply_ticket_'):
            if not is_admin(user_id):
                SUPPORT_BOT.answer_callback_query(call.id, "❌ Доступ только для администраторов.")
                return
            
            parts = call.data.split('_')
            if len(parts) >= 4:
                ticket_id = parts[2]
                user_to_reply = parts[3]
                
                user_states[user_id] = {
                    'step': 'admin_reply', 
                    'ticket_id': ticket_id, 
                    'user_id': user_to_reply
                }
                
                SUPPORT_BOT.answer_callback_query(call.id, "📝 Введите ответ:")
                SUPPORT_BOT.edit_message_text(
                    "📝 Ожидаю ваш ответ...", 
                    call.message.chat.id, 
                    call.message.message_id
                )
                
        elif call.data.startswith('reply_'):
            if not is_admin(user_id):
                SUPPORT_BOT.answer_callback_query(call.id, "❌ Доступ только для администраторов.")
                return
            
            parts = call.data.split('_')
            if len(parts) >= 3:
                ticket_id = parts[1]
                user_to_reply = parts[2]
                
                user_states[user_id] = {
                    'step': 'admin_reply', 
                    'ticket_id': ticket_id, 
                    'user_id': user_to_reply
                }
                
                SUPPORT_BOT.answer_callback_query(call.id, "📝 Введите ответ:")
                SUPPORT_BOT.edit_message_text(
                    "📝 Ожидаю ваш ответ...", 
                    call.message.chat.id, 
                    call.message.message_id
                )
    
    except Exception as e:
        logger.error(f"Ошибка в support_callback: {e}")
        SUPPORT_BOT.answer_callback_query(call.id, "❌ Произошла ошибка.")

@SUPPORT_BOT.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get('step') == 'write_message')
def handle_support_message(message):
    try:
        user_id = message.from_user.id
        content = message.text
        
        add_ticket(user_id, 'message', content)
        
        if user_id in user_states:
            del user_states[user_id]
        
        SUPPORT_BOT.reply_to(message, "✅ Сообщение отправлено в поддержку! Ожидайте ответа.")
    
    except Exception as e:
        logger.error(f"Ошибка в handle_support_message: {e}")

@SUPPORT_BOT.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get('step') == 'admin_reply')
def handle_admin_response(message):
    try:
        user_id = message.from_user.id
        
        if not is_admin(user_id):
            SUPPORT_BOT.reply_to(message, "❌ Доступ только для администраторов.")
            return
        
        state = user_states.get(user_id, {})
        response = message.text
        user_to_reply = state.get('user_id')
        
        if not user_to_reply:
            SUPPORT_BOT.reply_to(message, "❌ Ошибка: не найден пользователь для ответа.")
            return
        
        # Отправляем ответ пользователю
        SUPPORT_BOT.send_message(
            user_to_reply, 
            f"📩 <b>Ответ от поддержки:</b>\n{response}", 
            parse_mode='HTML'
        )
        
        # Уведомляем админа
        SUPPORT_BOT.reply_to(message, f"✅ Ответ отправлен пользователю (ID: {user_to_reply}).")
        
        # Очищаем состояние
        if user_id in user_states:
            del user_states[user_id]
    
    except Exception as e:
        logger.error(f"Ошибка в handle_admin_response: {e}")

@SUPPORT_BOT.message_handler(func=lambda m: True)
def handle_other_support(m):
    SUPPORT_BOT.reply_to(m, "ℹ️ Выберите действие из меню. Используйте /start, чтобы увидеть меню.")

if __name__ == "__main__":
    logger.info("🆘 Support-бот запущен...")
    try:
        SUPPORT_BOT.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
