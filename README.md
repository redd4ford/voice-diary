# voice-diary
a speech recognition Telegram bot that converts your voice messages to text and saves them to Firestore.

### Pre-requisites:
* [install ffmpeg](https://www.hostinger.com/tutorials/how-to-install-ffmpeg)
* create a Firebase project, setup Cloud Firestore and extract service account data ([How to get it](https://firebase.google.com/docs/admin/setup#initialize_the_sdk_in_non-google_environments))
* create a Telegram bot and get its token ([Via BotFather](https://t.me/BotFather))
* create `.env` based on `.env.example`
* install `requirements.txt`
* run `python main.py`
