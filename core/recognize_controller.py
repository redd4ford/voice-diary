import os
import wave
from abc import (
    ABC,
    abstractmethod,
)

import speech_recognition as speech_recognition_google_api
from google.cloud import speech_v1p1beta1 as speech_recognition_s2t_api


class SpeechRecognitionController(ABC):
    @abstractmethod
    def recognize(self, file_path: str, language: str = None):
        pass


class GoogleApiRecognitionController(SpeechRecognitionController):
    def __init__(self):
        self.api_ref = speech_recognition_google_api
        self.recognizer = self.api_ref.Recognizer()
        print('Using Google Speech Recognition API')

    def recognize(self, file_path: str, language: str = 'en-US') -> str:
        if os.path.isfile(file_path):
            with self.api_ref.AudioFile(file_path) as src:
                audio_data = self.recognizer.record(src)
                text = self.recognizer.recognize_google(audio_data, language=language)
            return text
        else:
            raise Exception('SERVER ERROR')


class SpeechToTextApiRecognitionController(SpeechRecognitionController):
    def __init__(self):
        self.api_ref = speech_recognition_s2t_api
        self.recognizer = self.api_ref.SpeechClient.from_service_account_info({
            'type': 'service_account',
            'project_id': os.getenv('FIREBASE_PROJECT_ID'),
            'private_key_id': os.getenv('FIREBASE_PRIVATE_KEY_ID'),
            'private_key': os.getenv('FIREBASE_PRIVATE_KEY'),
            'client_email': os.getenv('FIREBASE_CLIENT_EMAIL'),
            'client_id': os.getenv('FIREBASE_CLIENT_ID'),
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'auth_provider_x509_cert_url': 'https://www.googleapis.com/oauth2/v1/certs',
            'client_x509_cert_url': os.getenv('FIREBASE_CLIENT_X509_CERT_URL')
        })
        print('Using Google Speech-To-Text API')

    def recognize(self, file_path: str, language: str = None) -> tuple[str, str]:
        if os.path.isfile(file_path):
            with open(file_path, 'rb') as f:
                content = f.read()

            audio = self.api_ref.RecognitionAudio(content=content)

            config = self.api_ref.RecognitionConfig(
                audio_channel_count=self.get_channels(file_path),
                enable_automatic_punctuation=True,
                language_code='en-US',
                alternative_language_codes=['uk-UA']
            )

            response = self.recognizer.recognize(config=config, audio=audio)
            transcript = ''

            languages = {'en-US': 0, 'uk-UA': 0}
            for i, result in enumerate(response.results):
                # language_code comes in lowercase (en-us, uk-ua),
                # so we need to convert the last part of it to uppercase
                lan_code = result.language_code[:3] + result.language_code[3:].upper()
                languages[lan_code] += 1
                alternative = result.alternatives[0]
                transcript += f'{alternative.transcript}.'
            return self.get_used_language(languages), transcript
        else:
            raise Exception('SERVER ERROR')

    @classmethod
    def get_used_language(cls, languages: dict) -> str:
        return max(languages, key=languages.get)

    @classmethod
    def get_channels(cls, file_path: str) -> int:
        with wave.open(file_path, 'rb') as wave_file:
            return wave_file.getnchannels()
