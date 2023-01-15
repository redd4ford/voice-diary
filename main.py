import os
import re
from collections import defaultdict
from dotenv import load_dotenv
from functools import wraps

import google.api_core.exceptions as google_api_exceptions
from aiogram import (
    Bot,
    types,
)
from aiogram.dispatcher import Dispatcher
from aiogram.types import ParseMode
from aiogram.utils import executor

from core import (
    DatabaseController,
    SpeechToTextApiRecognitionController,
    GoogleApiRecognitionController,
    UserState,
    UserController,
)
from utils import (
    Keyboards,
    DateFormatter,
    EntryFormatter,
    ogg_to_wav,
    user_id,
    Commands,
)


load_dotenv()

bot = Bot(token=os.getenv('TOKEN'))
dp = Dispatcher(bot)

db_controller = DatabaseController()

USER_DATA = defaultdict(defaultdict)
user_controller = UserController(USER_DATA)


def use_state(func):
    @wraps(func)
    def out(*args, **kwargs):
        msg = args[0]
        if not user_controller.is_registered(msg):
            user_controller.register(msg)
        return func(*args, **kwargs)

    return out


@dp.message_handler(commands=['start'])
@use_state
async def process_start_command(msg: types.Message):
    await msg.reply(
        'Hello there!\nI can recognize phrases from your voice messages, convert them to txt, '
        'and store in Firestore DB. Send me a voice message to start. I support messages in '
        '<b>English</b> and <b>Ukrainian.</b>',
        reply_markup=Keyboards.GET_ENTRIES, parse_mode=ParseMode.HTML
    )


@dp.message_handler(text=['Get all the entries'])
@use_state
async def process_get_all(msg: types.Message):
    if not user_controller.user(msg).is_state_in(UserState.audio_states()):
        user_controller.user(msg).set_state(UserState.GET_ALL)

        entries = EntryFormatter.process_fetched(await db_controller.fetch_all(user_id(msg)))
        await print_entries(msg, entries)

        user_controller.user(msg).set_state(UserState.IDLE)


@dp.message_handler(text=['by date', 'after date'])
@use_state
async def process_get_by_date(msg: types.Message):
    if not user_controller.user(msg).is_state_in(UserState.audio_states()):
        user_controller.user(msg).set_state(
            UserState.GET_BY_DATE
            if msg.text == 'by date' else
            UserState.GET_ALL_AFTER
        )
        await msg.reply(
            'Send me a date in format <b>YYYY-mm-dd HH:MM:SS</b> or just <b>YYYY-mm-dd</b>.',
            reply_markup=Keyboards.FREQUENTLY_USED_DATES, parse_mode=ParseMode.HTML
        )


@dp.message_handler(text=['Today', 'Yesterday', 'Past week'])
@use_state
async def process_get_date_kb(msg: types.Message):
    if user_controller.user(msg).is_state_in(UserState.date_states_single()):
        days_since = {'Today': 0, 'Yesterday': 1, 'Past week': 7}
        datestamp = DateFormatter.days_ago_date(days=days_since[msg.text])

        entries = EntryFormatter.process_fetched(
            await db_controller.fetch_by_date(user_id(msg), date=datestamp, is_exact=False)
            if user_controller.user(msg).is_state(UserState.GET_BY_DATE) else
            await db_controller.fetch_after_date(user_id(msg), date=datestamp)
        )
        await print_entries(msg, entries)
        user_controller.user(msg).set_state(UserState.IDLE)


@dp.message_handler(text=['between two dates'])
@use_state
async def process_get_between(msg: types.Message):
    if not user_controller.user(msg).is_state_in(UserState.audio_states()):
        user_controller.user(msg).set_state(UserState.GET_ALL_BETWEEN)
        await msg.reply(
            'Send me two dates separated by space in format <b>YYYY-mm-dd HH:MM:SS YYYY-mm-dd '
            'HH:MM:SS</b> or just <b>YYYY-mm-dd YYYY-mm-dd</b>.',
            parse_mode=ParseMode.HTML
        )


