import os
import re
from collections import defaultdict

import google.api_core.exceptions as g
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.types import ParseMode
from aiogram.utils import executor

import db_controller
from bot_kb import get_entries_kb, get_lan_kb, freq_used_topics_kb, freq_used_dates_kb
from recognize_controller import recognize_google_api, recognize_speech_to_text
from user_state import UserState
from utils import days_ago_date, get_current_date, date_to_timestamp, timestamp_to_date, get_current_timestamp_len, \
    process_fetched, process_text, format_entry, ogg_to_wav, clear_user_data

TOKEN = 'TOKEN'

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

USER_DATA = defaultdict(defaultdict)

AUDIO_STATES = [UserState.AUDIO_INPUT_TOPIC, UserState.AUDIO_INPUT_LANGUAGE, UserState.AUDIO_AUTO_LANGUAGE,
                UserState.AUDIO_PROCESSING]

DATESTAMP_LEN_WITH_TIME = len('YEAR-MM-DD 00:00:00')   # 19
DATESTAMP_LEN_WITHOUT_TIME = len('YEAR-MM-DD')   # 10
TIMESTAMP_LEN = get_current_timestamp_len()   # 10


@dp.message_handler(commands=['start'])
async def process_start_command(msg: types.Message):
    if 'state' not in USER_DATA[msg.from_user.id].keys():
        USER_DATA[msg.from_user.id]['state'] = UserState.IDLE
    await msg.reply('Hello there!\nI can recognize phrases from your voice messages, convert them to txt, '
                    'and store in Firestore DB. Send me a voice message to start. I support messages in '
                    '<b>English</b>, <b>Russian</b>, and <b>Ukrainian.</b>',
                    reply_markup=get_entries_kb, parse_mode=ParseMode.HTML)


@dp.message_handler(text=['Get all the entries'])
async def process_get_all(msg: types.Message):
    if 'state' not in USER_DATA[msg.from_user.id].keys():
        USER_DATA[msg.from_user.id]['state'] = UserState.IDLE
    if USER_DATA[msg.from_user.id]['state'] not in AUDIO_STATES:
        USER_DATA[msg.from_user.id]['state'] = UserState.GET_ALL
        entries = process_fetched(await db_controller.fetch_all(user_id=msg.from_user.id))
        await print_entries(msg, entries)
        USER_DATA[msg.from_user.id]['state'] = UserState.IDLE


@dp.message_handler(text=['by date', 'after date'])
async def process_get_by_date(msg: types.Message):
    if 'state' not in USER_DATA[msg.from_user.id].keys():
        USER_DATA[msg.from_user.id]['state'] = UserState.IDLE
    if USER_DATA[msg.from_user.id]['state'] not in AUDIO_STATES:
        USER_DATA[msg.from_user.id]['state'] = \
            UserState.GET_BY_DATE if msg.text == 'by date' else UserState.GET_ALL_AFTER
        await msg.reply('Send me a date in format <b>YYYY-mm-dd HH:MM:SS</b> or just <b>YYYY-mm-dd</b>.',
                        reply_markup=freq_used_dates_kb, parse_mode=ParseMode.HTML)


@dp.message_handler(text=['Today', 'Yesterday', 'Past week'])
async def process_get_date_kb(msg: types.Message):
    if 'state' not in USER_DATA[msg.from_user.id].keys():
        USER_DATA[msg.from_user.id]['state'] = UserState.IDLE
    if USER_DATA[msg.from_user.id]['state'] in [UserState.GET_BY_DATE, UserState.GET_ALL_AFTER]:
        days_since = {'Today': 0, 'Yesterday': 1, 'Past week': 7}
        datestamp = days_ago_date(days=days_since[msg.text])
        entries = process_fetched(
            await db_controller.fetch_by_date(user_id=msg.from_user.id, date=datestamp, is_exact=False)
            if USER_DATA[msg.from_user.id]['state'] == UserState.GET_BY_DATE else
            await db_controller.fetch_after(user_id=msg.from_user.id, date=datestamp)
        )
        await print_entries(msg, entries)
        USER_DATA[msg.from_user.id]['state'] = UserState.IDLE


@dp.message_handler(text=['between two dates'])
async def process_get_between(msg: types.Message):
    if 'state' not in USER_DATA[msg.from_user.id].keys():
        USER_DATA[msg.from_user.id]['state'] = UserState.IDLE
    if USER_DATA[msg.from_user.id]['state'] not in AUDIO_STATES:
        USER_DATA[msg.from_user.id]['state'] = UserState.GET_ALL_BETWEEN
        await msg.reply('Send me two dates separated by space in format <b>YYYY-mm-dd HH:MM:SS YYYY-mm-dd '
                        'HH:MM:SS</b> or just <b>YYYY-mm-dd YYYY-mm-dd</b>.', parse_mode=ParseMode.HTML)


