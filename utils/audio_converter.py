import wave

def raw_to_wav(raw_file, wav_file):

    with open(raw_file, "rb") as f:
        raw_audio = f.read()

    with wave.open(wav_file, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(1)
        wav.setframerate(8000)
        wav.writeframes(raw_audio)

    return wav_file