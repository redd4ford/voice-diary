import wave
import json
import vosk


def recognize_phrase(model: vosk.Model, file_path: str) -> str:
    """
    Recognize Russian speech in a .wav file
    """

    wave_audio_file = wave.open(file_path, "rb")
    offline_recognizer = vosk.KaldiRecognizer(model, 24000)
    data = wave_audio_file.readframes(wave_audio_file.getnframes())

    offline_recognizer.AcceptWaveform(data)
    recognized_data = json.loads(offline_recognizer.Result())["text"]
    return recognized_data
