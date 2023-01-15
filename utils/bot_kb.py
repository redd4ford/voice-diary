from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
)


class Keyboards:
    GET_ENTRIES = (
        ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        .add(KeyboardButton('Get all the entries'))
        .row(
            KeyboardButton('by date'), KeyboardButton('by topic')
        )
        .add(KeyboardButton('last N entries'))
        .row(
            KeyboardButton('between two dates'), KeyboardButton('after date')
        )
    )

    GET_LANGUAGES = (
        ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        .row(
            KeyboardButton('🇺🇸 en-US'), KeyboardButton('🇺🇦 uk-UA')
        )
    )

    FREQUENTLY_USED_DATES = (
        ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        .add(KeyboardButton('Today'))
        .add(KeyboardButton('Yesterday'))
        .add(KeyboardButton('Past week'))
    )

    FREQUENTLY_USED_TOPICS = (
        ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        .add(KeyboardButton('None'))
    )
