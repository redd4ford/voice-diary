import os
from collections import defaultdict

from dotenv import load_dotenv
from functools import wraps

import google.api_core.exceptions as google_api_exc
import google.auth.exceptions as google_auth_exc

from aiogram import types
from aiogram.bot import Bot
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor

from core import (
    Responder,
    FileController,
    UserState,
    UserController,
    DatabaseController,
    RecognitionController,
)
from utils import (
    DateFormatter,
    EntryFormatter,
    MessageTypes,
)


load_dotenv()

bot = Bot(token=os.getenv('TOKEN'))
dp = Dispatcher(bot)

db_controller = DatabaseController(
    project_id=os.environ.get('FIREBASE_PROJECT_ID'),
    private_key_id=os.environ.get('FIREBASE_PRIVATE_KEY_ID'),
    private_key=os.environ.get('FIREBASE_PRIVATE_KEY'),
    client_email=os.environ.get('FIREBASE_CLIENT_EMAIL'),
    client_id=os.environ.get('FIREBASE_CLIENT_ID'),
    cert_url=os.environ.get('FIREBASE_CLIENT_X509_CERT_URL')
)

USER_DATA = defaultdict(defaultdict)
user_controller = UserController(USER_DATA)


def use_state(func):
    @wraps(func)
    def out(*args, **kwargs):
        msg = args[0]
        uid = msg.from_user.id
        if not user_controller.is_registered(uid):
            user_controller.register(uid)
        return func(uid, *args, **kwargs)

    return out


@dp.message_handler(commands=MessageTypes.Commands.START)
@use_state
async def process_start_command(uid: int, msg: types.Message):
    await Responder.respond(msg, content=Responder.Types.START(uid))


@dp.message_handler(text=MessageTypes.GetEntriesKeyboardChoices.GET_ALL_ENTRIES)
@use_state
async def process_get_all(uid: int, msg: types.Message):
    if not user_controller.user(uid).is_state_in(UserState.AUDIO_STATES()):
        user_controller.user(uid).set_state(UserState.GET_ALL)

        entries = EntryFormatter.process_fetched(await db_controller.fetch_all(uid))
        await print_entries(msg, entries)

        user_controller.user(uid).set_state(UserState.IDLE)


@dp.message_handler(text=MessageTypes.GetEntriesKeyboardChoices.GET_ALL_ENTRIES_BY_DATE)
@use_state
async def process_get_by_date(uid: int, msg: types.Message):
    if not user_controller.user(uid).is_state_in(UserState.AUDIO_STATES()):
        user_controller.user(uid).set_state(
            UserState.GET_BY_DATE
            if msg.text == 'by date' else
            UserState.GET_ALL_AFTER
        )
        await Responder.respond(msg, content=Responder.Types.GET_ALL_ENTRIES_BY_DATE)


@dp.message_handler(text=MessageTypes.GetEntriesKeyboardChoices.GET_ALL_ENTRIES_BY_RECENT_DATE)
@use_state
async def process_get_date_kb(uid: int, msg: types.Message):
    if user_controller.user(uid).is_state_in(UserState.ONE_DATE_STATES()):
        datestamp = DateFormatter.days_ago_date(days=DateFormatter.count_days_since(msg.text))

        entries = EntryFormatter.process_fetched(
            await db_controller.fetch_by_date(uid, date=datestamp, is_exact=False)
            if user_controller.user(uid).is_state(UserState.GET_BY_DATE) else
            await db_controller.fetch_after_date(uid, date=datestamp)
        )
        await print_entries(msg, entries)
        user_controller.user(uid).set_state(UserState.IDLE)


@dp.message_handler(text=MessageTypes.GetEntriesKeyboardChoices.GET_ALL_BETWEEN_TWO_DATES)
@use_state
async def process_get_between(uid: int, msg: types.Message):
    if not user_controller.user(uid).is_state_in(UserState.AUDIO_STATES()):
        user_controller.user(uid).set_state(UserState.GET_ALL_BETWEEN)
        await Responder.respond(msg, content=Responder.Types.GET_ALL_ENTRIES_BETWEEN_TWO_DATES)


