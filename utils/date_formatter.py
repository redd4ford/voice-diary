import datetime

from dateutil import parser


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
