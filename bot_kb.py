from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


get_rec_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)\
    .add(KeyboardButton('Get all the recordings'))\
    .row(KeyboardButton('by date'), KeyboardButton('by topic'))\
    .add(KeyboardButton('last N recordings'))\
    .row(KeyboardButton('between two dates'), KeyboardButton('after date'))

get_lan_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)\
    .row(KeyboardButton('🇺🇸 en-US'), KeyboardButton('🇷🇺 ru-RU'), KeyboardButton('🇺🇦 uk-UA'))

freq_used_dates_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)\
    .add(KeyboardButton('Today')).add(KeyboardButton('Yesterday')).add(KeyboardButton('Past week'))

freq_used_topics_kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(KeyboardButton('None'))
