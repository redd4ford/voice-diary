from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from aiogram.types import ParseMode, ReplyKeyboardMarkup, KeyboardButton
import db_controller
import firebase_admin
import subprocess
import os
import vosk
from utils import days_ago_date, process_fetched, get_date, date_to_timestamp
from recognize_controller import recognize_phrase

TOKEN = 'TOKEN'

VOICE_MODEL = vosk.Model

if not firebase_admin._apps:
    cred = firebase_admin.credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

"""
    POSSIBLE STATES:
    - IDLE
    - VID_PR - video processing
    - GET_ALL - get all the recordings
    - GET_LAST_N - get last N recordings
    - GET_BY_DATE - get all by date
    - GET_ALL_BW - get all between two dates
    - GET_ALL_AF - get all after date
    - GET_ALL_TP - get all by topic
"""
STATES = dict()

get_rec_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)\
    .add(KeyboardButton('Get all the recordings'))\
    .row(KeyboardButton('by date'), KeyboardButton('by topic'))\
    .add(KeyboardButton('last N recordings'))\
    .row(KeyboardButton('between two dates'), KeyboardButton('after date'))

freq_used_dates_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)\
    .add(KeyboardButton('Today')).add(KeyboardButton('Yesterday')).add(KeyboardButton('Past week'))

freq_used_topics_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(KeyboardButton('None'))


@dp.message_handler(commands=['start'])
async def process_start_command(msg: types.Message):
    STATES[msg.from_user.id] = 'IDLE'
    await msg.reply('Hello there!\nI can recognize phrases from your voice messages, convert them to txt, '
                    'and store in Firestore DB. Send me a voice message to start.', reply_markup=get_rec_kb)


@dp.message_handler(text=['Get all the recordings', 'Отримати всі', 'Получить все'])   # TODO LOCAL
async def process_get_all(msg: types.Message):
    STATES[msg.from_user.id] = 'GET_ALL'
    recordings = process_fetched(await db_controller.fetch_all(user_id=msg.from_user.id))
    await msg.reply(str(recordings), reply_markup=get_rec_kb)   # TODO NICE VISUALIZATION
    STATES[msg.from_user.id] = 'IDLE'


@dp.message_handler(text=['by date', 'after date'])   # TODO LOCAL
async def process_get_by_date(msg: types.Message):
    STATES[msg.from_user.id] = 'GET_BY_DATE' if msg.text == 'Get by date' else 'GET_ALL_AF'
    await msg.reply('Send me a date in format <b>YYYY-mm-dd HH:MM:SS</b> or just <b>YYYY-mm-dd</b>.',
                    reply_markup=freq_used_dates_kb, parse_mode=ParseMode.HTML)


@dp.message_handler(text=['Today', 'Yesterday', 'Past week'])   # TODO LOCAL
async def process_get_date_kb(msg: types.Message):
    if STATES[msg.from_user.id] in ['GET_BY_DATE', 'GET_ALL_AF']:
        cases = {'Today': 0, 'Yesterday': 1, 'Past week': 7}
        datestamp = days_ago_date(days=cases[msg.text])
        recordings = process_fetched(
            await db_controller.fetch_by_date(user_id=msg.from_user.id, date=datestamp, is_exact=False)
            if STATES[msg.from_user.id] == 'GET_BY_DATE' else
            await db_controller.fetch_after(user_id=msg.from_user.id, date=datestamp)
        )
        await msg.reply(str(recordings), reply_markup=get_rec_kb)  # TODO NICE VISUALIZATION
        STATES[msg.from_user.id] = 'IDLE'


@dp.message_handler(text=['between two dates'])   # TODO LOCAL
async def process_get_between(msg: types.Message):
    STATES[msg.from_user.id] = 'GET_ALL_BW'
    await msg.reply('Send me two dates separated by space in format <b>YYYY-mm-dd HH:MM:SS YYYY-mm-dd '
                    'HH:MM:SS</b> or just <b>YYYY-mm-dd YYYY-mm-dd</b>.', parse_mode=ParseMode.HTML)


