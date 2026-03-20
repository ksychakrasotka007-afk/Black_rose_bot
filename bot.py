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
CLAN_TAG = "#QGQQV82P"  # замени на тег своего клана
API_KEY = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAyTFLYi03ZmExLTJjNzQzM2MzY2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwILCJhdWQiOiJzdXB1cmNlbGw6Z2FtZWFaSiIsImpoaS16IjAxZDg10DI5LTQ30TAtNDYxOS1hNGZhLWUwOWYwZTd1NmIyMyIsImlhdCI6MTc3NDAwMTI4Oswic3ViIjoiZGv2ZwxcGVyL2M3N2U5NmZkLTZ1OTctMWu5NC1kMmJmLWU0MGISYju4MDYONiIsInNjb3BlcyI6WyJyb31hbGuixSwibGltaXRzIjpbeyJoAwVyIjoiZGv2ZwxcGVyL3NpbHZIciIsInR5cGUiOiJoAHJvdHRsaW5nIn0seyJjaWRycyI6WyIWlJjAuMC4WI10sInR5cGUiOiJjbGl1bnQifV19.YxHptQHFj0GKi0yFao3PTYzqjojUzxstgMRE1_qh1iR_CdQWcSSu_ij2qoxFMOLMrPLhwaJZPopbr1IyhNFtg"
# ================================

bot = telebot.TeleBot(TOKEN)

# ========== ПОСТОЯННОЕ ХРАНИЛИЩЕ ==========
DATA_DIR = "/app/data"
os.makedirs(DATA_DIR, exist_ok=True)

NICK_FILE = os.path.join(DATA_DIR, "game_nicks.json")
VOTE_FILE = os.path.join(DATA_DIR, "votes.json")
PLAYER_TAGS_FILE = os.path.join(DATA_DIR, "player_tags.json")
CLAN_CACHE_FILE = os.path.join(DATA_DIR, "clan_cache.json")
# ==========================================

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
player_tags = load_json(PLAYER_TAGS_FILE)
clan_cache = load_json(CLAN_CACHE_FILE)

def is_admin(user_id):
    return user_id == ADMIN_ID

def nick_button():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Добавить свой ник")
    return markup

def group_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📖 Команды", "🏛 Информация о клане", "🎮 Мой ник и тег")
    return markup

# ========== API ЗАПРОСЫ ==========
def api_request(endpoint):
    url = f"https://api.clashroyale.com/v1/{endpoint}"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"API error {resp.status_code}: {resp.text}")
            return None
    except Exception as e:
        print(f"API exception: {e}")
        return None

def get_player_data(tag):
    tag_clean = tag.replace("#", "").upper()
    data = api_request(f"players/%23{tag_clean}")
    if data:
        return {
            "name": data.get("name", "?"),
            "tag": data.get("tag", tag),
            "trophies": data.get("trophies", 0),
            "kingLevel": data.get("kingLevel", 0),
            "wins": data.get("wins", 0),
            "losses": data.get("losses", 0),
            "highestTrophies": data.get("bestTrophies", 0),
            "clan": data.get("clan", {}).get("name", "Нет клана"),
            "clan_tag": data.get("clan", {}).get("tag", ""),
            "lastSeen": data.get("lastSeen", "неизвестно"),
        }
    return None

def get_clan_data(tag):
    tag_clean = tag.replace("#", "").upper()
    data = api_request(f"clans/%23{tag_clean}")
    if data:
        members = data.get("memberList", [])
        members_sorted = sorted(members, key=lambda x: x.get("trophies", 0), reverse=True)[:10]
        return {
            "name": data.get("name", "?"),
            "tag": data.get("tag", tag),
            "type": data.get("type", "?"),
            "members": data.get("members", 0),
            "requiredTrophies": data.get("requiredTrophies", 0),
            "location": data.get("location", {}).get("name", "Международный"),
            "clanScore": data.get("clanScore", 0),
            "clanWarTrophies": data.get("clanWarTrophies", 0),
            "description": data.get("description", "Нет описания"),
            "top_members": [{"name": m["name"], "trophies": m["trophies"]} for m in members_sorted]
        }
    return None

