import os
import re
import subprocess
import time
from collections import defaultdict

from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.types import ParseMode
from aiogram.utils import executor

import db_controller
from user_state import UserState
from bot_kb import get_rec_kb, get_lan_kb, freq_used_topics_kb, freq_used_dates_kb
from recognize_controller import recognize_phrase
from utils import days_ago_date, get_current_date, date_to_timestamp, timestamp_to_date, process_fetched, \
    process_text, format_recording

TOKEN = 'TOKEN'

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)


USER_DATA = defaultdict(defaultdict)
AUDIO_STATES = [UserState.AUDIO_INPUT_TOPIC, UserState.AUDIO_INPUT_LANGUAGE, UserState.AUDIO_PROCESSING]


@dp.message_handler(commands=['start'])
async def process_start_command(msg: types.Message):
    if 'state' not in USER_DATA[msg.from_user.id].keys():
        USER_DATA[msg.from_user.id]['state'] = UserState.IDLE
    await msg.reply('Hello there!\nI can recognize phrases from your voice messages, convert them to txt, '
                    'and store in Firestore DB. Send me a voice message to start. I support messages in '
                    '<b>English</b>, <b>Russian</b>, and <b>Ukrainian.</b>',
                    reply_markup=get_rec_kb, parse_mode=ParseMode.HTML)


@dp.message_handler(text=['Get all the recordings'])
async def process_get_all(msg: types.Message):
    if 'state' not in USER_DATA[msg.from_user.id].keys():
        USER_DATA[msg.from_user.id]['state'] = UserState.IDLE
    if USER_DATA[msg.from_user.id]['state'] not in AUDIO_STATES:
        USER_DATA[msg.from_user.id]['state'] = UserState.GET_ALL
        recordings = process_fetched(await db_controller.fetch_all(user_id=msg.from_user.id))
        for recording in recordings:
            await msg.reply(format_recording(recording=recording), reply_markup=get_rec_kb, parse_mode=ParseMode.HTML)
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
        cases = {'Today': 0, 'Yesterday': 1, 'Past week': 7}
        datestamp = days_ago_date(days=cases[msg.text])
        recordings = process_fetched(
            await db_controller.fetch_by_date(user_id=msg.from_user.id, date=datestamp, is_exact=False)
            if USER_DATA[msg.from_user.id]['state'] == UserState.GET_BY_DATE else
            await db_controller.fetch_after(user_id=msg.from_user.id, date=datestamp)
        )
        for recording in recordings:
            await msg.reply(format_recording(recording=recording), reply_markup=get_rec_kb, parse_mode=ParseMode.HTML)
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
        # there are only two acceptable cases: either it's just a date or it's a date plus time
        len_with_time = 19
        len_without_time = 10
        datestamp = msg.text
        if USER_DATA[msg.from_user.id]['state'] == UserState.GET_BY_DATE:
            is_exact = True
            if len(datestamp) == len_without_time:
                datestamp += ' ' + '00:00:00'
                is_exact = False
            recordings = process_fetched(
                await db_controller.fetch_by_date(user_id=msg.from_user.id, date=datestamp, is_exact=is_exact)
            )
            for recording in recordings:
                await msg.reply(format_recording(recording=recording),
                                reply_markup=get_rec_kb, parse_mode=ParseMode.HTML)
            USER_DATA[msg.from_user.id]['state'] = UserState.IDLE
        elif USER_DATA[msg.from_user.id]['state'] == UserState.GET_ALL_AFTER:
            if len(datestamp) == len_without_time:
                datestamp += ' ' + '00:00:00'
            if len(datestamp) == len_with_time:
                recordings = process_fetched(await db_controller.fetch_after(user_id=msg.from_user.id, date=datestamp))
                for recording in recordings:
                    await msg.reply(format_recording(recording=recording),
                                    reply_markup=get_rec_kb, parse_mode=ParseMode.HTML)
            USER_DATA[msg.from_user.id]['state'] = UserState.IDLE


@dp.message_handler(regexp=r'^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})? \d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$')
async def process_get_between_input(msg: types.Message):
    if 'state' not in USER_DATA[msg.from_user.id].keys():
        USER_DATA[msg.from_user.id]['state'] = UserState.IDLE
    if USER_DATA[msg.from_user.id]['state'] not in AUDIO_STATES:
        len_with_time = 39
        len_without_time = 21
        if USER_DATA[msg.from_user.id]['state'] == UserState.GET_ALL_BETWEEN:
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
                for recording in recordings:
                    await msg.reply(format_recording(recording=recording),
                                    reply_markup=get_rec_kb, parse_mode=ParseMode.HTML)
                USER_DATA[msg.from_user.id]['state'] = UserState.IDLE


