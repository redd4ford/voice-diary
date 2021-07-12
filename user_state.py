from enum import Enum


class UserState(Enum):
    IDLE = 'IDLE'
    AUDIO_INPUT_TOPIC = 'AUD_INP_TP'
    AUDIO_INPUT_LANGUAGE = 'AUD_INP_LN'
    AUDIO_PROCESSING = 'AUD_PR'
    GET_ALL = 'GET_ALL'
    GET_LAST_N = 'GET_LAST_N'
    GET_BY_DATE = 'GET_BY_DATE'
    GET_ALL_BETWEEN = 'GET_ALL_BW'
    GET_ALL_AFTER = 'GET_ALL_AF'
    GET_BY_TOPIC = 'GET_ALL_TP'
