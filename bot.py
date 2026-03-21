import telebot
from telebot import types
import json
import os
import requests

TOKEN = "8679951155:AAHzQgjWPJxedavRIUdc_EbRm3176jYu_9k"
CHAT_ID = "-1002227029127"
ADMIN_ID = 5136954277
BOT_USERNAME = "BlackRoseCW_bot"

bot = telebot.TeleBot(TOKEN)

DATA_DIR = "/app/data"
os.makedirs(DATA_DIR, exist_ok=True)
NICK_FILE = os.path.join(DATA_DIR, "game_nicks.json")

def load_json():
    if os.path.exists(NICK_FILE):
        with open(NICK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(data):
    with open(NICK_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

game_nicks = load_json()

def is_admin(user_id):
    return user_id == ADMIN_ID

def nick_button():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Добавить свой ник")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id,
        "👋 Привет! Я бот клана Black Rose.\n\n"
        "Нажми кнопку, чтобы добавить свой игровой ник.",
        reply_markup=nick_button())

@bot.message_handler(func=lambda m: m.text == "➕ Добавить свой ник")
def ask_nick(message):
    msg = bot.send_message(message.chat.id, "📝 Напиши свой игровой ник (например: xX_Warrior_Xx):")
    bot.register_next_step_handler(msg, save_nick)

def save_nick(message):
    nick = message.text.strip()
    if len(nick) < 2 or len(nick) > 30:
        bot.send_message(message.chat.id, "❌ Слишком коротко или длинно. Попробуй ещё.", reply_markup=nick_button())
        return
    uid = str(message.from_user.id)
    game_nicks[uid] = {
        "game_nick": nick,
        "tg_username": message.from_user.username,
        "first_name": message.from_user.first_name
    }
    save_json(game_nicks)
    bot.send_message(message.chat.id, f"✅ Ник **{nick}** сохранён!", parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(commands=['list'])
def list_command(message):
    if not game_nicks:
        bot.send_message(message.chat.id, "📭 База пуста.")
        return
    text = "📋 **Список ников:**\n"
    for idx, (uid, data) in enumerate(game_nicks.items(), 1):
        text += f"{idx}. 🎮 {data['game_nick']}"
        if data.get('tg_username'):
            text += f" (@{data['tg_username']})"
        text += "\n"
    if is_admin(message.from_user.id):
        text += "\n🔧 Админ: /del НОМЕР — удалить игрока"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(commands=['del'])
def delete_command(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Только админ.")
        return
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ /del НОМЕР")
            return
        num = int(parts[1])
        items = list(game_nicks.items())
        if num < 1 or num > len(items):
            bot.reply_to(message, f"❌ Номер от 1 до {len(items)}")
            return
        uid, data = items[num-1]
        nick = data['game_nick']
        del game_nicks[uid]
        save_json(game_nicks)
        bot.reply_to(message, f"✅ Игрок {nick} удалён.")
        list_command(message)
    except:
        bot.reply_to(message, "❌ Ошибка")

if __name__ == "__main__":
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook")
        print("✅ Webhook deleted")
    except:
        pass

    print("🚀 Бот запущен")
    print(f"Сохранено ников: {len(game_nicks)}")
    print(f"Админ ID: {ADMIN_ID}")

    bot.infinity_polling()
