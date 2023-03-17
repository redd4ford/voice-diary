import firebase_admin
from firebase_admin import firestore
from firebase_admin import exceptions as firebase_exceptions

from core.user_controller import Entry
from utils import DateFormatter


class DatabaseController:
    def __init__(
        self, project_id: str, private_key_id: str, private_key: str, client_email: str,
        client_id: str, cert_url: str,
    ):
        cred = firebase_admin.credentials.Certificate(
            cert={
                'type': 'service_account',
                'project_id': project_id,
                'private_key_id': private_key_id,
                'private_key': private_key.replace('\\n', '\n'),
                'client_email': client_email,
                'client_id': client_id,
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'auth_provider_x509_cert_url': 'https://www.googleapis.com/oauth2/v1/certs',
                'client_x509_cert_url': cert_url
            }
        )
        firebase_admin.initialize_app(cred)
        self._db = firestore.client()

    def user_entries_ref(self, user_id: int):
        return self._db.collection('Users').document(f'{user_id}').collection('Entries')

    def curr_entry_ref(self, user_id: int, date: str):
        return self.user_entries_ref(user_id).document(date)

    async def create_entry(self, user_id: int, entry: Entry) -> str:
        """
        Save an entry to the user's collection of entries in Firestore.
        :param user_id: the user's Telegram ID.
        :param entry: the entry's data: date, timestamp, topic, text.
        :return: none
        """
        entry = entry.to_dict()
        try:
            (
                self
                .user_entries_ref(user_id)
                .document(entry['date'])
                .set(dict(
                    timestamp=entry['timestamp'],
                    topic=entry['topic'],
                    text=entry['text'],
                    language=entry['language'],
                ))
            )
        except firebase_exceptions.PermissionDeniedError:
            print('PERMISSION DENIED')
        except firebase_exceptions.UnavailableError:
            print('FIRESTORE UNAVAILABLE')
        except firebase_exceptions.UnknownError:
            print('UNKNOWN ERROR')
        else:
            return entry['date']

    async def delete_entry(self, user_id: int, timestamp: int) -> str:
        """
        Delete the user's entry by its timestamp.
        :param user_id: the user's Telegram ID.
        :param timestamp: the entry's date in timestamp.
        :return: none
        """
        date = DateFormatter.timestamp_to_date(timestamp)
        try:
            (
                self
                .curr_entry_ref(user_id, date)
                .delete()
            )
        except firebase_exceptions.PermissionDeniedError:
            print('PERMISSION DENIED')
        except firebase_exceptions.UnavailableError:
            print('FIRESTORE UNAVAILABLE')
        except firebase_exceptions.UnknownError:
            print('UNKNOWN ERROR')
        else:
            return DateFormatter.timestamp_to_date(timestamp=timestamp)

    async def fetch_all(self, user_id: int) -> dict:
        """
        Get the user's entries.
        :param user_id: the user's Telegram ID.
        :return: a list of DocumentSnapshots (still need to be converted to dicts!)
        """
        try:
            return (
                self
                .user_entries_ref(user_id)
                .get()
            )
        except firebase_exceptions.PermissionDeniedError:
            print('PERMISSION DENIED')
        except firebase_exceptions.UnavailableError:
            print('FIRESTORE UNAVAILABLE')
        except firebase_exceptions.UnknownError:
            print('UNKNOWN ERROR')

    async def fetch_by_date(self, user_id: int, date: str, is_exact: bool) -> list:
        """
        Fetch all entries for the date if the date is presented like YY-mm-dd without timing.
        :param user_id: the user's Telegram ID.
        :param date: the date to fetch the entries for.
        :param is_exact: is date the exact datetime; if not, parse all the entries for that day.
        :return: a list of DocumentSnapshots (still need to be converted to dicts!)
        """
        try:
            if is_exact:
                # if the exact date is passed, get the entry by its doc ID
                return (
                    self
                    .user_entries_ref(user_id)
                    .document(date)
                    .get()
                )
            else:
                return (
                    self
                    .user_entries_ref(user_id)
                    .order_by('timestamp', direction='ASCENDING')
                    .start_at({'timestamp': DateFormatter.date_to_timestamp(date)})
                    .end_before({'timestamp': DateFormatter.days_ago_timestamp(-1, date=date)})
                    .get()
                )
        except firebase_exceptions.PermissionDeniedError:
            print('PERMISSION DENIED')
        except firebase_exceptions.UnavailableError:
            print('FIRESTORE UNAVAILABLE')
        except firebase_exceptions.UnknownError:
            print('UNKNOWN ERROR')

    async def fetch_by_topic(self, user_id: int, topic: str) -> list:
        """
        Get all the entries by topic param.
        :param user_id: the user's Telegram ID.
        :param topic: the topic to search for.
        :return: a list of DocumentSnapshots (still need to be converted to dicts!)
        """
        try:
            return (
                self
                .user_entries_ref(user_id)
                .where('topic', '==', topic)
                .get()
            )
        except firebase_exceptions.PermissionDeniedError:
            print('PERMISSION DENIED')
        except firebase_exceptions.UnavailableError:
            print('FIRESTORE UNAVAILABLE')
        except firebase_exceptions.UnknownError:
            print('UNKNOWN ERROR')

    async def fetch_last_n(self, user_id: int, number: int) -> list:
        """
        Get the user's N last entries.
        :param user_id: the user's Telegram ID.
        :param number: the number of entries to fetch.
        :return: a list of DocumentSnapshots (still need to be converted to dicts!)
        """
        try:
            return (
                self
                .user_entries_ref(user_id)
                .order_by('timestamp', direction='DESCENDING')
                .limit(number)
                .get()
            )
        except firebase_exceptions.PermissionDeniedError:
            print('PERMISSION DENIED')
        except firebase_exceptions.UnavailableError:
            print('FIRESTORE UNAVAILABLE')
        except firebase_exceptions.UnknownError:
            print('UNKNOWN ERROR')

    async def fetch_between_dates(self, user_id: int, date1: str, date2: str) -> list:
        """
        Get all the entries between two dates. Handles the cases when date1 >= date2.
        :param user_id: the user's Telegram ID.
        :param date1: the first date of the interval.
        :param date2: the second date of the interval.
        :return: a list of DocumentSnapshots (still need to be converted to dicts!)
        """
        if DateFormatter.is_equal(date1, date2):
            await self.fetch_by_date(user_id, date1, is_exact=True)
        else:
            try:
                return (
                    self
                    .user_entries_ref(user_id)
                    .order_by('timestamp', direction='ASCENDING')
                    .start_at({'timestamp': DateFormatter.min_timestamp(date1, date2)})
                    .end_at({'timestamp': DateFormatter.max_timestamp(date1, date2)})
                    .get()
                )
            except firebase_exceptions.PermissionDeniedError:
                print('PERMISSION DENIED')
            except firebase_exceptions.UnavailableError:
                print('FIRESTORE UNAVAILABLE')
            except firebase_exceptions.UnknownError:
                print('UNKNOWN ERROR')

    async def fetch_after_date(self, user_id: int, date: str) -> list:
        """
        Get all the entries after a specific date.
        :param user_id: the user's Telegram ID.
        :param date: the date to fetch after.
        :return: a list of DocumentSnapshots (still need to be converted to dicts!)
        """
        try:
            return (
                self
                .user_entries_ref(user_id)
                .order_by('timestamp', direction='ASCENDING')
                .start_after({'timestamp': DateFormatter.date_to_timestamp(date)})
                .get()
            )
        except firebase_exceptions.PermissionDeniedError:
            print('PERMISSION DENIED')
        except firebase_exceptions.UnavailableError:
            print('FIRESTORE UNAVAILABLE')
        except firebase_exceptions.UnknownError:
            print('UNKNOWN ERROR')
