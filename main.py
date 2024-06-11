import logging
import sqlite3
import config
from art import tprint
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ParseMode, ContentType
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


API_TOKEN = config.CONF_TOKEN
members = []

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

invite_storage = {}

scheduler = AsyncIOScheduler()

async def send_message(group_id):
    photo_url = config.WAY_TO_MEDIA
    caption = config.HELLO_TEXT
    keyboard = InlineKeyboardMarkup(row_width=1)
    button1 = InlineKeyboardButton(text="Добавить 20 новых участников", callback_data='addusers')
    button2 = InlineKeyboardButton(text="Я добавил 20 новых участников", callback_data='addedusers')
    keyboard.add(button1, button2)
    await bot.send_photo(chat_id=group_id, photo=photo_url, caption=caption, reply_markup=keyboard)


@dp.message_handler(content_types=types.ContentType.NEW_CHAT_MEMBERS)
async def on_new_chat_members(message: types.Message):
    scheduler.add_job(send_message(message.chat.id), 'cron', hour=12, minute=0)
    scheduler.add_job(send_message(message.chat.id), 'cron', hour=18, minute=0)
    scheduler.start()
    database = sqlite3.connect('usersinfo.db')
    cursor = database.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS usersinfo (
        id INTEGER PRIMARY KEY,
        tgid INTEGER,
        invites INTEGER,
        invitedusers TEXT,
        groupid INTEGER
    ) 
    ''')

    invited_user_id = message.new_chat_members[0].id
    who_invited_id = message.from_user.id
    group_id = message.chat.id
    cursor.execute('SELECT * FROM usersinfo WHERE tgid = ? AND groupid = ?', (who_invited_id, group_id))
    result = cursor.fetchone()

    try: bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    except Exception:
        pass

    if 7329880336 in [user.id for user in message.new_chat_members]:
        chat_id = message.chat.id
        photo_url = config.WAY_TO_MEDIA
        caption = config.HELLO_TEXT
        keyboard = InlineKeyboardMarkup(row_width=1)
        button1 = InlineKeyboardButton(text="Добавить 20 новых участников", callback_data='addusers')
        button2 = InlineKeyboardButton(text="Я добавил 20 новых участников", callback_data='addedusers')
        keyboard.add(button1, button2)
        print(members)
        await bot.send_photo(chat_id=message.chat.id, photo=photo_url, caption=caption, reply_markup=keyboard)

    if result:
        user_id, tgid, invites, invitedusers_str, groupid = result
        invitedusers = invitedusers_str.split(',') if invitedusers_str else []

        if str(invited_user_id) in invitedusers:
            tprint('A   cheating   attempt   has   been   detected!   The   attempt   was   not   counted   in   the   database')
            cursor.close()
            database.close()
            return

        invites += 1
        invitedusers.append(str(invited_user_id))
        invitedusers_str = ','.join(invitedusers)

        cursor.execute('''
        UPDATE usersinfo
        SET invites = ?, invitedusers = ?
        WHERE tgid = ? AND groupid = ?
        ''', (invites, invitedusers_str, tgid, groupid))
    else:
        cursor.execute('INSERT INTO usersinfo (tgid, invites, invitedusers, groupid) VALUES (?, ?, ?, ?)',
                       (who_invited_id, 1, str(invited_user_id), group_id))

    database.commit()
    cursor.close()
    database.close()


@dp.callback_query_handler(lambda query: query.data == 'addusers')
async def addusers(callback_query: types.CallbackQuery):
    # Получаем ID пользователя, который нажал на кнопку
    user_id = callback_query.from_user.id
    # Переходим в чат с ботом
    await bot.send_chat_action(chat_id=user_id, action=types.ChatActions.TYPING)
    await bot.send_message(chat_id=user_id, text=config.INVITE_TEXT)

@dp.callback_query_handler(lambda query: query.data == 'addedusers')
async def addedusers(callback_query: types.CallbackQuery):
    database = sqlite3.connect('usersinfo.db')
    cursor = database.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usersinfo (
            id INTEGER PRIMARY KEY,
            tgid INTEGER,
            invites INTEGER,
            invitedusers TEXT,
            groupid INTEGER
        ) 
        ''')
    user_id = callback_query.from_user.id
    group_id = callback_query.message.chat.id
    cheer_photo = config.WAY_TO_CHEER_MEDIA
    CHEER_TEXT = 'https://yourcontent.businessbouquet.online/?id=ID(' + user_id +')'
    cursor.execute("SELECT invites FROM usersinfo WHERE tgid = ? AND groupid = ?",
                   (user_id, group_id))
    invites = cursor.fetchall()
    print(invites, config.MINIMUM_INVITES)
    min_invites = config.MINIMUM_INVITES
    if invites[0][0] >= min_invites:
        await bot.send_photo(chat_id=user_id, photo=cheer_photo, caption=CHEER_TEXT)
    else:
        i_invited = 20 - invites[0][0]
        NOT_ENOUGH_INVITES_TEXT = 'Вы пригласили', str(invites[0][0])+', Вам нужно пригласить минимум еще', i_invited, 'человек.'
        await bot.send_message(chat_id=user_id, text=NOT_ENOUGH_INVITES_TEXT)
    database.commit()
    cursor.close()
    database.close()

if __name__ == '__main__':
    tprint('INVITE   BOT   LOADED. MADE   BY   @KrackF1')
    executor.start_polling(dp, skip_updates=True)
