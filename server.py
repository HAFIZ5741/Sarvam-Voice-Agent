import json
import base64
import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse, Connect

from main import SarvamE2EAgent  # your existing class

app = FastAPI()
agent = SarvamE2EAgent()

# ---------------------------
# 1. Twilio Webhook (TwiML)
# ---------------------------
@app.post("/voice")
async def voice():
    response = VoiceResponse()

    connect = Connect()
    connect.stream(url="ws://revise-squiggly-resilient.ngrok-free.dev/media")

    response.append(connect)

    return Response(content=str(response), media_type="text/xml")


# ---------------------------
# 2. WebSocket Media Stream
# ---------------------------
@app.websocket("/media")
async def media_stream(ws: WebSocket):
    await ws.accept()
    print("📞 Call Connected")

    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)

            if msg["event"] == "media":
                audio_payload = msg["media"]["payload"]

                # decode audio from Twilio
                audio_bytes = base64.b64decode(audio_payload)

                # 👉 send this audio to your STT pipeline
                # You need to modify your agent to accept external audio
                # await agent.transcript_queue.put("test input from call")
                await agent.process_audio_chunk(audio_bytes)

            elif msg["event"] == "start":
                print("▶ Stream started")

            elif msg["event"] == "stop":
                print("⛔ Call ended")
                break

    except Exception as e:
        print("Error:", e)



import asyncio
import base64
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse, Connect

from main import SarvamE2EAgent

app = FastAPI()

# >>> Set this to your current ngrok host (no protocol prefix) <<<
PUBLIC_HOST = "revise-squiggly-resilient.ngrok-free.dev"


# ---------------------------
# 1. Twilio Webhook (TwiML)
# ---------------------------
@app.post("/voice")
async def voice():
    response = VoiceResponse()
    connect = Connect()
    # Twilio Media Streams REQUIRE a secure websocket (wss), not ws.
    connect.stream(url=f"wss://{PUBLIC_HOST}/media")
    response.append(connect)
    return Response(content=str(response), media_type="text/xml")


# ---------------------------
# 2. WebSocket Media Stream
# ---------------------------
@app.websocket("/media")
async def media_stream(ws: WebSocket):
    await ws.accept()
    print("📞 Call Connected")

    stream_sid = None
    pipeline_task = None

    async def send_audio_to_twilio(mulaw_chunk: bytes):
        if stream_sid is None:
            return
        payload = base64.b64encode(mulaw_chunk).decode("utf-8")
        await ws.send_text(json.dumps({
            "event": "media",
            "streamSid": stream_sid,
            "media": {"payload": payload}
        }))

    # One agent per call, with its own queues/STT-socket/TTS-socket.
    agent = SarvamE2EAgent(send_audio_callback=send_audio_to_twilio)

    try:
        while True:
            data = await ws.receive_text()
            msg = json.loads(data)
            event = msg.get("event")

            if event == "start":
                stream_sid = msg["start"]["streamSid"]
                print(f"▶ Stream started: {stream_sid}")
                # Now that we have a live call, start the agent's pipelines.
                pipeline_task = asyncio.create_task(agent.start())

            elif event == "media":
                audio_payload = msg["media"]["payload"]
                audio_bytes = base64.b64decode(audio_payload)  # mu-law 8k from Twilio
                await agent.process_audio_chunk(audio_bytes)

            elif event == "stop":
                print("⛔ Call ended")
                break

    except WebSocketDisconnect:
        print("⚠️ Twilio websocket disconnected")
    except Exception as e:
        print("Error:", e)
    finally:
        agent.stop()
        if pipeline_task:
            pipeline_task.cancel()