@dp.message_handler(regexp=r'^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$')
async def process_get_date_input(msg: types.Message):
    # there are only two acceptable cases: either it's just a date or it's a date plus time
    len_with_time = 19
    len_without_time = 10
    datestamp = msg.text
    if STATES[msg.from_user.id] == 'GET_BY_DATE':
        is_exact = True
        if len(datestamp) == len_without_time:
            datestamp = f'{datestamp} 00:00:00'
            is_exact = False
        print(datestamp)
        recordings = process_fetched(
            await db_controller.fetch_by_date(user_id=msg.from_user.id, date=datestamp, is_exact=is_exact)
        )
        await msg.reply(str(recordings), reply_markup=get_rec_kb)   # TODO NICE VISUALIZATION
        STATES[msg.from_user.id] = 'IDLE'
    elif STATES[msg.from_user.id] == 'GET_ALL_AF':
        if len(datestamp) == len_without_time:
            datestamp = f'{datestamp} 00:00:00'
        if len(datestamp) == len_with_time:
            recordings = process_fetched(await db_controller.fetch_after(user_id=msg.from_user.id, date=datestamp))
            await msg.reply(str(recordings), reply_markup=get_rec_kb)   # TODO NICE VISUALIZATION
        STATES[msg.from_user.id] = 'IDLE'


@dp.message_handler(regexp=r'^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})? \d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$')
async def process_get_between_input(msg: types.Message):
    len_with_time = 39
    len_without_time = 21
    if STATES[msg.from_user.id] == 'GET_ALL_BW':
        datestamps = msg.text
        if len(datestamps) == len_without_time:
            datestamps = f'{datestamps[:10]} 00:00:00 {datestamps[11:]} 23:59:59'
        if len(datestamps) == len_with_time:
            date1 = datestamps[:19]
            date2 = datestamps[20:]
            # get all the matches for this date
            recordings = process_fetched(
                await db_controller.fetch_between(user_id=msg.from_user.id, date1=date1, date2=date2)
            )
            await msg.reply(str(recordings), reply_markup=get_rec_kb)   # TODO NICE VISUALIZATION
            STATES[msg.from_user.id] = 'IDLE'


@dp.message_handler(text=['last N recordings'])   # TODO LOCAL
async def process_get_last_n_command(msg: types.Message):
    STATES[msg.from_user.id] = 'GET_LAST_N'
    await msg.reply('Send me a number of recordings you want to get.')


@dp.message_handler(regexp=r'^\d+$')   # TODO LOCAL
async def process_get_last_n_number_input(msg: types.Message):
    if STATES[msg.from_user.id] == 'GET_LAST_N':
        recordings = process_fetched(await db_controller.fetch_last_n(user_id=msg.from_user.id, number=int(msg.text)))
        await msg.reply(str(recordings), reply_markup=get_rec_kb)   # TODO NICE VISUALIZATION
        STATES[msg.from_user.id] = 'IDLE'


@dp.message_handler(text=['by topic'])   # TODO LOCAL
async def process_get_by_topic_command(msg: types.Message):
    STATES[msg.from_user.id] = 'GET_BY_TP'
    await msg.reply('Send me a topic name to search for.', reply_markup=freq_used_topics_kb)


@dp.message_handler(regexp=r'^.*$')   # TODO LOCAL
async def process_get_topic_input(msg: types.Message):
    if STATES[msg.from_user.id] == 'GET_BY_TP':
        recordings = process_fetched(await db_controller.fetch_by_topic(user_id=msg.from_user.id, topic=msg.text))
        await msg.reply(str(recordings), reply_markup=get_rec_kb)   # TODO NICE VISUALIZATION
        STATES[msg.from_user.id] = 'IDLE'


@dp.message_handler(content_types=['voice'])
async def process_voice_message(msg: types.Message):
    datestamp = get_date()
    timestamp = date_to_timestamp(datestamp)
    filename = f'{msg.chat.id}_{timestamp}'

    voice_message = await bot.get_file(msg.voice.file_id)
    await bot.download_file(voice_message.file_path, f'{filename}.ogg')

    process = subprocess.Popen(['ffmpeg', '-i', f'{filename}.ogg', f'{filename}.wav'], shell=True)
    if process.returncode != 0:
        raise Exception('Something went wrong')   # FIXME

    user_text = recognize_phrase(VOICE_MODEL, f'{filename}.wav')
    await db_controller.create_recording(user_id=msg.from_user.id, recording={
        'date': datestamp,
        'timestamp': timestamp,
        'topic': 'None',   # TODO ADD TOPICS
        'text': user_text
    })

    await msg.reply(f'Message stored: {datestamp}', reply_markup=get_rec_kb)

    os.remove(f'{filename}.ogg')
    os.remove(f'{filename}.wav')


if __name__ == '__main__':
    executor.start_polling(dp)
