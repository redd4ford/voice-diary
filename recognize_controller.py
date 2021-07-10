import speech_recognition as sr
import os


def recognize_phrase(file_path: str, language='en-US') -> str:
    """
    Recognize speech in a .wav file
    """
    r = sr.Recognizer()
    if os.path.isfile(file_path):
        with sr.AudioFile(file_path) as src:
            audio_data = r.record(src)
            text = r.recognize_google(audio_data, language=language)
        return text
    else:
        raise Exception('SERVER ERROR')
