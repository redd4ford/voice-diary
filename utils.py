import datetime


def get_date() -> str:
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def timestamp_to_date(timestamp: int) -> str:
    return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')


def date_to_timestamp(date: str) -> int:
    return int(datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S').timestamp())


def days_ago_date(days: int) -> str:
    return (datetime.date.today() - datetime.timedelta(days=days)).strftime('%Y-%m-%d 00:00:00')


def days_ago_timestamp(days: int) -> int:
    return date_to_timestamp(days_ago_date(days=days))


def process_fetched(fetched_data) -> list:
    return sorted([recording.to_dict() for recording in fetched_data], key=lambda rec: rec['timestamp'])
