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
CLAN_TAG = "#QGQQV82P"  # тег клана
# ================================

bot = telebot.TeleBot(TOKEN)

# ========== ПОСТОЯННОЕ ХРАНИЛИЩЕ ==========
DATA_DIR = "/app/data"
os.makedirs(DATA_DIR, exist_ok=True)

NICK_FILE = os.path.join(DATA_DIR, "game_nicks.json")
VOTE_FILE = os.path.join(DATA_DIR, "votes.json")
PLAYER_TAGS_FILE = os.path.join(DATA_DIR, "player_tags.json")
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

def is_admin(user_id):
    return user_id == ADMIN_ID

def nick_button():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("➕ Добавить свой ник")
    return markup

# ========== API С БИБЛИОТЕКОЙ (попытка) ==========
try:
    from clash_royale import Client
    client = Client()
    print("✅ Библиотека clash-royale-python загружена")
except:
    client = None
    print("⚠️ Библиотека не загружена, используем резервный RoyaleAPI")

def get_player_data(tag):
    tag_clean = tag.replace("#", "").upper()
    data = None
    
    # 1. Пробуем официальный API через библиотеку
    if client:
        try:
            player = client.get_player(tag)
            data = {
                "name": player.name,
                "tag": player.tag,
                "trophies": player.trophies,
                "kingLevel": player.king_level,
                "wins": player.wins,
                "losses": player.losses,
                "highestTrophies": player.best_trophies,
                "clan": player.clan.name if player.clan else "Нет клана",
                "clan_tag": player.clan.tag if player.clan else "",
                "lastSeen": "недавно"
            }
        except Exception as e:
            print(f"Ошибка библиотеки: {e}")
    
    # 2. Если библиотека не сработала — используем RoyaleAPI
    if not data:
        try:
            url = f"https://royaleapi.com/api/player/{tag_clean}"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                d = resp.json()
                data = {
                    "name": d.get("name", "?"),
                    "tag": d.get("tag", tag),
                    "trophies": d.get("trophies", 0),
                    "kingLevel": d.get("kingLevel", 0),
                    "wins": d.get("wins", 0),
                    "losses": d.get("losses", 0),
                    "highestTrophies": d.get("bestTrophies", 0),
                    "clan": d.get("clan", {}).get("name", "Нет клана"),
                    "clan_tag": d.get("clan", {}).get("tag", ""),
                    "lastSeen": d.get("lastSeen", "неизвестно")
                }
        except Exception as e:
            print(f"Ошибка RoyaleAPI: {e}")
    
    return data

# ========== КОМАНДЫ ==========
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id,
        "👋 Привет! Я бот клана Black Rose.\n\nНажми кнопку «Добавить свой ник» и напиши свой игровой ник.",
        reply_markup=nick_button())

@bot.message_handler(func=lambda m: m.text == "➕ Добавить свой ник")
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
    save_json(NICK_FILE, game_nicks)
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
        if data.get('tg_username'):
            text += f" (@{data['tg_username']})"
        text += "\n"
    if is_admin(message.from_user.id):
        text += "\n🔧 Админ: /del НОМЕР — удалить игрока"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(commands=['tag'])
def save_tag(message):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Напиши так: /tag #твой_тег")
            return
        tag = parts[1].strip()
        if not tag.startswith("#"):
            tag = "#" + tag
        
        data = get_player_data(tag)
        if not data:
            bot.reply_to(message, "❌ Тег не найден в Clash Royale. Проверь и попробуй ещё раз.")
            return
        
        user_id = str(message.from_user.id)
        player_tags[user_id] = tag
        save_json(PLAYER_TAGS_FILE, player_tags)
        
        # Выводим полную статистику
        stats = (
            f"✅ Тег **{tag}** сохранён для игрока **{data['name']}**!\n\n"
            f"🏆 Трофеи: {data['trophies']}\n"
            f"👑 Уровень короля: {data['kingLevel']}\n"
            f"⚔️ Победы: {data['wins']}\n"
            f"💔 Поражения: {data['losses']}\n"
            f"🎯 Максимум трофеев: {data['highestTrophies']}\n"
            f"🏛 Клан: {data['clan']}\n"
            f"📅 Последний бой: {data['lastSeen']}"
        )
        bot.reply_to(message, stats, parse_mode="Markdown")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

# ========== ОСТАЛЬНЫЕ КОМАНДЫ (упрощённо) ==========
@bot.message_handler(commands=['del'])
def delete_nick(message):
    if not is_admin(message.from_user.id):
        bot.reply_to(message, "❌ Только админ")
        return
    try:
        num = int(message.text.split()[1])
        items = list(game_nicks.items())
        if 1 <= num <= len(items):
            uid, _ = items[num-1]
            del game_nicks[uid]
            if uid in player_tags:
                del player_tags[uid]
            save_json(NICK_FILE, game_nicks)
            save_json(PLAYER_TAGS_FILE, player_tags)
            bot.reply_to(message, f"✅ Игрок удалён")
            list_nicks(message)
    except:
        bot.reply_to(message, "❌ Пример: /del 2")

@bot.message_handler(commands=['whoami'])
def whoami(message):
    bot.reply_to(message, f"Твой ID: {message.from_user.id}")

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    try:
        requests.get(f"https://api.telegram.org/bot{TOKEN}/deleteWebhook")
        print("✅ Webhook deleted")
    except Exception as e:
        print(f"❌ Webhook delete error: {e}")

    print("🚀 Бот запущен")
    print(f"Сохранено ников: {len(game_nicks)}")
    bot.infinity_polling()
