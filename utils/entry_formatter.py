import re

from utils import DateFormatter


class EntryFormatter:
    @classmethod
    def process_fetched(cls, fetched_data) -> list:
        if not isinstance(fetched_data, list):
            fetched_data = [fetched_data]
        try:
            return sorted(
                [entry.to_dict() for entry in fetched_data],
                key=lambda entry: entry['timestamp']
            )
        except TypeError:
            return []

    @classmethod
    def process_text(cls, text: str) -> str:
        if len(text):
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
        text_len = len(re.findall(r'\w+', entry['text']))
        line_len = int(len(entry_header) * 1.6)

        return (
            f'<b>{entry_header}</b>\n'
            f'{"-" * line_len}\n'
            f'<i>{text_len} words</i>\n\n'
            f'{entry["text"]}\n\n'
            f'🗑️ /d_{entry["timestamp"]}'
        )
