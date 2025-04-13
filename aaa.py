import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
from googletrans import Translator
from gtts import gTTS
import os

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация переводчика
translator = Translator()

# Подключение к базе данных SQLite
def init_db():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()

    # Создаем таблицу users, если она не существует
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT
        )
    ''')

    # Создаем таблицу favorites, если она не существует
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            phrase TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')

    conn.commit()
    conn.close()

# Функция для добавления пользователя в базу данных
def add_user_to_db(user_id, username, first_name, last_name):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()

    # Проверяем, существует ли пользователь
    cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name))

    conn.commit()
    conn.close()

# Функция для добавления фразы в избранное
def add_favorite_to_db(user_id, phrase):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO favorites (user_id, phrase)
        VALUES (?, ?)
    ''', (user_id, phrase))

    conn.commit()
    conn.close()

# Функция для получения избранного пользователя
def get_favorites_from_db(user_id):
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()

    cursor.execute('SELECT phrase FROM favorites WHERE user_id = ?', (user_id,))
    favorites = cursor.fetchall()

    conn.close()
    return [fav[0] for fav in favorites]  # Возвращаем список фраз

# Функция для перевода текста
def translate_text(text, dest_language):
    try:
        translation = translator.translate(text, dest=dest_language)
        return translation.text
    except Exception as e:
        logger.error(f"Ошибка перевода: {e}")
        return "Ошибка перевода. Попробуйте снова."

# Функция для создания голосового сообщения
def create_voice_message(text, language):
    try:
        tts = gTTS(text=text, lang=language)
        filename = "voice_message.mp3"
        tts.save(filename)
        return filename
    except Exception as e:
        logger.error(f"Ошибка создания голосового сообщения: {e}")
        return None

# Обработчик команды /start
def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    add_user_to_db(user.id, user.username, user.first_name, user.last_name)  # Добавляем пользователя в базу данных
    update.message.reply_text("Привет! Отправь мне текст, и я переведу его. Используй команды:\n"
                             "/tolang - выбрать язык перевода\n"
                             "/favourites - показать избранное\n"
                             "/learn - изучать избранные фразы\n"
                             "/quiz - пройти викторину")

