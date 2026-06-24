import sounddevice as sd
import soundfile as sf

def record_audio():

    duration = 5
    sample_rate = 16000

    print("Speak now...")

    recording = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1
    )

    sd.wait()

    sf.write(
        "audio/input.wav",
        recording,
        sample_rate
    )

    print("Recording saved")