@dp.message_handler(text=['last N recordings'])
async def process_get_last_n_command(msg: types.Message):
    if 'state' not in USER_DATA[msg.from_user.id].keys():
        USER_DATA[msg.from_user.id]['state'] = UserState.IDLE
    if USER_DATA[msg.from_user.id]['state'] not in AUDIO_STATES:
        USER_DATA[msg.from_user.id]['state'] = UserState.GET_LAST_N
        await msg.reply('Send me a number of recordings you want to get.')


@dp.message_handler(regexp=r'^\d+$')
async def process_get_number_input(msg: types.Message):
    if 'state' not in USER_DATA[msg.from_user.id].keys():
        USER_DATA[msg.from_user.id]['state'] = UserState.IDLE
    if USER_DATA[msg.from_user.id]['state'] == UserState.GET_LAST_N:
        recordings = process_fetched(await db_controller.fetch_last_n(user_id=msg.from_user.id, number=int(msg.text)))
        for recording in recordings:
            await msg.reply(format_recording(recording=recording), reply_markup=get_rec_kb, parse_mode=ParseMode.HTML)
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
    command = re.search(r'^/d_(\d{10})$', msg.text)   # /d command regex

    if USER_DATA[msg.from_user.id]['state'] == UserState.GET_BY_TOPIC:
        recordings = process_fetched(await db_controller.fetch_by_topic(user_id=msg.from_user.id, topic=msg.text))
        for recording in recordings:
            await msg.reply(format_recording(recording=recording), reply_markup=get_rec_kb, parse_mode=ParseMode.HTML)
        USER_DATA[msg.from_user.id]['state'] = UserState.IDLE

    elif USER_DATA[msg.from_user.id]['state'] == UserState.AUDIO_INPUT_TOPIC:
        USER_DATA[msg.from_user.id]['recording']['topic'] = msg.text
        USER_DATA[msg.from_user.id]['state'] = UserState.AUDIO_INPUT_LANGUAGE
        await msg.reply('Now enter the language of your voice message.', reply_markup=get_lan_kb)

    elif USER_DATA[msg.from_user.id]['state'] == UserState.AUDIO_INPUT_LANGUAGE:
        # buttons also contain flag emojis, so we need to remove them from msg.text
        USER_DATA[msg.from_user.id]['recording']['language'] = msg.text[3:]
        USER_DATA[msg.from_user.id]['state'] = UserState.AUDIO_PROCESSING
        await convert_voice_message(msg)

    elif USER_DATA[msg.from_user.id]['state'] == UserState.IDLE and command:
        timestamp = int(command.group(1))
        await db_controller.delete_recording(user_id=msg.from_user.id, timestamp=timestamp)
        await msg.reply(f'Successfully removed the recording: <b>{timestamp_to_date(timestamp=timestamp)}</b>',
                        reply_markup=freq_used_topics_kb, parse_mode=ParseMode.HTML)


@dp.message_handler(content_types=['voice'])
async def process_voice_message(msg: types.Message):
    if 'state' not in USER_DATA[msg.from_user.id].keys():
        USER_DATA[msg.from_user.id]['state'] = UserState.IDLE
    if USER_DATA[msg.from_user.id]['state'] not in AUDIO_STATES:
        datestamp = get_current_date()
        timestamp = date_to_timestamp(datestamp)
        USER_DATA[msg.from_user.id]['recording'] = {'date': datestamp, 'timestamp': timestamp, 'topic': 'None'}

        voice_message = await bot.get_file(msg.voice.file_id)
        await bot.download_file(voice_message.file_path, f'{msg.chat.id}_{timestamp}.ogg')

        USER_DATA[msg.from_user.id]['state'] = UserState.AUDIO_INPUT_TOPIC
        await msg.reply(f'Please enter the topic for this recording.', reply_markup=freq_used_topics_kb)


async def convert_voice_message(msg: types.Message):
    filename = f'{msg.from_user.id}_{USER_DATA[msg.from_user.id]["recording"]["timestamp"]}'
    try:
        # convert ogg to wav using ffmpeg
        subprocess.Popen(['ffmpeg', '-i', f'{filename}.ogg', f'{filename}.wav'], shell=True)
        # wait before it updates the list of files
        time.sleep(0.5)
        USER_DATA[msg.from_user.id]['recording']['text'] = process_text(
            recognize_phrase(f'{filename}.wav', language=USER_DATA[msg.from_user.id]['recording']['language'])
        )
        await db_controller.create_recording(user_id=msg.from_user.id,
                                             recording=USER_DATA[msg.from_user.id]['recording'])
    except FileNotFoundError:
        print('SERVER ERROR')
    else:
        await msg.reply(f'Message stored: {USER_DATA[msg.from_user.id]["recording"]["date"]}', reply_markup=get_rec_kb)
    finally:
        os.remove(f'{filename}.ogg')
        os.remove(f'{filename}.wav')
        print(USER_DATA)
        USER_DATA[msg.from_user.id].pop('recording')
        USER_DATA[msg.from_user.id]['state'] = UserState.IDLE


if __name__ == '__main__':
    executor.start_polling(dp)