# Обработчик команды /tolang
def tolang(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("Английский🇬🇧", callback_data="lang_en"), InlineKeyboardButton("Русский🇷🇺", callback_data="lang_ru")],
        [InlineKeyboardButton("Французский🇫🇷", callback_data="lang_fr"), InlineKeyboardButton("Немецкий🇩🇪", callback_data="lang_de")],
        [InlineKeyboardButton("Таджикский🇹🇯", callback_data="lang_tg"), InlineKeyboardButton("Узбекский🇺🇿", callback_data="lang_uz")],
        [InlineKeyboardButton("Арабский🇸🇦", callback_data="lang_ar"), InlineKeyboardButton("Итальянский🇮🇹", callback_data="lang_it")],
        [InlineKeyboardButton("Китайский традиционный", callback_data="lang_zh-TW"), InlineKeyboardButton("Китайский упрощенный🇨🇳", callback_data="lang_zh-CN")],
        [InlineKeyboardButton("Корейский🇰🇷", callback_data="lang_ko"), InlineKeyboardButton("Японский🇯🇵", callback_data="lang_ja")],
        [InlineKeyboardButton("Испанский🇪🇸", callback_data="lang_es"), InlineKeyboardButton("Турецкий🇹🇷", callback_data="lang_tr")],
        [InlineKeyboardButton("Казахский🇰🇿", callback_data="lang_kk"), InlineKeyboardButton("Кыргызский🇰🇬", callback_data="lang_ky")],
        [InlineKeyboardButton("Хинди🇮🇳", callback_data="lang_hi"), InlineKeyboardButton("Бенгальский🇧🇩", callback_data="lang_bn")],
        [InlineKeyboardButton("Португальский🇵🇹", callback_data="lang_pt"), InlineKeyboardButton("Урду🇵🇰", callback_data="lang_ur")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Выберите язык перевода:", reply_markup=reply_markup)

# Обработчик команды /favourites
def show_favourites(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    favorites = get_favorites_from_db(user_id)  # Получаем избранное из базы данных

    if favorites:
        favorite_texts = "\n".join(favorites)
        update.message.reply_text(f"Ваше избранное:\n{favorite_texts}")
    else:
        update.message.reply_text("Ваше избранное пусто😢.")

# Обработчик команды /learn
def learn(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    favorites = get_favorites_from_db(user_id)  # Получаем избранное из базы данных

    if not favorites:
        update.message.reply_text("Ваше избранное пусто😢.")
        return

    # Сохраняем индекс текущей фразы для изучения
    context.user_data['learn_index'] = 0
    context.user_data['learn_user_id'] = user_id

    # Показываем первую фразу
    show_next_phrase(update, context)

# Функция для показа следующей фразы
def show_next_phrase(update: Update, context: CallbackContext):
    user_id = context.user_data.get('learn_user_id')
    learn_index = context.user_data.get('learn_index', 0)
    favorites = get_favorites_from_db(user_id)  # Получаем избранное из базы данных

    if learn_index >= len(favorites):
        update.message.reply_text("Вы изучили все фразы! 🎉")
        return

    phrase = favorites[learn_index]
    context.user_data['learn_index'] = learn_index + 1

    keyboard = [[InlineKeyboardButton("Перевести", callback_data=f'translate_phrase_{learn_index}')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(f"Фраза для изучения:\n{phrase}", reply_markup=reply_markup)

# Обработчик команды /quiz
def quiz(update: Update, context: CallbackContext):
    # Создаем кнопку с ссылкой на мини-приложение
    keyboard = [
        [InlineKeyboardButton("Пройти викторину 🎮", url="http://t.me/TalkTranslatorbot/quiz")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Нажмите на кнопку ниже, чтобы перейти к викторине:", reply_markup=reply_markup)

# Обработчик текстовых сообщений
def handle_text(update: Update, context: CallbackContext):
    user_text = update.message.text
    context.user_data['original_text'] = user_text

    target_language = context.user_data.get('target_language', 'en')
    translated_text = translate_text(user_text, target_language)

    keyboard = [
        [InlineKeyboardButton("Озвучить перевод 🔊", callback_data='voice_translated')],
        [InlineKeyboardButton("Озвучить оригинал 🔊", callback_data='voice_original')],
        [InlineKeyboardButton("Добавить в избранное ⭐️", callback_data='add_to_favorites')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(f"Перевод ({target_language}): {translated_text}", reply_markup=reply_markup)

# Обработчик нажатий на кнопки
def button_click(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    user_id = query.from_user.id
    original_text = context.user_data.get('original_text', '')
    target_language = context.user_data.get('target_language', 'en')

    if query.data == 'voice_translated':
        translated_text = translate_text(original_text, target_language)
        voice_file = create_voice_message(translated_text, target_language)
        if voice_file:
            query.message.reply_voice(voice=open(voice_file, 'rb'))
            os.remove(voice_file)
        else:
            query.message.reply_text("Ошибка создания голосового сообщения.")

    elif query.data == 'voice_original':
        voice_file = create_voice_message(original_text, 'ru')
        if voice_file:
            query.message.reply_voice(voice=open(voice_file, 'rb'))
            os.remove(voice_file)
        else:
            query.message.reply_text("Ошибка создания голосового сообщения.")

    elif query.data == 'add_to_favorites':
        add_favorite_to_db(user_id, original_text)  # Добавляем фразу в избранное в базу данных
        query.message.reply_text("Добавлено в избранное ⭐️")

    elif query.data.startswith('lang_'):
        lang_code = query.data.split('_')[1]
        lang_names = {
            "en": "Английский🇬🇧", "ru": "Русский🇷🇺", "fr": "Французский🇫🇷", "de": "Немецкий🇩🇪",
            "tg": "Таджикский🇹🇯", "uz": "Узбекский🇺🇿", "ar": "Арабский🇸🇦", "it": "Итальянский🇮🇹",
            "zh-TW": "Китайский традиционный🇨🇳", "zh-CN": "Китайский упрощенный🇨🇳", "ko": "Корейский🇰🇷",
            "ja": "Японский🇯🇵", "es": "Испанский🇪🇸", "tr": "Турецкий🇹🇷", "kk": "Казахский🇰🇿",
            "ky": "Кыргызский🇰🇬", "hi": "Хинди🇮🇳", "bn": "Бенгальский🇧🇩", "pt": "Португальский🇵🇹",
            "ur": "Урду🇵🇰"
        }
        lang_name = lang_names.get(lang_code, 'Английский')
        context.user_data['target_language'] = lang_code
        query.message.reply_text(f"Язык перевода изменен на {lang_name}.")

    elif query.data.startswith('translate_phrase_'):
        learn_index = int(query.data.split('_')[-1])
        user_id = context.user_data.get('learn_user_id')
        target_language = context.user_data.get('target_language', 'en')
        favorites = get_favorites_from_db(user_id)

        phrase = favorites[learn_index]
        translated_text = translate_text(phrase, target_language)
        query.message.reply_text(f"Перевод:\n{translated_text}")

        voice_file = create_voice_message(translated_text, target_language)
        if voice_file:
            query.message.reply_voice(voice=open(voice_file, 'rb'))
            os.remove(voice_file)
        else:
            query.message.reply_text("Ошибка создания голосового сообщения.")

        show_next_phrase(query, context)

# Основная функция
def main():
    init_db()  # Инициализируем базу данных
    updater = Updater("7278991582:AAFq_35XDFlt99pw4mY5fr_ErYwg7jQF8QI", use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("tolang", tolang))
    dp.add_handler(CommandHandler("favourites", show_favourites))
    dp.add_handler(CommandHandler("learn", learn))
    dp.add_handler(CommandHandler("quiz", quiz))  # Добавляем обработчик команды /quiz

    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    dp.add_handler(CallbackQueryHandler(button_click))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()