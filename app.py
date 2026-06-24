import asyncio, base64, io, json, logging, os, ssl, struct, urllib.request, urllib.error, wave, time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import Response

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

SARVAM_API_KEY = os.environ["SARVAM_API_KEY"]
PUBLIC_HOST    = os.environ["PUBLIC_HOST"]
TWILIO_RATE    = 8000
STT_RATE       = 16000
SILENCE_SEC    = 1.5
MIN_BYTES      = 6400
MAX_BYTES      = 200000

app = FastAPI()

@app.get("/")
async def health():
    return {"status": "ok"}

@app.post("/twilio")
async def twilio_hook(request: Request):
    xml = '<?xml version="1.0" encoding="UTF-8"?><Response><Connect><Stream url="wss://' + PUBLIC_HOST + '/ws"/></Connect></Response>'
    return Response(content=xml, media_type="text/xml")

def ulaw_decode(data):
    out = bytearray(len(data) * 2)
    for i, b in enumerate(data):
        b = (~b) & 0xFF
        sign = b & 0x80
        exp  = (b >> 4) & 0x07
        mant = b & 0x0F
        val  = (((mant << 1) + 33) << exp) - 33
        if sign: val = -val
        struct.pack_into("<h", out, i*2, max(-32768, min(32767, val)))
    return bytes(out)

_E = [0,0,1,1,2,2,2,2,3,3,3,3,3,3,3,3,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,
      5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,5,
      6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,
      6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,6,
      7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,
      7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,
      7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,
      7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7,7]

def ulaw_encode(pcm16):
    n = len(pcm16)//2
    samples = struct.unpack(f"<{n}h", pcm16)
    out = bytearray(n)
    for i, s in enumerate(samples):
        sg = 0
        if s < 0: sg = 0x80; s = -s
        s = min(s, 32635) + 0x84
        e = _E[s >> 8]
        out[i] = (~(sg | (e << 4) | ((s >> (e+3)) & 0x0F))) & 0xFF
    return bytes(out)

def resample(pcm16, fh, th):
    if fh == th: return pcm16
    ni = len(pcm16)//2
    no = max(1, int(round(ni * th / fh)))
    src = struct.unpack(f"<{ni}h", pcm16)
    out = []
    for i in range(no):
        p = i*(ni-1)/max(no-1,1)
        lo = int(p); hi = min(lo+1, ni-1)
        out.append(int(src[lo] + (p-lo)*(src[hi]-src[lo])))
    return struct.pack(f"<{no}h", *out)

def make_wav(pcm16, rate):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(pcm16)
    return buf.getvalue()

def read_wav(data):
    buf = io.BytesIO(data)
    with wave.open(buf, "rb") as w:
        return w.readframes(w.getnframes()), w.getframerate()

_SSL = ssl.create_default_context()

