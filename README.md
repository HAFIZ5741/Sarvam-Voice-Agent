# Sarvam Voice Agent

A real-time AI Voice Agent built using Sarvam AI, FastAPI, Twilio, and Ngrok. The application receives voice input from a phone call, converts speech to text, generates intelligent responses using an LLM, converts the response back to speech, and streams it to the caller.

## Tech Stack

* Python
* FastAPI
* Sarvam AI
* Twilio
* Ngrok
* WebSockets
* Uvicorn

## Project Structure

```text
sarvam_voice_agent/
│
├── services/
│   ├── stt.py
│   ├── llm.py
│   └── tts.py
│
├── utils/
│   ├── recorder.py
│   └── audio_converter.py
│
├── app.py
├── main.py
├── stt.py
├── README.md
└── .env
```

## System Architecture

1. User places a call through Twilio.
2. Twilio sends audio data to the FastAPI application.
3. Ngrok exposes the local FastAPI server to the internet.
4. Sarvam STT converts speech into text.
5. The text is sent to the LLM for response generation.
6. Sarvam TTS converts the generated response into audio.
7. Audio is streamed back to the caller through Twilio.

## Setup

### Clone Repository

```bash
git clone https://github.com/HAFIZ5741/Sarvam-Voice-Agent.git
cd Sarvam-Voice-Agent
```

### Create Virtual Environment

```bash
python -m venv .venv
```
### Activate Environment

Windows:

```bash
.venv\Scripts\activate
```
## Environment Variables

Create a `.env` file:

```env
SARVAM_API_KEY=your_api_key
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=your_twilio_number
```

## Running the Application

Start the FastAPI server:

```bash
uvicorn app:app --reload
```

## Expose Local Server Using Ngrok

Start Ngrok:

```bash
ngrok http 8000
```

Copy the generated HTTPS URL and configure it in Twilio Voice Webhooks.

Example:

```text
https://your-ngrok-url.ngrok-free.app/twilio
```

## Twilio Integration

* Configure the Twilio phone number webhook.
* Point the Voice URL to the Ngrok HTTPS endpoint.
* Twilio forwards call events and audio streams to the FastAPI server.



## Author

Hafiz Mansuri