@dp.message_handler(regexp=r'^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$')
@use_state
async def process_get_date_input(msg: types.Message):
    if not user_controller.user(msg).is_state_in(UserState.audio_states()):
        datestamp = msg.text
        if user_controller.user(msg).is_state(UserState.GET_BY_DATE):
            # there are only two acceptable cases: either it's just a date or it's a date plus time
            is_date_without_time = True
            if len(datestamp) == DateFormatter.DATESTAMP_LEN_WITHOUT_TIME:
                datestamp = f'{datestamp} 00:00:00'
                is_date_without_time = False
            entries = EntryFormatter.process_fetched(
                await db_controller.fetch_by_date(
                    user_id(msg), date=datestamp, is_exact=is_date_without_time
                )
            )
            await print_entries(msg, entries)
            user_controller.user(msg).set_state(UserState.IDLE)
        elif user_controller.user(msg).is_state(UserState.GET_ALL_AFTER):
            if len(datestamp) == DateFormatter.DATESTAMP_LEN_WITHOUT_TIME:
                datestamp = f'{datestamp} 00:00:00'
            if len(datestamp) == DateFormatter.DATESTAMP_LEN_WITH_TIME:
                entries = EntryFormatter.process_fetched(
                    await db_controller.fetch_after_date(user_id(msg), date=datestamp)
                )
                await print_entries(msg, entries)
            user_controller.user(msg).set_state(UserState.IDLE)


@dp.message_handler(regexp=r'^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})? \d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$')
@use_state
async def process_get_between_input(msg: types.Message):

    if all([
        not user_controller.user(msg).is_state_in(UserState.audio_states()),
        user_controller.user(msg).is_state(UserState.GET_ALL_BETWEEN)
    ]):
        datestamps = msg.text

        if len(datestamps) == DateFormatter.LEN_TWO_DATESTAMPS_WITHOUT_TIME:
            datestamps = DateFormatter.add_time_to_datestamps(datestamps)

        if len(datestamps) == DateFormatter.LEN_TWO_DATESTAMPS_WITH_TIME:
            date1, date2 = DateFormatter.split_datestamps_in_two_dates(datestamps)

            entries = EntryFormatter.process_fetched(
                await db_controller.fetch_between_dates(user_id(msg), date1, date2)
            )
            await print_entries(msg, entries)
            user_controller.user(msg).set_state(UserState.IDLE)


@dp.message_handler(text=['last N entries'])
@use_state
async def process_get_last_n_command(msg: types.Message):
    if not user_controller.user(msg).is_state_in(UserState.audio_states()):
        user_controller.user(msg).set_state(UserState.GET_LAST_N)
        await msg.reply('Send me a number of entries you want to get.')


@dp.message_handler(regexp=r'^\d+$')
@use_state
async def process_get_number_input(msg: types.Message):
    if user_controller.user(msg).is_state(UserState.GET_LAST_N):
        entries = EntryFormatter.process_fetched(
            await db_controller.fetch_last_n(user_id(msg), number=int(msg.text))
        )
        await print_entries(msg, entries)
        user_controller.user(msg).set_state(UserState.IDLE)


@dp.message_handler(text=['by topic'])
@use_state
async def process_get_by_topic_command(msg: types.Message):
    if not user_controller.user(msg).is_state_in(UserState.audio_states()):
        user_controller.user(msg).set_state(UserState.GET_BY_TOPIC)
        await msg.reply(
            'Send me a topic name to search for.',
            reply_markup=Keyboards.FREQUENTLY_USED_TOPICS
        )


@dp.message_handler(regexp=r'^.*$')
@use_state
async def process_get_text_input(msg: types.Message):
    delete_command = re.search(Commands.DELETE_REGEX, msg.text)

    if user_controller.user(msg).is_state(UserState.GET_BY_TOPIC):
        entries = EntryFormatter.process_fetched(
            await db_controller.fetch_by_topic(user_id(msg), topic=msg.text)
        )
        await print_entries(msg, entries)
        user_controller.user(msg).set_state(UserState.IDLE)

    elif user_controller.user(msg).is_state(UserState.AUDIO_INPUT_TOPIC):
        user_controller.user(msg).cache_entry_data(topic=msg.text)

        # try auto-detecting the language with Speech-To-Text
        user_controller.user(msg).set_state(UserState.AUDIO_AUTO_LANGUAGE)
        await convert_voice_message_using_s2t(msg)

    elif user_controller.user(msg).is_state(UserState.AUDIO_INPUT_LANGUAGE):
        # buttons also contain flag emojis, so we need to remove them from msg.text
        user_controller.user(msg).cache_entry_data(language=msg.text[3:])
        user_controller.user(msg).set_state(UserState.AUDIO_PROCESSING)
        await convert_voice_message_using_gapi(msg)

    elif user_controller.user(msg).is_state(UserState.IDLE) and delete_command:
        timestamp = int(delete_command.group(1))
        await db_controller.delete_entry(user_id(msg), timestamp=timestamp)
        await msg.reply(
            f'Successfully removed the entry: <b>{DateFormatter.timestamp_to_date(timestamp=timestamp)}</b>',
            reply_markup=Keyboards.FREQUENTLY_USED_TOPICS, parse_mode=ParseMode.HTML
        )