@dp.message_handler(regexp=r'^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$')
async def process_get_date_input(msg: types.Message):
    if 'state' not in USER_DATA[msg.from_user.id].keys():
        USER_DATA[msg.from_user.id]['state'] = UserState.IDLE
    if USER_DATA[msg.from_user.id]['state'] not in AUDIO_STATES:
        datestamp = msg.text
        if USER_DATA[msg.from_user.id]['state'] == UserState.GET_BY_DATE:
            # there are only two acceptable cases: either it's just a date or it's a date plus time
            is_exact = True
            if len(datestamp) == DATESTAMP_LEN_WITHOUT_TIME:
                datestamp += ' ' + '00:00:00'
                is_exact = False
            entries = process_fetched(
                await db_controller.fetch_by_date(user_id=msg.from_user.id, date=datestamp, is_exact=is_exact)
            )
            await print_entries(msg, entries)
            USER_DATA[msg.from_user.id]['state'] = UserState.IDLE
        elif USER_DATA[msg.from_user.id]['state'] == UserState.GET_ALL_AFTER:
            if len(datestamp) == DATESTAMP_LEN_WITHOUT_TIME:
                datestamp += ' ' + '00:00:00'
            if len(datestamp) == DATESTAMP_LEN_WITH_TIME:
                entries = process_fetched(await db_controller.fetch_after(user_id=msg.from_user.id, date=datestamp))
                await print_entries(msg, entries)
            USER_DATA[msg.from_user.id]['state'] = UserState.IDLE


@dp.message_handler(regexp=r'^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})? \d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$')
async def process_get_between_input(msg: types.Message):
    if 'state' not in USER_DATA[msg.from_user.id].keys():
        USER_DATA[msg.from_user.id]['state'] = UserState.IDLE
    if USER_DATA[msg.from_user.id]['state'] not in AUDIO_STATES:
        if USER_DATA[msg.from_user.id]['state'] == UserState.GET_ALL_BETWEEN:
            datestamps = msg.text
            if len(datestamps) == DATESTAMP_LEN_WITHOUT_TIME * 2 + 1:   # 21: 2 datestamps w/out time + space symbol
                datestamps = f'{datestamps[:TIMESTAMP_LEN]} 00:00:00 {datestamps[(TIMESTAMP_LEN + 1):]} 23:59:59'
            if len(datestamps) == DATESTAMP_LEN_WITH_TIME * 2 + 1:   # 39: 2 datestamps w/ time + space symbol
                date1 = datestamps[:DATESTAMP_LEN_WITH_TIME]
                date2 = datestamps[(DATESTAMP_LEN_WITH_TIME + 1):]   # omitting that space after the 1st datestamp
                # get all the matches for this date
                entries = process_fetched(
                    await db_controller.fetch_between(user_id=msg.from_user.id, date1=date1, date2=date2)
                )
                await print_entries(msg, entries)
                USER_DATA[msg.from_user.id]['state'] = UserState.IDLE


@dp.message_handler(text=['last N entries'])
async def process_get_last_n_command(msg: types.Message):
    if 'state' not in USER_DATA[msg.from_user.id].keys():
        USER_DATA[msg.from_user.id]['state'] = UserState.IDLE
    if USER_DATA[msg.from_user.id]['state'] not in AUDIO_STATES:
        USER_DATA[msg.from_user.id]['state'] = UserState.GET_LAST_N
        await msg.reply('Send me a number of entries you want to get.')


@dp.message_handler(regexp=r'^\d+$')
async def process_get_number_input(msg: types.Message):
    if 'state' not in USER_DATA[msg.from_user.id].keys():
        USER_DATA[msg.from_user.id]['state'] = UserState.IDLE
    if USER_DATA[msg.from_user.id]['state'] == UserState.GET_LAST_N:
        entries = process_fetched(await db_controller.fetch_last_n(user_id=msg.from_user.id, number=int(msg.text)))
        await print_entries(msg, entries)
        USER_DATA[msg.from_user.id]['state'] = UserState.IDLE


@dp.message_handler(text=['by topic'])
async def process_get_by_topic_command(msg: types.Message):
    if 'state' not in USER_DATA[msg.from_user.id].keys():
        USER_DATA[msg.from_user.id]['state'] = UserState.IDLE
    if USER_DATA[msg.from_user.id]['state'] not in AUDIO_STATES:
        USER_DATA[msg.from_user.id]['state'] = UserState.GET_BY_TOPIC
        await msg.reply('Send me a topic name to search for.', reply_markup=freq_used_topics_kb)


