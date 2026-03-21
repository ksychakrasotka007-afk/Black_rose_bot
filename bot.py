import telebot
from telebot import types
import schedule
import time
import threading
import json
import os
import requests
from datetime import datetime

# ========== НАСТРОЙКИ ==========
TOKEN = "8679951155:AAHzQgjWPJxedavRIUdc_EbRm3176jYu_9k"
CHAT_ID = "-1002227029127"
ADMIN_ID = 5136954277
BOT_USERNAME = "BlackRoseCW_bot"
# ================================

bot = telebot.TeleBot(TOKEN)

# ========== ПОСТОЯННОЕ ХРАНИЛИЩЕ ==========
DATA_DIR = "/app/data"
os.makedirs(DATA_DIR, exist_ok=True)

NICK_FILE = os.path.join(DATA_DIR, "game_nicks.json")
VOTE_FILE = os.path.join(DATA_DIR, "votes.json")

def load_json(file):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

game_nicks = load_json(NICK_FILE)
votes = load_json(VOTE_FILE)

def is_admin(user_id):
    return user_id == ADMIN_ID

def nick_button():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Добавить свой ник")
    return markup

def group_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📖 Команды")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id,
        "👋 Привет! Я бот клана Black Rose.\n\n"
        "Нажми кнопку, чтобы добавить свой игровой ник.",
        reply_markup=nick_button())

@bot.message_handler(commands=['menu'])
def menu_command(message):
    if message.chat.type in ['group', 'supergroup']:
        bot.send_message(message.chat.id, "📋 **Меню клана:**", parse_mode="Markdown", reply_markup=group_menu())

@bot.message_handler(func=lambda m: m.text == "📖 Команды")
def commands_list(message):
    text = (
        "📖 **Команды бота:**\n\n"
        "👥 **Для всех:**\n"
        "/start — запустить бота\n"
        "/list — список ников\n"
        "/whoami — твой ID\n"
        "/results — текущие голоса\n\n"
        "👑 **Админ:**\n"
        "/del [номер] — удалить игрока\n"
        "/startvote — запустить опрос"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "➕ Добавить свой ник")
def ask_nick_in_group(message):
    msg = bot.send_message(message.chat.id, "📝 Напиши свой игровой ник (например: xX_Warrior_Xx):")
    bot.register_next_step_handler(msg, save_nick_from_group)

def save_nick_from_group(message):
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
    save_json(NICK_FILE, game_nicks)
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
        save_json(NICK_FILE, game_nicks)
        bot.reply_to(message, f"✅ Игрок {nick} удалён.")
        list_command(message)
    except:
        bot.reply_to(message, "❌ Ошибка")

@bot.message_handler(commands=['whoami'])
def whoami(message):
    bot.reply_to(message, f"Твой ID: {message.from_user.id}")

@bot.message_handler(commands=['results'])
def results_command(message):
    if not votes:
        bot.send_message(message.chat.id, "📭 Голосование не проводилось.")
        return
    yes = [game_nicks.get(uid, {}).get("game_nick", "?") for uid, v in votes.items() if v == "yes"]
    no = [game_nicks.get(uid, {}).get("game_nick", "?") for uid, v in votes.items() if v == "no"]
    not_voted = [game_nicks[uid]["game_nick"] for uid in game_nicks if uid not in votes]
    text = "**📊 Текущие результаты:**\n\n"
    if yes:
        text += f"✅ Участвуют ({len(yes)}):\n" + "\n".join(f"🎮 {n}" for n in yes) + "\n\n"
    if no:
        text += f"❌ Не участвуют ({len(no)}):\n" + "\n".join(f"🎮 {n}" for n in no) + "\n\n"
    if not_voted:
        text += f"🤔 Ещё не голосовали ({len(not_voted)})"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

def start_voting():
    global votes
    votes = {}
    save_json(VOTE_FILE, votes)
    bot.send_message(CHAT_ID, "📢 **Голосование началось!** Игроки, проверьте личные сообщения.", parse_mode="Markdown")
    for uid, data in game_nicks.items():
        try:
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("✅ Участвую", callback_data=f"vote_yes_{uid}"),
                types.InlineKeyboardButton("❌ Не участвую", callback_data=f"vote_no_{uid}")
            )
            bot.send_message(uid, f"⚔️ **КВ завтра. Ты участвуешь?**\n\nТвой ник: {data['game_nick']}", parse_mode="Markdown", reply_markup=markup)
        except:
            pass
    threading.Timer(12 * 60 * 60, end_voting).start()

def end_voting():
    if not votes:
        bot.send_message(CHAT_ID, "📭 Голосование завершено. Никто не голосовал.")
        return
    yes = []
    no = []
    for uid, v in votes.items():
        nick = game_nicks.get(uid, {}).get("game_nick", "?")
        if v == "yes":
            yes.append(f"✅ {nick}")
        else:
            no.append(f"❌ {nick}")
    text = "**📊 Итоги голосования:**\n\n"
    if yes:
        text += "✅ **Участвуют:**\n" + "\n".join(yes) + "\n\n"
    if no:
        text += "❌ **Не участвуют:**\n" + "\n".join(no)
    bot.send_message(CHAT_ID, text, parse_mode="Markdown")
    votes.clear()
    save_json(VOTE_FILE, votes)

@bot.callback_query_handler(func=lambda call: call.data.startswith('vote_'))
def handle_vote(call):
    uid = str(call.from_user.id)
    _, vote_type, target = call.data.split('_')
    if uid != target:
        bot.answer_callback_query(call.id, "❌ Нельзя голосовать за другого")
        return
    if uid not in game_nicks:
        bot.answer_callback_query(call.id, "❌ Сначала добавь ник через кнопку в группе")
        return
    if uid in votes:
        bot.answer_callback_query(call.id, "❌ Ты уже голосовал")
        return
    votes[uid] = vote_type
    save_json(VOTE_FILE, votes)
    if vote_type == "yes":
        bot.answer_callback_query(call.id, "✅ Голос принят: ты участвуешь!")
    else:
        bot.answer_callback_query(call.id, "❌ Голос принят: ты не участвуешь")
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

@bot.message_handler(commands=['startvote'])
def startvote_command(message):
    if is_admin(message.from_user.id):
        start_voting()
        bot.reply_to(message, "✅ Голосование запущено!")
    else:
        bot.reply_to(message, "❌ Только админ")

@bot.message_handler(commands=['endvote'])
def endvote_command(message):
    if is_admin(message.from_user.id):
        end_voting()
        bot.reply_to(message, "✅ Голосование завершено досрочно.")
    else:
        bot.reply_to(message, "❌ Только админ")

@bot.message_handler(content_types=['new_chat_members'])
def welcome(message):
    for user in message.new_chat_members:
        if user.id == bot.get_me().id:
            continue
        bot.send_message(message.chat.id, f"👋 Добро пожаловать, {user.first_name}! Чтобы участвовать в опросах, нажми кнопку «➕ Добавить свой ник».")

if __name__ == "__main__":
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook")
        print("✅ Webhook deleted")
    except Exception as e:
        print(f"❌ Webhook delete error: {e}")

    print("🚀 Бот запущен")
    print(f"Сохранено ников: {len(game_nicks)}")
    print(f"Админ ID: {ADMIN_ID}")
    print(f"Бот: @{BOT_USERNAME}")

    bot.infinity_polling()
