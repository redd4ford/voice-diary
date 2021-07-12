import datetime
import re
import subprocess
import time

from dateutil import parser


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


def process_fetched(fetched_data) -> list:
    return sorted([recording.to_dict() for recording in fetched_data], key=lambda rec: rec['timestamp'])


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


def format_recording(recording: dict) -> str:
    language_flags = {'en-US': '🇺🇸', 'ru-RU': '🇷🇺', 'uk-UA': '🇺🇦'}
    recording_header = f'{timestamp_to_date(recording["timestamp"])} | ' \
                       f'{language_flags[recording["language"]]} {recording["topic"]}'
    text_len = len(re.findall(r'\w+', recording["text"]))
    line_len = int(len(recording_header) * 1.6)

    return f'<b>{recording_header}</b>\n' \
           f'{"-" * line_len}\n' \
           f'<i>{text_len} words</i>\n\n' \
           f'{recording["text"]}\n\n' \
           f'🗑️ /d_{recording["timestamp"]}'


def ogg_to_wav(filename: str):
    # convert ogg to wav using ffmpeg
    subprocess.Popen(['ffmpeg', '-i', f'{filename}.ogg', f'{filename}.wav', '-loglevel', 'quiet'], shell=True)
    # wait before it updates the list of files
    time.sleep(0.5)
