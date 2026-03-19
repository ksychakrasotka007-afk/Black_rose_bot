import telebot
from telebot import types
import schedule
import time
import threading
import json
import os
from datetime import datetime

# ========== ПРЯМЫЕ ЗНАЧЕНИЯ ==========
TOKEN = "8679951155:AAEmiMjS3awuU_n30Dx0TSxN5_0Dub0s801M"
CHAT_ID = "-1002227029127"
ADMIN_ID = 5136954277
BOT_USERNAME = "BlackRoseCW_bot"
# ======================================

bot = telebot.TeleBot(TOKEN)
NICK_FILE = "game_nicks.json"
VOTE_FILE = "votes.json"

def load_nicks():
    if os.path.exists(NICK_FILE):
        with open(NICK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_nicks(nicks):
    with open(NICK_FILE, "w", encoding="utf-8") as f:
        json.dump(nicks, f, ensure_ascii=False, indent=2)

def load_votes():
    if os.path.exists(VOTE_FILE):
        with open(VOTE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_votes(votes):
    with open(VOTE_FILE, "w", encoding="utf-8") as f:
        json.dump(votes, f, ensure_ascii=False, indent=2)

game_nicks = load_nicks()
votes = load_votes()

def is_admin(user_id):
    return user_id == ADMIN_ID

def nick_button():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn = types.KeyboardButton("➕ Добавить свой ник")
    markup.add(btn)
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id,
        "👋 Привет! Я бот клана **Black Rose**.\n\n"
        "🎮 Нажми кнопку **«Добавить свой ник»** и напиши свой игровой ник.",
        parse_mode="Markdown", reply_markup=nick_button())

@bot.message_handler(commands=['nick'])
def save_nick_command(message):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Напиши так: /nick ТвойИгровойНик")
            return
        game_nick = parts[1]
        user_id = str(message.from_user.id)
        game_nicks[user_id] = {
            "game_nick": game_nick,
            "tg_username": message.from_user.username,
            "first_name": message.from_user.first_name
        }
        save_nicks(game_nicks)
        bot.reply_to(message, f"✅ Игровой ник **{game_nick}** сохранён!", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, "❌ Ошибка. Попробуй ещё раз.")

@bot.message_handler(func=lambda message: message.text == "➕ Добавить свой ник")
def ask_nick(message):
    msg = bot.send_message(message.chat.id, "📝 Напиши свой игровой ник (например: xX_Warrior_Xx):")
    bot.register_next_step_handler(msg, save_nick)

def save_nick(message):
    nick = message.text.strip()
    if len(nick) < 2 or len(nick) > 30:
        bot.send_message(message.chat.id, "❌ Слишком коротко или длинно. Попробуй ещё раз.", reply_markup=nick_button())
        return
    user_id = str(message.from_user.id)
    game_nicks[user_id] = {
        "game_nick": nick,
        "tg_username": message.from_user.username,
        "first_name": message.from_user.first_name
    }
    save_nicks(game_nicks)
    bot.send_message(message.chat.id, f"✅ Ник **{nick}** сохранён!", parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(commands=['list'])
def list_nicks(message):
    if not game_nicks:
        bot.send_message(message.chat.id, "📭 База пуста.")
        return
    text = "📋 **Список ников:**\n"
    items = list(game_nicks.items())
    for idx, (uid, data) in enumerate(items, 1):
        text += f"{idx}. 🎮 {data['game_nick']}"
        if data['tg_username']:
            text += f" (@{data['tg_username']})"
        text += "\n"
    if is_admin(message.from_user.id):
        text += "\n🔧 Админ: /del НОМЕР — удалить игрока"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(commands=['del'])
def delete_nick(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Только админ может удалять игроков.")
        return
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Напиши так: /del НОМЕР")
            return
        num = int(parts[1])
        items = list(game_nicks.items())
        if num < 1 or num > len(items):
            bot.reply_to(message, f"❌ Номер должен быть от 1 до {len(items)}")
            return
        user_id, data = items[num-1]
        game_nick = data.get("game_nick", "?")
        del game_nicks[user_id]
        save_nicks(game_nicks)
        bot.reply_to(message, f"✅ Игрок **{game_nick}** удалён из базы.", parse_mode="Markdown")
        list_nicks(message)
    except ValueError:
        bot.reply_to(message, "❌ Номер должен быть числом")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

@bot.message_handler(commands=['whoami'])
def whoami(message):
    bot.reply_to(message, f"Твой ID: {message.from_user.id}")

@bot.message_handler(content_types=['new_chat_members'])
def welcome(message):
    for user in message.new_chat_members:
        if user.id == bot.get_me().id:
            continue
        bot.send_message(message.chat.id, f"👋 {user.first_name}, напиши боту в личку @{BOT_USERNAME} и нажми «Добавить свой ник»")
        try:
            bot.send_message(user.id, "👋 Сохрани свой игровой ник:", reply_markup=nick_button())
        except:
            pass

def start_voting():
    global votes
    votes = {}
    save_votes(votes)
    bot.send_message(CHAT_ID, f"📢 **Голосование на КВ началось!**\n\nКаждому игроку пришло сообщение в личку.\nИтоги будут завтра в 07:00.", parse_mode="Markdown")
    sent = 0
    blocked = 0
    for user_id, data in game_nicks.items():
        try:
            markup = types.InlineKeyboardMarkup()
            btn_yes = types.InlineKeyboardButton("✅ Да, иду", callback_data=f"vote_yes_{user_id}")
            btn_no = types.InlineKeyboardButton("❌ Нет, не иду", callback_data=f"vote_no_{user_id}")
            markup.add(btn_yes, btn_no)
            bot.send_message(user_id, f"⚔️ **КВ завтра. Ты идёшь?**\n\nТвой ник: {data['game_nick']}", parse_mode="Markdown", reply_markup=markup)
            sent += 1
        except:
            blocked += 1
    bot.send_message(ADMIN_ID, f"📊 Рассылка завершена:\n✅ Отправлено: {sent}\n❌ Заблокировали бота: {blocked}")
    threading.Timer(12 * 60 * 60, finish_voting).start()

def finish_voting():
    yes_list = []
    no_list = []
    not_voted = []
    for user_id, data in game_nicks.items():
        game_nick = data['game_nick']
        if user_id in votes:
            if votes[user_id] == "yes":
                yes_list.append(f"✅ {game_nick}")
            else:
                no_list.append(f"❌ {game_nick}")
        else:
            not_voted.append(f"🤔 {game_nick}")
    text = "**📊 Итоги голосования на КВ:**\n\n"
    if yes_list:
        text += f"✅ **Идут ({len(yes_list)}):**\n" + "\n".join(yes_list) + "\n\n"
    if no_list:
        text += f"❌ **Не идут ({len(no_list)}):**\n" + "\n".join(no_list) + "\n\n"
    if not_voted:
        text += f"🤔 **Не проголосовали ({len(not_voted)}):**\n" + "\n".join(not_voted[:10])
        if len(not_voted) > 10:
            text += f"\n... и ещё {len(not_voted) - 10}"
    bot.send_message(CHAT_ID, text, parse_mode="Markdown")
    votes.clear()
    save_votes(votes)

@bot.callback_query_handler(func=lambda call: call.data.startswith('vote_'))
def handle_vote(call):
    user_id = str(call.from_user.id)
    data = call.data.split('_')
    vote_type = data[1]
    target_user_id = data[2]
    if user_id != target_user_id:
        bot.answer_callback_query(call.id, "❌ Нельзя голосовать за другого")
        return
    if user_id not in game_nicks:
        bot.answer_callback_query(call.id, "❌ Ты не сохранил ник. Напиши /nick")
        return
    if user_id in votes:
        bot.answer_callback_query(call.id, "❌ Ты уже проголосовал")
        return
    votes[user_id] = vote_type
    save_votes(votes)
    game_nick = game_nicks[user_id]['game_nick']
    if vote_type == "yes":
        bot.answer_callback_query(call.id, f"✅ Отмечено: ты идёшь ({game_nick})")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        bot.send_message(call.message.chat.id, f"✅ Твой голос учтён: ты идёшь на КВ.")
    else:
        bot.answer_callback_query(call.id, f"❌ Отмечено: ты не идёшь")
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        bot.send_message(call.message.chat.id, f"❌ Твой голос учтён: ты не идёшь на КВ.")

@bot.message_handler(commands=['startvote'])
def start_vote_command(message):
    if is_admin(message.from_user.id):
        start_voting()
        bot.reply_to(message, "✅ Голосование запущено!")
    else:
        bot.reply_to(message, "❌ Только админ может запустить голосование.")

@bot.message_handler(commands=['results'])
def results_command(message):
    if not votes:
        bot.send_message(message.chat.id, "📭 Голосование ещё не проводилось.")
        return
    yes_list = []
    no_list = []
    not_voted = []
    for user_id, data in game_nicks.items():
        game_nick = data['game_nick']
        if user_id in votes:
            if votes[user_id] == "yes":
                yes_list.append(f"✅ {game_nick}")
            else:
                no_list.append(f"❌ {game_nick}")
        else:
            not_voted.append(f"🤔 {game_nick}")
    text = "**📊 Текущие результаты:**\n\n"
    if yes_list:
        text += f"✅ Идут ({len(yes_list)}):\n" + "\n".join(yes_list) + "\n\n"
    if no_list:
        text += f"❌ Не идут ({len(no_list)}):\n" + "\n".join(no_list) + "\n\n"
    if not_voted:
        text += f"🤔 Ещё не голосовали ({len(not_voted)})"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

def daily_vote():
    now = datetime.now()
    if now.weekday() in [2, 3, 4, 5, 6]:
        start_voting()

schedule.every().day.at("19:00").do(daily_vote)

def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    print("🚀 Бот для клановых войн запущен...")
    print(f"Сохранено игровых ников: {len(game_nicks)}")
    print(f"Админ ID: {ADMIN_ID}")
    print(f"Бот: @{BOT_USERNAME}")
    threading.Thread(target=run_schedule, daemon=True).start()
    bot.infinity_polling()