@dp.message_handler(content_types=['voice'])
@use_state
async def process_voice_message(msg: types.Message):
    if not user_controller.user(msg).is_state_in(UserState.audio_states()):
        datestamp = DateFormatter.get_current_date()
        timestamp = DateFormatter.date_to_timestamp(datestamp)
        user_controller.user(msg).cache_entry_data(date=datestamp, timestamp=timestamp, topic='None')

        voice_message = await bot.get_file(msg.voice.file_id)
        await bot.download_file(voice_message.file_path, f'{msg.chat.id}_{timestamp}.ogg')

        user_controller.user(msg).set_state(UserState.AUDIO_INPUT_TOPIC)
        await msg.reply(
            f'Please choose the topic for this entry.',
            reply_markup=Keyboards.FREQUENTLY_USED_TOPICS
        )


async def convert_voice_message_using_s2t(msg: types.Message):
    filename = user_controller.user(msg).get_voice_message_filename()
    try:
        ogg_to_wav(filename)
        language, text = (
            SpeechToTextApiRecognitionController().recognize(f'{filename}.wav')
        )
        user_controller.user(msg).cache_entry_data(
            language=language, text=EntryFormatter.process_text(text)
        )
    except google_api_exceptions.PermissionDenied:
        print('SERVER ERROR, SWITCHING TO GOOGLE SPEECH API')
        user_controller.user(msg).set_state(UserState.AUDIO_INPUT_LANGUAGE)
        await msg.reply(
            'Now enter the language of your voice message.',
            reply_markup=Keyboards.GET_LANGUAGES
        )
    else:
        await db_controller.create_entry(user_id(msg), entry=user_controller.user(msg).current_entry)
        await msg.reply(
            f'Message stored: {user_controller.user(msg).current_entry.date}',
            reply_markup=Keyboards.GET_ENTRIES
        )
        user_controller.user(msg).clear_cache()


async def convert_voice_message_using_gapi(msg: types.Message):
    filename = user_controller.user(msg).get_voice_message_filename()
    try:
        if not os.path.exists(f'{filename}.wav'):
            ogg_to_wav(filename)
        text = GoogleApiRecognitionController().recognize(
            f'{filename}.wav', language=user_controller.user(msg).current_entry.language
        )
        user_controller.user(msg).cache_entry_data(text=EntryFormatter.process_text(text))
        await db_controller.create_entry(user_id(msg), entry=user_controller.user(msg).current_entry)
    except (FileNotFoundError, PermissionError):
        print('SERVER ERROR')
        await msg.reply(
            f'An error has occurred. Please try again later.',
            reply_markup=Keyboards.GET_ENTRIES
        )
    else:
        await msg.reply(
            f'Message stored: {user_controller.user(msg).current_entry.date}',
            reply_markup=Keyboards.GET_ENTRIES
        )
    finally:
        user_controller.user(msg).clear_cache()


async def print_entries(msg: types.Message, entries: list):
    if len(entries) == 0:
        await msg.reply(
            'No entries found!',
            reply_markup=Keyboards.GET_ENTRIES, parse_mode=ParseMode.HTML
        )
    else:
        for entry in entries:
            await msg.reply(
                EntryFormatter.format_entry(entry=entry),
                reply_markup=Keyboards.GET_ENTRIES, parse_mode=ParseMode.HTML
            )


if __name__ == '__main__':
    executor.start_polling(dp)