@dp.message_handler(regexp=MessageTypes.RegularExpressions.MATCH_DATE_WITH_OPTIONAL_TIME)
@use_state
async def process_get_date_input(uid: int, msg: types.Message):
    if not user_controller.user(uid).is_state_in(UserState.AUDIO_STATES()):
        datestamp = msg.text
        is_date_with_time, datestamp = DateFormatter.add_time_to_datestamp_if_needed(datestamp)
        if user_controller.user(uid).is_state(UserState.GET_BY_DATE):
            entries = EntryFormatter.process_fetched(
                await db_controller.fetch_by_date(
                    uid, date=datestamp, is_exact=is_date_with_time
                )
            )
            await print_entries(msg, entries)
            user_controller.user(uid).set_state(UserState.IDLE)
        elif user_controller.user(uid).is_state(UserState.GET_ALL_AFTER):
            entries = EntryFormatter.process_fetched(
                await db_controller.fetch_after_date(uid, date=datestamp)
            )
            await print_entries(msg, entries)
            user_controller.user(uid).set_state(UserState.IDLE)


@dp.message_handler(regexp=MessageTypes.RegularExpressions.MATCH_TWO_DATES_WITH_OPTIONAL_TIME)
@use_state
async def process_get_between_input(uid: int, msg: types.Message):
    if all([
        not user_controller.user(uid).is_state_in(UserState.AUDIO_STATES()),
        user_controller.user(uid).is_state(UserState.GET_ALL_BETWEEN)
    ]):
        datestamps = msg.text

        if len(datestamps) == DateFormatter.LEN_TWO_DATESTAMPS_WITHOUT_TIME:
            datestamps = DateFormatter.add_time_to_datestamps(datestamps)

        if len(datestamps) == DateFormatter.LEN_TWO_DATESTAMPS_WITH_TIME:
            date1, date2 = DateFormatter.split_datestamps_in_two_dates(datestamps)

            entries = EntryFormatter.process_fetched(
                await db_controller.fetch_between_dates(uid, date1, date2)
            )
            await print_entries(msg, entries)
            user_controller.user(uid).set_state(UserState.IDLE)


@dp.message_handler(text=MessageTypes.GetEntriesKeyboardChoices.GET_LAST_N_ENTRIES)
@use_state
async def process_get_last_n_command(uid: int, msg: types.Message):
    if not user_controller.user(uid).is_state_in(UserState.AUDIO_STATES()):
        user_controller.user(uid).set_state(UserState.GET_LAST_N)
        await Responder.respond(msg, content=Responder.Types.GET_LAST_N_ENTRIES)


@dp.message_handler(regexp=MessageTypes.RegularExpressions.MATCH_NUMBER)
@use_state
async def process_number_of_entries_to_get_input(uid: int, msg: types.Message):
    if user_controller.user(uid).is_state(UserState.GET_LAST_N):
        entries = EntryFormatter.process_fetched(
            await db_controller.fetch_last_n(uid, number=int(msg.text))
        )
        await print_entries(msg, entries)
        user_controller.user(uid).set_state(UserState.IDLE)


@dp.message_handler(text=MessageTypes.GetEntriesKeyboardChoices.GET_ALL_ENTRIES_BY_TOPIC)
@use_state
async def process_get_by_topic_command(uid: int, msg: types.Message):
    if not user_controller.user(uid).is_state_in(UserState.AUDIO_STATES()):
        user_controller.user(uid).set_state(UserState.GET_BY_TOPIC)
        await Responder.respond(msg, content=Responder.Types.GET_ALL_ENTRIES_BY_TOPIC)


@dp.message_handler(regexp=MessageTypes.RegularExpressions.MATCH_ANY_TEXT)
@use_state
async def process_get_text_input(uid: int, msg: types.Message):
    delete_command = MessageTypes.get_delete_command(msg.text)

    if user_controller.user(uid).is_state(UserState.GET_BY_TOPIC):
        entries = EntryFormatter.process_fetched(
            await db_controller.fetch_by_topic(uid, topic=msg.text)
        )
        await print_entries(msg, entries)
        user_controller.user(uid).set_state(UserState.IDLE)

    elif user_controller.user(uid).is_state(UserState.AUDIO_INPUT_TOPIC):
        user_controller.user(uid).cache_entry_data(topic=msg.text)
        # try auto-detecting the language with Speech-To-Text
        user_controller.user(uid).set_state(UserState.AUDIO_AUTO_LANGUAGE)
        await convert_voice_message_using_s2t(uid, msg)

    elif user_controller.user(uid).is_state(UserState.AUDIO_INPUT_LANGUAGE):
        # buttons also contain flag emojis, so we need to remove them from msg.text
        user_controller.user(uid).cache_entry_data(language=msg.text[3:])
        user_controller.user(uid).set_state(UserState.AUDIO_PROCESSING)
        await convert_voice_message_using_gapi(uid, msg)

    elif user_controller.user(uid).is_state(UserState.IDLE) and delete_command:
        timestamp = int(delete_command.group(1))
        eid = await db_controller.delete_entry(uid, timestamp=timestamp)
        await Responder.respond(msg, content=Responder.Types.REMOVE_ENTRY_SUCCESS(eid))


