from utils.recorder import record_audio
from services.stt import transcribe
from services.llm import generate_response
from services.tts import text_to_speech

from playsound import playsound

while True:

    record_audio()

    print("Transcribing...")

    user_text = transcribe("audio/input.wav")

    print(f"\nYou: {user_text}")

    if not user_text:
        continue

    if any(word in user_text.lower() for word in ["exit", "quit", "stop"]):
        print("Stopping...")
        break

    print("Thinking...")

    ai_response = generate_response(user_text)

    if not ai_response:
        print("No response from LLM")
        continue

    print("\nAI Response Length:", len(ai_response))
    print(f"\nAI: {ai_response}")

    print("Generating speech...")

    output_file = text_to_speech(ai_response)

    print("Playing response...")

    playsound(output_file)

print("Goodbye!")