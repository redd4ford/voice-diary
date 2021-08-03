import os
import wave

import speech_recognition as sr_gapi
from google.cloud import speech_v1p1beta1 as sr_s2t


def recognize_google_api(file_path: str, language='en-US') -> str:
    r = sr_gapi.Recognizer()
    if os.path.isfile(file_path):
        with sr_gapi.AudioFile(file_path) as src:
            audio_data = r.record(src)
            text = r.recognize_google(audio_data, language=language)
        return text
    else:
        raise Exception('SERVER ERROR')


def recognize_speech_to_text(file_path: str) -> tuple[str, str]:
    client = sr_s2t.SpeechClient.from_service_account_json('serviceAccountKey.json')
    if os.path.isfile(file_path):
        with open(file_path, 'rb') as f:
            content = f.read()

        audio = sr_s2t.RecognitionAudio(content=content)

        config = sr_s2t.RecognitionConfig(audio_channel_count=get_channels(file_path),
                                          enable_automatic_punctuation=True,
                                          language_code='en-US', alternative_language_codes=['uk-UA', 'ru-RU'])

        response = client.recognize(config=config, audio=audio)
        transcript = ''
        languages = {'en-US': 0, 'ru-RU': 0, 'uk-UA': 0}
        for i, result in enumerate(response.results):
            # language_code comes in lowercase (en-us, ru-ru, uk-ua),
            # so we need to convert the last part of it to uppercase
            lan_code = result.language_code[:3] + result.language_code[3:].upper()
            languages[lan_code] += 1
            alternative = result.alternatives[0]
            transcript += alternative.transcript + '.'
        return get_used_language(languages), transcript
    else:
        raise Exception('SERVER ERROR')


def get_used_language(languages: dict) -> str:
    return str(list(languages.keys())[list(languages.values()).index(max(languages.values()))])


def get_channels(file_path: str) -> int:
    with wave.open(file_path, 'rb') as wave_file:
        return wave_file.getnchannels()
