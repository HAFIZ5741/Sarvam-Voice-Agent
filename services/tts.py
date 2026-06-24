from sarvamai import SarvamAI
from dotenv import load_dotenv
import os
import base64
import time

load_dotenv()

client = SarvamAI(
    api_subscription_key=os.getenv("SARVAM_API_KEY")
)

def text_to_speech(text):

    response = client.text_to_speech.convert(
        text=text,
        target_language_code="en-IN",
        speaker="priya",
        model="bulbul:v3",
        output_audio_codec="wav"
    )

    audio_base64 = response.audios[0]

    audio_bytes = base64.b64decode(audio_base64)

    # Create a unique filename every time
    filename = f"audio/output_{int(time.time())}.wav"

    with open(filename, "wb") as f:
        f.write(audio_bytes)

    return filename