@dp.message_handler(content_types=MessageTypes.ContentTypes.VOICE)
@use_state
async def process_voice_message(uid: int, msg: types.Message):
    if not user_controller.user(uid).is_state_in(UserState.AUDIO_STATES()):
        datestamp = DateFormatter.get_current_date()
        timestamp = DateFormatter.date_to_timestamp(datestamp)
        user_controller.user(uid).cache_entry_data(
            date=datestamp, timestamp=timestamp, topic='None'
        )

        voice_message = await bot.get_file(msg.voice.file_id)
        await bot.download_file(voice_message.file_path, f'{msg.chat.id}_{timestamp}.ogg')

        user_controller.user(uid).set_state(UserState.AUDIO_INPUT_TOPIC)
        await Responder.respond(msg, content=Responder.Types.CHOOSE_TOPIC_FOR_NEW_ENTRY)


async def convert_voice_message_using_s2t(uid: int, msg: types.Message):
    try:
        filename = FileController.convert_ogg_to_wav(
            filename=user_controller.user(uid).voice_message_filename
        )
        speech_recognizer = RecognitionController.strategy(recognition_type='s2t')
        language, text = speech_recognizer.recognize(f'{filename}.wav')

        user_controller.user(uid).cache_entry_data(
            language=language, text=EntryFormatter.process_text(text)
        )
    except (google_api_exc.PermissionDenied, google_auth_exc.MalformedError):
        # switching to Google Speech API
        user_controller.user(uid).set_state(UserState.AUDIO_INPUT_LANGUAGE)
        await Responder.respond(msg, content=Responder.Types.CHOOSE_LANGUAGE_FOR_NEW_ENTRY)
    else:
        if len(text):
            eid = await db_controller.create_entry(uid, user_controller.user(uid).current_entry)
            await Responder.respond(msg, content=Responder.Types.CREATE_ENTRY_SUCCESS(eid))
        else:
            await Responder.respond(msg, content=Responder.Types.TEXT_NOT_RECOGNIZED)
        user_controller.user(uid).clear_cache()


async def convert_voice_message_using_gapi(uid: int, msg: types.Message):
    try:
        filename = FileController.convert_ogg_to_wav(
            filename=user_controller.user(uid).voice_message_filename
        )
        speech_recognizer = RecognitionController.strategy(recognition_type='gapi')
        selected_language = user_controller.user(uid).current_entry.language
        text = speech_recognizer.recognize(f'{filename}.wav', selected_language)

        user_controller.user(uid).cache_entry_data(text=EntryFormatter.process_text(text))
    except (FileNotFoundError, PermissionError):
        await Responder.respond(msg, content=Responder.Types.ERROR)
    else:
        if len(text):
            eid = await db_controller.create_entry(uid, user_controller.user(uid).current_entry)
            await Responder.respond(msg, content=Responder.Types.CREATE_ENTRY_SUCCESS(eid))
        else:
            await Responder.respond(msg, content=Responder.Types.TEXT_NOT_RECOGNIZED)
    finally:
        user_controller.user(uid).clear_cache()


async def print_entries(msg: types.Message, entries: list):
    if len(entries):
        for entry in entries:
            formatted = EntryFormatter.format_entry(entry=entry)
            await Responder.respond(msg, content=Responder.Types.PRINT_ENTRY(formatted))
    else:
        await Responder.respond(msg, content=Responder.Types.ENTRIES_NOT_FOUND)


if __name__ == '__main__':
    executor.start_polling(dp)
