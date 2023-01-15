import os
from enum import Enum
from typing import Optional

from utils import user_id


class UserState(Enum):
    IDLE = 'IDLE'
    AUDIO_INPUT_TOPIC = 'AUD_INP_TP'
    AUDIO_AUTO_LANGUAGE = 'AUD_AUT_LN'
    AUDIO_INPUT_LANGUAGE = 'AUD_INP_LN'
    AUDIO_PROCESSING = 'AUD_PR'
    GET_ALL = 'GET_ALL'
    GET_LAST_N = 'GET_LAST_N'
    GET_BY_DATE = 'GET_BY_DATE'
    GET_ALL_BETWEEN = 'GET_ALL_BW'
    GET_ALL_AFTER = 'GET_ALL_AF'
    GET_BY_TOPIC = 'GET_ALL_TP'

    @staticmethod
    def audio_states():
        return [
            UserState.AUDIO_INPUT_TOPIC,
            UserState.AUDIO_INPUT_LANGUAGE,
            UserState.AUDIO_AUTO_LANGUAGE,
            UserState.AUDIO_PROCESSING
        ]

    @staticmethod
    def date_states_single():
        return [UserState.GET_BY_DATE, UserState.GET_ALL_AFTER]


class Entry:
    def __init__(
            self,
            topic: str = '', text: str = '', date: str = '', timestamp: int = '', language: str = ''
    ):
        self.language = language
        self.topic = topic
        self.text = text
        self.date = date
        self.timestamp = timestamp

    def to_dict(self) -> dict:
        return dict(
            (attr, getattr(self, attr)) for attr in dir(self) if not attr.startswith('__')
        )


class User:
    def __init__(self, user_id: int, state: UserState = UserState.IDLE, current_entry: Entry = None):
        self._id = user_id
        self._state = state
        self._current_entry = current_entry

    def set_state(self, state: UserState) -> None:
        self._state = state

    def is_state(self, state: Optional[UserState]) -> bool:
        return self._state == state

    def is_state_in(self, state_list: list) -> bool:
        return self._state in state_list

    @property
    def current_entry(self) -> Entry:
        return self._current_entry

    def cache_entry_data(
            self,
            topic: str = '', text: str = '', date: str = '', timestamp: int = '', language: str = ''
    ):
        self._current_entry.topic = topic
        self._current_entry.text = text
        self._current_entry.date = date
        self._current_entry.timestamp = timestamp
        self._current_entry.language = language

    def get_voice_message_filename(self) -> str:
        return f'{self._id}_{self._current_entry.timestamp}'

    def clear_cache(self):
        os.remove(f'{self.get_voice_message_filename()}.ogg')
        os.remove(f'{self.get_voice_message_filename()}.wav')
        self._current_entry = None
        self.set_state(UserState.IDLE)


class UserController:
    def __init__(self, users: dict):
        self.users = users

    def user(self, msg) -> Optional[User]:
        return self.users.get(user_id(msg), None)

    def is_registered(self, msg) -> bool:
        return self.user(msg) and not self.user(msg).is_state(None)

    def register(self, msg):
        if self.user(msg) is None:
            self.users[user_id(msg)] = User(
                user_id=user_id(msg),
                state=UserState.IDLE,
            )
        else:
            self.user(msg).set_state(UserState.IDLE)