def update_clan_cache():
    data = get_clan_data(CLAN_TAG)
    if data:
        clan_cache["data"] = data
        clan_cache["last_update"] = datetime.now().isoformat()
        save_json(CLAN_CACHE_FILE, clan_cache)
        print("Клан кэш обновлён")

# ========== КОМАНДЫ ==========
@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.type in ['group', 'supergroup']:
        return
    bot.send_message(message.chat.id,
        "👋 Привет! Я бот клана Black Rose.\n\n"
        "Нажми кнопку «Добавить свой ник» и напиши свой игровой ник.",
        reply_markup=nick_button())

@bot.message_handler(func=lambda m: m.text == "➕ Добавить свой ник")
def ask_nick(message):
    if message.chat.type in ['group', 'supergroup']:
        return
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
    save_json(NICK_FILE, game_nicks)
    bot.send_message(message.chat.id, f"✅ Ник **{nick}** сохранён!", parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(commands=['nick'])
def save_nick_command(message):
    if message.chat.type in ['group', 'supergroup']:
        return
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
        save_json(NICK_FILE, game_nicks)
        bot.reply_to(message, f"✅ Игровой ник **{game_nick}** сохранён!", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, "❌ Ошибка. Попробуй ещё раз.")

@bot.message_handler(commands=['tag'])
def save_tag_command(message):
    if message.chat.type in ['group', 'supergroup']:
        return
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Напиши так: /tag #твой_тег")
            return
        tag = parts[1].strip()
        if not tag.startswith("#"):
            tag = "#" + tag
        # Проверяем тег через API
        data = get_player_data(tag)
        if not data:
            bot.reply_to(message, "❌ Тег не найден в Clash Royale. Проверь и попробуй ещё раз.")
            return
        user_id = str(message.from_user.id)
        player_tags[user_id] = tag
        save_json(PLAYER_TAGS_FILE, player_tags)
        bot.reply_to(message, f"✅ Тег **{tag}** сохранён для игрока **{data['name']}**!")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

@bot.message_handler(commands=['list'])
def list_nicks(message):
    if not game_nicks:
        bot.send_message(message.chat.id, "📭 База пуста.")
        return
    text = "📋 **Список ников:**\n"
    items = list(game_nicks.items())
    for idx, (uid, data) in enumerate(items, 1):
        text += f"{idx}. 🎮 {data['game_nick']}"
        if data.get('tg_username'):
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
        if user_id in player_tags:
            del player_tags[user_id]
        save_json(NICK_FILE, game_nicks)
        save_json(PLAYER_TAGS_FILE, player_tags)
        bot.reply_to(message, f"✅ Игрок **{game_nick}** удалён из базы.", parse_mode="Markdown")
        list_nicks(message)
    except ValueError:
        bot.reply_to(message, "❌ Номер должен быть числом")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

@bot.message_handler(commands=['whoami'])
def whoami(message):
    bot.reply_to(message, f"Твой ID: {message.from_user.id}")

@bot.message_handler(commands=['results'])
def results_command(message):
    if not votes:
        bot.send_message(message.chat.id, "📭 Голосование ещё не проводилось.")
        return
    yes = [game_nicks.get(uid, {}).get("game_nick", "?") for uid, v in votes.items() if v == "yes"]
    no = [game_nicks.get(uid, {}).get("game_nick", "?") for uid, v in votes.items() if v == "no"]
    not_voted = [game_nicks[uid]["game_nick"] for uid in game_nicks if uid not in votes]
    text = "**📊 Текущие результаты:**\n\n"
    if yes:
        text += f"✅ Идут ({len(yes)}):\n" + "\n".join(f"🎮 {n}" for n in yes) + "\n\n"
    if no:
        text += f"❌ Не идут ({len(no)}):\n" + "\n".join(f"🎮 {n}" for n in no) + "\n\n"
    if not_voted:
        text += f"🤔 Ещё не голосовали ({len(not_voted)})"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ========== МЕНЮ В ГРУППЕ ==========
@bot.message_handler(commands=['menu'])
def show_menu(message):
    if message.chat.type in ['group', 'supergroup']:
        bot.send_message(message.chat.id, "📋 **Меню клана:**", parse_mode="Markdown", reply_markup=group_menu())

@bot.message_handler(func=lambda m: m.text == "📖 Команды")
def send_commands_list(message):
    text = (
        "📖 **Доступные команды бота:**\n\n"
        "👥 **Для всех игроков:**\n"
        "/start — запустить бота (только в личке)\n"
        "/nick [игровой ник] — сохранить игровой ник\n"
        "/tag [тег] — сохранить тег Clash Royale\n"
        "/list — показать список всех сохранённых ников\n"
        "/whoami — узнать свой Telegram ID\n"
        "/results — показать текущие результаты голосования на КВ\n\n"
        "👑 **Для админа:**\n"
        "/del [номер] — удалить игрока из базы (номер из /list)\n"
        "/startvote — запустить голосование вручную\n"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🏛 Информация о клане")
def clan_info(message):
    data = get_clan_data(CLAN_TAG)
    if not data and clan_cache.get("data"):
        data = clan_cache["data"]
        cache_time = clan_cache.get("last_update", "неизвестно")
        cache_note = f"\n⚠️ Данные из кэша от {cache_time} (API временно недоступен)"
    else:
        cache_note = ""
    
    if not data:
        bot.send_message(message.chat.id, "❌ Не удалось получить данные клана. Попробуй позже.")
        return
    
    text = (
        f"🏛 **Клан {data['name']}:**\n\n"
        f"🏷 Тег: {data['tag']}\n"
        f"👥 Участников: {data['members']}/50\n"
        f"🏆 Требуемые трофеи: {data['requiredTrophies']}\n"
        f"🏴 Регион: {data['location']}\n"
        f"💪 Очки клана: {data['clanScore']}\n"
        f"⚔️ Военные трофеи: {data['clanWarTrophies']}\n"
        f"📋 Описание: {data['description'][:200]}\n\n"
        "📊 **Топ-10 игроков:**\n"
    )
    for i, m in enumerate(data.get('top_members', [])[:10], 1):
        text += f"{i}. {m['name']} ({m['trophies']} 🏆)\n"
    text += cache_note
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🎮 Мой ник и тег")
def my_info(message):
    user_id = str(message.from_user.id)
    nick = game_nicks.get(user_id, {}).get("game_nick", "не сохранён")
    tag = player_tags.get(user_id, "не сохранён")
    
    text = f"🎮 **Твой игровой ник:** {nick}\n"
    text += f"🏷 **Твой тег:** {tag}"
    
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

# ========== ПРИВЕТСТВИЕ НОВИЧКОВ ==========
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

# ========== ОПРОСЫ ПО РАСПИСАНИЮ ==========
def start_voting():
    global votes
    votes = {}
    save_json(VOTE_FILE, votes)
    bot.send_message(CHAT_ID, f"📢 **Голосование на КВ началось!**\n\nКаждому игроку пришло сообщение в личку.\nИтоги будут завтра в 07:00.", parse_mode="Markdown")
    sent = 0
    blocked = 0
    for user_id, data in game_nicks.items():
        try:
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("✅ Да, иду", callback_data=f"vote_yes_{user_id}"),
                types.InlineKeyboardButton("❌ Нет, не иду", callback_data=f"vote_no_{user_id}")
            )
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
    save_json(VOTE_FILE, votes)

@bot.callback_query_handler(func=lambda call: call.data.startswith('vote_'))
def handle_vote(call):
    user_id = str(call.from_user.id)
    _, vote_type, target_id = call.data.split('_')
    if user_id != target_id:
        bot.answer_callback_query(call.id, "❌ Нельзя голосовать за другого")
        return
    if user_id not in game_nicks:
        bot.answer_callback_query(call.id, "❌ Ты не сохранил ник. Напиши /nick")
        return
    if user_id in votes:
        bot.answer_callback_query(call.id, "❌ Ты уже проголосовал")
        return
    votes[user_id] = vote_type
    save_json(VOTE_FILE, votes)
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
    print(f"Сохранено тегов: {len(player_tags)}")
    print(f"Админ ID: {ADMIN_ID}")
    print(f"Бот: @{BOT_USERNAME}")
    print(f"📁 Данные хранятся в: {DATA_DIR}")
    
    # Запускаем автообновление кэша клана (раз в 6 часов)
    update_clan_cache()
    schedule.every(6).hours.do(update_clan_cache)
    
    bot.remove_webhook()
    threading.Thread(target=run_schedule, daemon=True).start()
    bot.infinity_polling()
