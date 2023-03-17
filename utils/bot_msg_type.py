import re

from utils import DateFormatter


class MessageTypes:
    class RegularExpressions:
        # this matches `YYYY-MM-DD` and `YYYY-MM-DD HH:MM:SS`
        MATCH_DATE_WITH_OPTIONAL_TIME = (
            r'^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$'
        )
        # this matches `YYYY-MM-DD YYYY-MM-DD` and optionally time for both dates
        MATCH_TWO_DATES_WITH_OPTIONAL_TIME = (
            r'^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})? \d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$'
        )
        MATCH_ANY_TEXT = (
            r'^.*$'
        )
        MATCH_NUMBER = (
            r'^\d+$'
        )

    class GetEntriesKeyboardChoices:
        GET_ALL_ENTRIES = ['Get all the entries']
        GET_ALL_ENTRIES_BY_DATE = ['by date', 'after date']
        GET_ALL_ENTRIES_BY_RECENT_DATE = ['Today', 'Yesterday', 'Past week']
        GET_ALL_BETWEEN_TWO_DATES = ['between two dates']
        GET_LAST_N_ENTRIES = ['last N entries']
        GET_ALL_ENTRIES_BY_TOPIC = ['by topic']

    class ContentTypes:
        VOICE = ['voice']

    class Commands:
        START = ['start']
        DELETE_REGEX = rf'^/d_(\d{len(DateFormatter.get_current_timestamp())})$'

    @staticmethod
    def get_delete_command(text: str):
        return re.search(MessageTypes.Commands.DELETE_REGEX, text)
