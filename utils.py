import datetime
import re
import os
import subprocess
import time
from user_state import UserState

from dateutil import parser


# DATE & TIME RELATED FUNCTIONS

def get_current_date() -> str:
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def timestamp_to_date(timestamp: int) -> str:
    return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')


def date_to_timestamp(date: str) -> int:
    return int(datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S').timestamp())


def days_ago_date(days: int, date=datetime.date.today()) -> str:
    return (date - datetime.timedelta(days=days)).strftime('%Y-%m-%d 00:00:00')


def days_ago_timestamp(days: int, date=datetime.date.today()) -> int:
    if isinstance(date, str):
        date = parser.parse(date)
    return date_to_timestamp(days_ago_date(days=days, date=date))


def get_current_timestamp_len() -> int:
    return len(str(date_to_timestamp(get_current_date())))


def process_fetched(fetched_data) -> list:
    return sorted([entry.to_dict() for entry in fetched_data], key=lambda rec: rec['timestamp'])


def process_text(text: str) -> str:
    add_dots_indices = []
    for index, symbol in enumerate(text):
        if symbol == ' ' and text[index + 1].istitle() and text[index - 1] != '.':
            add_dots_indices.append(index)
    for arr_index, index in enumerate(add_dots_indices):
        text = text[:index] + '.' + text[index:]
        for i in range(arr_index, len(add_dots_indices)):
            add_dots_indices[i] += 1
    text[0].upper()
    text += '.'
    return text


def format_entry(entry: dict) -> str:
    language_flags = {'en-US': '🇺🇸', 'ru-RU': '🇷🇺', 'uk-UA': '🇺🇦'}
    entry_header = f'{timestamp_to_date(entry["timestamp"])} | {language_flags[entry["language"]]} {entry["topic"]}'
    text_len = len(re.findall(r'\w+', entry["text"]))
    line_len = int(len(entry_header) * 1.6)

    return f'<b>{entry_header}</b>\n' \
           f'{"-" * line_len}\n' \
           f'<i>{text_len} words</i>\n\n' \
           f'{entry["text"]}\n\n' \
           f'🗑️ /d_{entry["timestamp"]}'


def ogg_to_wav(filename: str):
    # convert ogg to wav using ffmpeg
    subprocess.Popen(['ffmpeg', '-i', f'{filename}.ogg', f'{filename}.wav', '-loglevel', 'quiet'], shell=True)
    # wait before it updates the list of files
    time.sleep(0.5)


def clear_user_data(uid: int, user_data_ref: dict):
    filename = f'{uid}_{user_data_ref["entry"]["timestamp"]}'
    os.remove(f'{filename}.ogg')
    os.remove(f'{filename}.wav')
    user_data_ref.pop('entry')
    user_data_ref['state'] = UserState.IDLE
