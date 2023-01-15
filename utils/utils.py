import subprocess
import time

from aiogram import types


def ogg_to_wav(filename: str):
    # convert ogg to wav using ffmpeg
    subprocess.Popen(
        ['ffmpeg', '-i', f'{filename}.ogg', f'{filename}.wav', '-loglevel', 'quiet'], shell=True
    )
    # wait before it updates the list of files
    time.sleep(0.5)


def user_id(msg: types.Message):
    return msg.from_user.id
