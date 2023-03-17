import os
import subprocess
import time


class FileController:
    @classmethod
    def convert_ogg_to_wav(cls, filename: str) -> str:
        if not os.path.exists(f'{filename}.wav'):
            # convert ogg to wav using ffmpeg
            subprocess.Popen(
                ['ffmpeg', '-i', f'{filename}.ogg', f'{filename}.wav', '-loglevel', 'quiet']
            )
            # wait before it updates the list of files
            time.sleep(1.5)
        return filename

    @classmethod
    def remove_files(cls, filename: str) -> bool:
        if os.path.exists(f'{filename}.ogg'):
            os.remove(f'{filename}.ogg')
        if os.path.exists(f'{filename}.wav'):
            os.remove(f'{filename}.wav')
        return True
