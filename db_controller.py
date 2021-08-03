import firebase_admin
from firebase_admin import firestore
from firebase_admin import exceptions as f
from utils import date_to_timestamp, timestamp_to_date, days_ago_timestamp

cred = firebase_admin.credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

user_recs_ref = lambda user_id: db.collection('Users').document(str(user_id)).collection('Entries')

curr_rec_ref = lambda user_id, date: user_recs_ref(user_id).document(date)


async def create_entry(user_id: int, entry: dict):
    """
    Save a entry to the user's collection of entries in Firestore.
    :param user_id: the user's Telegram ID.
    :param entry: the entry's data in a dictionary: date, timestamp, topic, text.
    :return: none
    """
    try:
        user_recs_ref(user_id)\
                .document(entry['date'])\
                .set({
                    'timestamp': entry['timestamp'],
                    'topic': entry['topic'],
                    'text': entry['text'],
                    'language': entry['language']
                })
    except f.PermissionDeniedError:
        print('PERMISSION DENIED')
    except f.UnavailableError:
        print('FIRESTORE UNAVAILABLE')
    except f.UnknownError:
        print('UNKNOWN ERROR')
    else:
        print('OK')


async def delete_entry(user_id: int, timestamp: int):
    """
    Delete the user's entry by its timestamp.
    :param user_id: the user's Telegram ID.
    :param timestamp: the entry's date in timestamp.
    :return: none
    """
    date = timestamp_to_date(timestamp)
    try:
        curr_rec_ref(user_id, date)\
                .delete()
    except f.PermissionDeniedError:
        print('PERMISSION DENIED')
    except f.UnavailableError:
        print('FIRESTORE UNAVAILABLE')
    except f.UnknownError:
        print('UNKNOWN ERROR')
    else:
        print('OK')


async def fetch_all(user_id: int) -> dict:
    """
    Get the user's entries.
    :param user_id: the user's Telegram ID.
    :return: a list of DocumentSnapshots (still need to be converted to dicts!)
    """
    try:
        return user_recs_ref(user_id)\
                .get()
    except f.PermissionDeniedError:
        print('PERMISSION DENIED')
    except f.UnavailableError:
        print('FIRESTORE UNAVAILABLE')
    except f.UnknownError:
        print('UNKNOWN ERROR')


async def fetch_by_date(user_id: int, date: str, is_exact: bool) -> list:
    """
    Fetch all entries for the date if the date is presented like YY-mm-dd without timing.
    :param user_id: the user's Telegram ID.
    :param date: the date to fetch the entries for.
    :param is_exact: is date the exact datetime; if not, parse all the entries for that day.
    :return: a list of DocumentSnapshots (still need to be converted to dicts!)
    """
    try:
        if is_exact:
            # if the exact data is passed, get the entry by its doc ID
            return [user_recs_ref(user_id)
                    .document(date)
                    .get()]
        else:
            return user_recs_ref(user_id) \
                .order_by('timestamp', direction='ASCENDING')\
                .start_at({'timestamp': date_to_timestamp(date)})\
                .end_before({'timestamp': days_ago_timestamp(-1, date=date)})\
                .get()
    except f.PermissionDeniedError:
        print('PERMISSION DENIED')
    except f.UnavailableError:
        print('FIRESTORE UNAVAILABLE')
    except f.UnknownError:
        print('UNKNOWN ERROR')


async def fetch_by_topic(user_id: int, topic: str) -> list:
    """
    Get all the entries by topic param.
    :param user_id: the user's Telegram ID.
    :param topic: the topic to search for.
    :return: a list of DocumentSnapshots (still need to be converted to dicts!)
    """
    try:
        return user_recs_ref(user_id)\
                .where('topic', '==', topic)\
                .get()
    except f.PermissionDeniedError:
        print('PERMISSION DENIED')
    except f.UnavailableError:
        print('FIRESTORE UNAVAILABLE')
    except f.UnknownError:
        print('UNKNOWN ERROR')


async def fetch_last_n(user_id: int, number: int) -> list:
    """
    Get the user's N last entries.
    :param user_id: the user's Telegram ID.
    :param number: the number of entries to fetch.
    :return: a list of DocumentSnapshots (still need to be converted to dicts!)
    """
    try:
        return user_recs_ref(user_id)\
                .order_by('timestamp', direction='DESCENDING')\
                .limit(number)\
                .get()
    except f.PermissionDeniedError:
        print('PERMISSION DENIED')
    except f.UnavailableError:
        print('FIRESTORE UNAVAILABLE')
    except f.UnknownError:
        print('UNKNOWN ERROR')


async def fetch_between(user_id: int, date1: str, date2: str) -> list:
    """
    Get all the entries between two dates. Handles the cases when date1 >= date2.
    :param user_id: the user's Telegram ID.
    :param date1: the first date of the interval.
    :param date2: the second date of the interval.
    :return: a list of DocumentSnapshots (still need to be converted to dicts!)
    """
    if date_to_timestamp(date1) == date_to_timestamp(date2):
        await fetch_by_date(user_id, date1, is_exact=True)
    else:
        try:
            return user_recs_ref(user_id)\
                    .order_by('timestamp', direction='ASCENDING')\
                    .start_at({'timestamp': min(date_to_timestamp(date1), date_to_timestamp(date2))})\
                    .end_at({'timestamp': max(date_to_timestamp(date1), date_to_timestamp(date2))})\
                    .get()
        except f.PermissionDeniedError:
            print('PERMISSION DENIED')
        except f.UnavailableError:
            print('FIRESTORE UNAVAILABLE')
        except f.UnknownError:
            print('UNKNOWN ERROR')


async def fetch_after(user_id: int, date: str) -> list:
    """
    Get all the entries after a specific date.
    :param user_id: the user's Telegram ID.
    :param date: the date to fetch after.
    :return: a list of DocumentSnapshots (still need to be converted to dicts!)
    """
    try:
        return user_recs_ref(user_id) \
                .order_by('timestamp', direction='ASCENDING') \
                .start_after({'timestamp': date_to_timestamp(date)})\
                .get()
    except f.PermissionDeniedError:
        print('PERMISSION DENIED')
    except f.UnavailableError:
        print('FIRESTORE UNAVAILABLE')
    except f.UnknownError:
        print('UNKNOWN ERROR')