def post_json(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
        headers={"api-subscription-key": SARVAM_API_KEY, "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, context=_SSL, timeout=25) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        t = e.read().decode(); log.error(f"HTTP {e.code}: {t[:200]}"); return e.code, {"error": t}

def post_mp(url, fields, fdata, fname):
    bd = b"B0undary123"
    body = b""
    for k, v in fields.items():
        body += b"--"+bd+b"\r\nContent-Disposition: form-data; name=\""+k.encode()+b"\"\r\n\r\n"+v.encode()+b"\r\n"
    body += b"--"+bd+b"\r\nContent-Disposition: form-data; name=\"file\"; filename=\""+fname.encode()+b"\"\r\nContent-Type: audio/wav\r\n\r\n"+fdata+b"\r\n--"+bd+b"--\r\n"
    req = urllib.request.Request(url, data=body,
        headers={"api-subscription-key": SARVAM_API_KEY, "Content-Type": "multipart/form-data; boundary=B0undary123"}, method="POST")
    try:
        with urllib.request.urlopen(req, context=_SSL, timeout=25) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        t = e.read().decode(); log.error(f"HTTP {e.code}: {t[:200]}"); return e.code, {"error": t}

async def stt(wav):
    log.info(f"[STT] {len(wav)} bytes")
    s, d = await asyncio.to_thread(post_mp, "https://api.sarvam.ai/speech-to-text",
        {"model": "saarika:v2.5", "language_code": "unknown"}, wav, "a.wav")
    log.info(f"[STT] HTTP {s} {str(d)[:200]}")
    if s != 200: return None
    t = (d.get("transcript") or "").strip()
    log.info(f"[STT] -> '{t}'")
    return t or None

async def llm(msgs):
    for model in ["sarvam-105b", "sarvam-30b"]:
        s, d = await asyncio.to_thread(post_json, "https://api.sarvam.ai/v1/chat/completions",
            {"model": model, "messages": msgs, "max_tokens": 200, "temperature": 0.7})
        log.info(f"[LLM] {model} HTTP {s} {str(d)[:200]}")
        if s == 200:
            c = (d.get("choices",[{}])[0].get("message",{}).get("content") or "").strip()
            if c: log.info(f"[LLM] -> '{c}'"); return c
    return None

async def tts(text):
    log.info(f"[TTS] '{text[:80]}'")
    s, d = await asyncio.to_thread(post_json, "https://api.sarvam.ai/text-to-speech",
        {"inputs": [text], "target_language_code": "en-IN", "speaker": "anushka",
         "model": "bulbul:v2", "enable_preprocessing": True})
    log.info(f"[TTS] HTTP {s}")
    if s != 200: log.error(f"[TTS] {d}"); return None
    try:
        w = base64.b64decode(d["audios"][0]); log.info(f"[TTS] {len(w)} bytes"); return w
    except Exception as e:
        log.error(f"[TTS] {e}"); return None

@app.websocket("/ws")
async def ws_handler(ws: WebSocket):
    await ws.accept()
    log.info("[WS] CALL STARTED")
    sid        = None
    buf        = bytearray()
    speaking   = False
    processing = False
    active     = True
    last_chunk = 0.0
    history    = [{"role": "system", "content": "You are a helpful AI voice assistant on a phone call. Reply in 1-2 short sentences only. No bullet points."}]

    async def play(wav_bytes):
        nonlocal speaking, buf
        if not sid: return
        speaking = True
        buf = bytearray()
        try:
            pcm, rate = read_wav(wav_bytes)
            ulaw = ulaw_encode(resample(pcm, rate, TWILIO_RATE))
            log.info(f"[PLAY] {len(ulaw)} bytes")
            for i in range(0, len(ulaw), 160):
                await ws.send_text(json.dumps({"event":"media","streamSid":sid,
                    "media":{"payload":base64.b64encode(ulaw[i:i+160]).decode()}}))
            await ws.send_text(json.dumps({"event":"mark","streamSid":sid,"mark":{"name":"done"}}))
            await asyncio.sleep(0.8)
        except Exception as e:
            log.error(f"[PLAY] {e}")
        finally:
            buf = bytearray()
            speaking = False
            log.info("[PLAY] done - mic ON")

    async def pipeline(audio):
        nonlocal processing
        processing = True
        log.info(f"[PIPE] {len(audio)} bytes")
        try:
            if len(audio) > MAX_BYTES:
                audio = audio[-MAX_BYTES:]
            text = await stt(make_wav(resample(audio, TWILIO_RATE, STT_RATE), STT_RATE))
            if not text: return
            history.append({"role":"user","content":text})
            reply = await llm(history) or "Sorry, could you repeat that?"
            history.append({"role":"assistant","content":reply})
            w = await tts(reply)
            if w: await play(w)
        except Exception as e:
            log.exception(f"[PIPE] {e}")
        finally:
            processing = False
            log.info("[PIPE] done")

    async def watcher():
        nonlocal last_chunk, buf
        while active:
            await asyncio.sleep(0.2)
            if speaking or processing or last_chunk == 0: continue
            if time.time() - last_chunk >= SILENCE_SEC and len(buf) >= MIN_BYTES:
                log.info(f"[WATCHER] silence -> pipeline buf={len(buf)}")
                audio = bytes(buf)
                buf = bytearray()
                last_chunk = 0.0
                await pipeline(audio)

    async def greet():
        w = await tts("Hello! I am your AI assistant. How can I help you today?")
        if w: await play(w)

    try:
        async for raw in ws.iter_text():
            try: msg = json.loads(raw)
            except: continue
            ev = msg.get("event","")
            if ev == "connected":
                log.info("[WS] connected")
            elif ev == "start":
                sid = msg["start"]["streamSid"]
                log.info(f"[WS] started sid={sid}")
                asyncio.create_task(watcher())
                asyncio.create_task(greet())
            elif ev == "media":
                if speaking: continue
                buf.extend(ulaw_decode(base64.b64decode(msg["media"]["payload"])))
                last_chunk = time.time()
                if len(buf) >= MAX_BYTES and not processing:
                    log.info("[WS] buf full -> pipeline")
                    audio = bytes(buf)
                    buf = bytearray()
                    last_chunk = 0.0
                    asyncio.create_task(pipeline(audio))
            elif ev == "stop":
                log.info("[WS] stopped")
                break
    except WebSocketDisconnect:
        log.info("[WS] disconnected")
    except Exception as e:
        log.exception(f"[WS] {e}")
    finally:
        active = False
        log.info("[WS] CALL ENDED")
