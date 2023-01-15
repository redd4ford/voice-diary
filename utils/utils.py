import datetime
import re
import subprocess
import time

from aiogram import types

from dateutil import parser


# DATE & TIME RELATED FUNCTIONS

class DateFormatter:
    DATE_STRING_DEFAULT_FORMAT = '%Y-%m-%d %H:%M:%S'

    @classmethod
    def get_current_date(cls) -> str:
        return datetime.datetime.now().strftime(cls.DATE_STRING_DEFAULT_FORMAT)

    @classmethod
    def timestamp_to_date(cls, timestamp: int) -> str:
        return datetime.datetime.fromtimestamp(timestamp).strftime(cls.DATE_STRING_DEFAULT_FORMAT)

    @classmethod
    def date_to_timestamp(cls, date: str) -> int:
        return int(datetime.datetime.strptime(date, cls.DATE_STRING_DEFAULT_FORMAT).timestamp())

    @classmethod
    def days_ago_date(cls, days: int, date=datetime.date.today()) -> str:
        return (date - datetime.timedelta(days=days)).strftime(cls.DATE_STRING_DEFAULT_FORMAT)

    @classmethod
    def days_ago_timestamp(cls, days: int, date=datetime.date.today()) -> int:
        if isinstance(date, str):
            date = parser.parse(date)
        return cls.date_to_timestamp(
            cls.days_ago_date(days=days, date=date)
        )

    @classmethod
    def get_current_timestamp(cls) -> str:
        return str(
            cls.date_to_timestamp(cls.get_current_date())
        )

    @classmethod
    def is_equal(cls, date1: str, date2: str) -> bool:
        return cls.date_to_timestamp(date1) == cls.date_to_timestamp(date2)

    @classmethod
    def min_timestamp(cls, date1: str, date2: str) -> int:
        return min(
            cls.date_to_timestamp(date1),
            cls.date_to_timestamp(date2)
        )

    @classmethod
    def max_timestamp(cls, date1: str, date2: str) -> int:
        return max(
            cls.date_to_timestamp(date1),
            cls.date_to_timestamp(date2)
        )

    @classmethod
    def add_time_to_datestamps(cls, datestamps: str) -> str:
        curr_timestamp_len = len(DateFormatter.get_current_timestamp())
        return (
                f'{datestamps[:curr_timestamp_len]} 00:00:00 '
                f'{datestamps[(curr_timestamp_len + 1):]} 23:59:59'
        )

    DATESTAMP_LEN_WITH_TIME = len('YEAR-MM-DD 00:00:00')   # 19
    DATESTAMP_LEN_WITHOUT_TIME = len('YEAR-MM-DD')   # 10
    LEN_TWO_DATESTAMPS_WITHOUT_TIME = DATESTAMP_LEN_WITHOUT_TIME * 2 + 1   # 21 (incl space symbol)
    LEN_TWO_DATESTAMPS_WITH_TIME = DATESTAMP_LEN_WITH_TIME * 2 + 1   # 39 (incl space symbol)

    @classmethod
    def split_datestamps_in_two_dates(cls, datestamps: str) -> tuple[str, str]:
        # datestamps = YYYY-MM-DD 00:00:00 YYYY-MM-DD 23:59:59
        return (
            datestamps[:DateFormatter.DATESTAMP_LEN_WITH_TIME],
            datestamps[(DateFormatter.DATESTAMP_LEN_WITH_TIME + 1):]   # omitting that space after the 1st datestamp
        )


# ENTRY DATA FORMATTING

class EntryFormatter:
    @classmethod
    def process_fetched(cls, fetched_data) -> list:
        return sorted(
            [entry.to_dict() for entry in fetched_data], key=lambda entry: entry['timestamp']
        )

    @classmethod
    def process_text(cls, text: str) -> str:
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

    @classmethod
    def format_entry(cls, entry: dict) -> str:
        language_flags = {'en-US': '🇺🇸', 'uk-UA': '🇺🇦'}
        entry_header = (
            f'{DateFormatter.timestamp_to_date(entry["timestamp"])} | '
            f'{language_flags[entry["language"]]} {entry["topic"]}'
        )
        text_len = len(re.findall(r'\w+', entry["text"]))
        line_len = int(len(entry_header) * 1.6)

        return (
            f'<b>{entry_header}</b>\n'
            f'{"-" * line_len}\n'
            f'<i>{text_len} words</i>\n\n'
            f'{entry["text"]}\n\n'
            f'🗑️ /d_{entry["timestamp"]}'
        )


def ogg_to_wav(filename: str):
    # convert ogg to wav using ffmpeg
    subprocess.Popen(
        ['ffmpeg', '-i', f'{filename}.ogg', f'{filename}.wav', '-loglevel', 'quiet'], shell=True
    )
    # wait before it updates the list of files
    time.sleep(0.5)


def user_id(msg: types.Message):
    return msg.from_user.id


class Commands:
    DELETE_REGEX = rf'^/d_(\d{len(DateFormatter.get_current_timestamp())})$'
