from typing import Optional

from aiogram import types

from utils import Keyboards


class Responder:
    class Types:
        GET_ALL_ENTRIES_BY_DATE = dict(
            message='Send me a date in format: <b>YYYY-mm-dd HH:MM:SS</b> or just '
                    '<b>YYYY-mm-dd</b>.',
            kb=Keyboards.FREQUENTLY_USED_DATES,
            html=True,
        )
        GET_ALL_ENTRIES_BETWEEN_TWO_DATES = dict(
            message='Send me two dates separated by space in format: '
                    '<b>YYYY-mm-dd HH:MM:SS YYYY-mm-dd HH:MM:SS</b> or just '
                    '<b>YYYY-mm-dd YYYY-mm-dd</b>.',
            html=True,
        )
        GET_LAST_N_ENTRIES = dict(
            message='Send me a number of entries you want to get.',
        )
        GET_ALL_ENTRIES_BY_TOPIC = dict(
            message='Send me a topic name to search for.',
            kb=Keyboards.FREQUENTLY_USED_TOPICS,
        )
        CHOOSE_TOPIC_FOR_NEW_ENTRY = dict(
            message='Please select the topic for this entry.',
            kb=Keyboards.FREQUENTLY_USED_TOPICS,
        )
        CHOOSE_LANGUAGE_FOR_NEW_ENTRY = dict(
            message='Now select the language of your voice message.',
            kb=Keyboards.GET_LANGUAGES,
        )
        ERROR = dict(
            message='An error has occurred. Please try again later.',
            kb=Keyboards.GET_ENTRIES,
        )
        TEXT_NOT_RECOGNIZED = dict(
            message='Unable to process your voice message. Try re-recording it.',
            kb=Keyboards.GET_ENTRIES,
        )
        ENTRIES_NOT_FOUND = dict(
            message='No entries found!',
            kb=Keyboards.GET_ENTRIES,
            html=True
        )

        @classmethod
        def START(cls, user_id: int) -> dict:   # NOSONAR
            return dict(
                message='Hello there!\n'
                        'I can recognize phrases from your voice messages, convert them to text, '
                        'and store in Firestore DB. Send me a voice message to start.\n'
                        f'Your voice messages will be downloaded for processing and will be '
                        f'deleted right after they are stored in the DB. I also use your '
                        f'Telegram ID: {user_id} to separate you from the other users.\n\n'
                        'I support messages in <b>English</b> 🇺🇸 and <b>Ukrainian</b> 🇺🇦',
                kb=Keyboards.GET_ENTRIES,
                html=True,
            )

        @classmethod
        def REMOVE_ENTRY_SUCCESS(cls, entry_id: str) -> dict:   # NOSONAR
            return dict(
                message=f'Successfully removed the entry: <b>{entry_id}</b>',
                kb=Keyboards.FREQUENTLY_USED_TOPICS,
                html=True,
            )

        @classmethod
        def CREATE_ENTRY_SUCCESS(cls, entry_id: str) -> dict:   # NOSONAR
            return dict(
                message=f'Message stored: <b>{entry_id}</b>',
                kb=Keyboards.GET_ENTRIES,
                html=True,
            )

        @classmethod
        def PRINT_ENTRY(cls, entry: str) -> dict:   # NOSONAR
            return dict(
                message=entry,
                kb=Keyboards.GET_ENTRIES,
                html=True,
            )

    @classmethod
    def __get_content(cls, content: dict) -> (
        Optional[str], Optional[types.ReplyKeyboardMarkup], Optional[types.ParseMode]
    ):
        return (
            content.get('message', None),
            content.get('kb', None),
            types.ParseMode.HTML if content.get('html', False) else None
        )

    @classmethod
    async def respond(cls, msg: types.Message, content: dict):
        message, keyboard, parse_mode = cls.__get_content(content)
        await msg.reply(message, reply_markup=keyboard, parse_mode=parse_mode)
