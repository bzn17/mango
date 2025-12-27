import telebot
import threading
import json
import sqlite3
from flask import Flask, render_template_string

# --- НАСТРОЙКИ ---
BOT_TOKEN = '8567001241:AAEACtLehk_GTV0Mx-Aly9r3Rt8gjbMP-yk'
ADMIN_ID = 7916596817
DB_NAME = 'database.db'

# Инициализация
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# --- РАБОТА С БАЗОЙ ДАННЫХ (SQLITE) ---
def init_db():
    """Создает таблицу, если её нет"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link TEXT UNIQUE NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def get_bots():
    """Получает список всех ссылок"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT link FROM bots')
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def add_bot_db(link):
    """Добавляет ссылку. Возвращает True, если успешно, False, если такая уже есть"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO bots (link) VALUES (?)', (link,))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        # Ссылка уже существует
        return False

def delete_bot_db(target):
    """Удаляет ссылку, если она содержит target"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Удаляем строки, где ссылка похожа на введенную
    cursor.execute("DELETE FROM bots WHERE link LIKE ?", ('%' + target + '%',))
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted_count

# Создаем базу при старте скрипта
init_db()

# --- ЛОГИКА ТЕЛЕГРАМ БОТА ---

@bot.message_handler(func=lambda message: message.from_user.id != ADMIN_ID)
def ignore_others(message):
    return # Игнор всех кроме админа

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "🔋 Система запущена. База данных активна.\n/show - список\n/add ссылка - добавить\n/delete часть_ссылки - удалить")

@bot.message_handler(commands=['show'])
def show_bots(message):
    bots = get_bots()
    if not bots:
        bot.reply_to(message, "📂 База пуста.")
        return
    
    text = f"<b>📋 В базе {len(bots)} ботов:</b>\n\n"
    for i, link in enumerate(bots, 1):
        text += f"{i}. {link}\n"
    bot.reply_to(message, text, parse_mode='HTML', disable_web_page_preview=True)

@bot.message_handler(commands=['add'])
def add_bots_command(message):
    try:
        raw_text = message.text[4:].strip()
        if not raw_text:
            bot.reply_to(message, "⚠️ Пример: /add t.me/bot1, t.me/bot2")
            return

        links = [x.strip() for x in raw_text.split(',')]
        added = 0
        skipped = 0

        for link in links:
            if 't.me/' in link:
                if not link.startswith('http'):
                    final_link = 'https://' + link
                else:
                    final_link = link
                
                if add_bot_db(final_link):
                    added += 1
                else:
                    skipped += 1 # Дубликат
            else:
                bot.reply_to(message, f"❌ '{link}' - нет t.me/")

        msg = f"✅ Добавлено: {added}"
        if skipped > 0:
            msg += f"\n♻️ Дубликатов (пропущено): {skipped}"
        bot.reply_to(message, msg)
            
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['delete'])
def delete_bot_command(message):
    target = message.text[7:].strip()
    if not target:
        bot.reply_to(message, "⚠️ Пример: /delete my_bot_name")
        return

    count = delete_bot_db(target)
    if count > 0:
        bot.reply_to(message, f"🗑 Удалено ботов: {count}")
    else:
        bot.reply_to(message, "🔍 Ничего не найдено.")

# --- ВЕБ-СЕРВЕР ---
@app.route('/')
def home():
    current_bot_list = get_bots()
    
    html_template = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Актуальные Боты</title>
        <style>
            body {
                margin: 0; padding: 0; background-color: #121212; color: #ffffff;
                font-family: 'Courier New', Courier, monospace;
                display: flex; flex-direction: column; justify-content: center;
                align-items: center; height: 100vh;
            }
            .container {
                text-align: center; background: #1e1e1e; padding: 40px;
                border-radius: 15px; border: 1px solid #333;
                box-shadow: 0 0 20px rgba(0, 255, 136, 0.1);
                max-width: 90%; width: 400px;
            }
            h1 { color: #00ff88; margin-bottom: 10px; font-size: 24px; }
            p { color: #aaaaaa; margin-bottom: 30px; font-size: 14px; }
            .magic-button {
                background: linear-gradient(45deg, #00b09b, #96c93d);
                border: none; padding: 15px 30px; color: white;
                font-size: 18px; font-weight: bold; border-radius: 50px;
                cursor: pointer; transition: transform 0.2s, box-shadow 0.2s;
                width: 100%; text-transform: uppercase; letter-spacing: 1px;
            }
            .magic-button:hover { transform: scale(1.05); box-shadow: 0 0 15px rgba(0, 255, 136, 0.6); }
            .magic-button:active { transform: scale(0.95); }
            .status { margin-top: 20px; font-size: 12px; color: #555; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Актуальный бот ContentBox</h1>
            <p>Нажми на кнопку, чтобы перейти к актуальному боту.</p>
            
            <button class="magic-button" onclick="openRandomBot()">Перейти</button>
            <div class="status" id="statusText">Ожидание выбора...</div>
        </div>

        <script>
            const botList = {{ bots_json|safe }};

            function openRandomBot() {
                if (!botList || botList.length === 0) {
                    document.getElementById("statusText").innerHTML = "Список пуст, ждем админа...";
                    return;
                }
                const randomIndex = Math.floor(Math.random() * botList.length);
                const selectedBot = botList[randomIndex];
                const statusDiv = document.getElementById("statusText");
                statusDiv.innerHTML = "Перенаправление...";
                statusDiv.style.color = "#00ff88";
                setTimeout(() => {
                    window.location.href = selectedBot; 
                }, 500);
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(html_template, bots_json=json.dumps(current_bot_list))

def run_bot():
    try:
        bot.remove_webhook()
        bot.polling(none_stop=True)
    except Exception as e:
        print(e)

if __name__ == '__main__':
    t = threading.Thread(target=run_bot)
    t.start()
    app.run(host='0.0.0.0', port=5000, debug=False)