@dp.message_handler(regexp=r'^.*$')
async def process_get_text_input(msg: types.Message):
    if 'state' not in USER_DATA[msg.from_user.id].keys():
        USER_DATA[msg.from_user.id]['state'] = UserState.IDLE
    command = re.search(rf'^/d_(\d{TIMESTAMP_LEN})$', msg.text)   # /d command regex

    if USER_DATA[msg.from_user.id]['state'] == UserState.GET_BY_TOPIC:
        entries = process_fetched(await db_controller.fetch_by_topic(user_id=msg.from_user.id, topic=msg.text))
        await print_entries(msg, entries)
        USER_DATA[msg.from_user.id]['state'] = UserState.IDLE

    elif USER_DATA[msg.from_user.id]['state'] == UserState.AUDIO_INPUT_TOPIC:
        USER_DATA[msg.from_user.id]['entry']['topic'] = msg.text
        # try auto detecting the language with Speech-To-Text
        USER_DATA[msg.from_user.id]['state'] = UserState.AUDIO_AUTO_LANGUAGE
        await convert_voice_message_using_s2t(msg)

    elif USER_DATA[msg.from_user.id]['state'] == UserState.AUDIO_INPUT_LANGUAGE:
        # buttons also contain flag emojis, so we need to remove them from msg.text
        USER_DATA[msg.from_user.id]['entry']['language'] = msg.text[3:]
        USER_DATA[msg.from_user.id]['state'] = UserState.AUDIO_PROCESSING
        await convert_voice_message_using_gapi(msg)

    elif USER_DATA[msg.from_user.id]['state'] == UserState.IDLE and command:
        timestamp = int(command.group(1))
        await db_controller.delete_entry(user_id=msg.from_user.id, timestamp=timestamp)
        await msg.reply(f'Successfully removed the entry: <b>{timestamp_to_date(timestamp=timestamp)}</b>',
                        reply_markup=freq_used_topics_kb, parse_mode=ParseMode.HTML)


@dp.message_handler(content_types=['voice'])
async def process_voice_message(msg: types.Message):
    if 'state' not in USER_DATA[msg.from_user.id].keys():
        USER_DATA[msg.from_user.id]['state'] = UserState.IDLE
    if USER_DATA[msg.from_user.id]['state'] not in AUDIO_STATES:
        datestamp = get_current_date()
        timestamp = date_to_timestamp(datestamp)
        USER_DATA[msg.from_user.id]['entry'] = {'date': datestamp, 'timestamp': timestamp, 'topic': 'None'}

        voice_message = await bot.get_file(msg.voice.file_id)
        await bot.download_file(voice_message.file_path, f'{msg.chat.id}_{timestamp}.ogg')

        USER_DATA[msg.from_user.id]['state'] = UserState.AUDIO_INPUT_TOPIC
        await msg.reply(f'Please choose the topic for this entry.', reply_markup=freq_used_topics_kb)


async def convert_voice_message_using_s2t(msg: types.Message):
    filename = f'{msg.from_user.id}_{USER_DATA[msg.from_user.id]["entry"]["timestamp"]}'
    try:
        ogg_to_wav(filename)
        language, text = recognize_speech_to_text(f'{filename}.wav')
        USER_DATA[msg.from_user.id]['entry']['language'] = language
        USER_DATA[msg.from_user.id]['entry']['text'] = process_text(text)
    except g.PermissionDenied:
        print('SERVER ERROR, SWITCHING TO GOOGLE SPEECH API')
        USER_DATA[msg.from_user.id]['state'] = UserState.AUDIO_INPUT_LANGUAGE
        await msg.reply('Now enter the language of your voice message.', reply_markup=get_lan_kb)
    else:
        await db_controller.create_entry(user_id=msg.from_user.id, entry=USER_DATA[msg.from_user.id]['entry'])
        await msg.reply(f'Message stored: {USER_DATA[msg.from_user.id]["entry"]["date"]}', reply_markup=get_entries_kb)
        clear_user_data(uid=msg.from_user.id, user_data_ref=USER_DATA[msg.from_user.id])


async def convert_voice_message_using_gapi(msg: types.Message):
    filename = f'{msg.from_user.id}_{USER_DATA[msg.from_user.id]["entry"]["timestamp"]}'
    try:
        if not os.path.exists(f'{filename}.wav'):
            ogg_to_wav(filename)
        USER_DATA[msg.from_user.id]['entry']['text'] = process_text(
            recognize_google_api(f'{filename}.wav', language=USER_DATA[msg.from_user.id]['entry']['language'])
        )
        await db_controller.create_entry(user_id=msg.from_user.id, entry=USER_DATA[msg.from_user.id]['entry'])
    except (FileNotFoundError, PermissionError):
        print('SERVER ERROR')
        await msg.reply(f'An error has occurred. Please try again later.', reply_markup=get_entries_kb)
    else:
        await msg.reply(f'Message stored: {USER_DATA[msg.from_user.id]["entry"]["date"]}', reply_markup=get_entries_kb)
    finally:
        clear_user_data(uid=msg.from_user.id, user_data_ref=USER_DATA[msg.from_user.id])


async def print_entries(msg: types.Message, entries: list):
    if len(entries) == 0:
        await msg.reply('No entries found!', reply_markup=get_entries_kb, parse_mode=ParseMode.HTML)
    else:
        for entry in entries:
            await msg.reply(format_entry(entry=entry), reply_markup=get_entries_kb, parse_mode=ParseMode.HTML)


if __name__ == '__main__':
    executor.start_polling(dp)
