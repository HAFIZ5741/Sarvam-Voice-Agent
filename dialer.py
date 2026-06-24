from twilio.rest import Client

ACCOUNT_SID  = ""
AUTH_TOKEN   = ""
PUBLIC_HOST  = ""   # your ngrok URL

client = Client(ACCOUNT_SID, AUTH_TOKEN)

call = client.calls.create(
    to="",          # your phone number
    from_="",        # your Twilio number
    url=f"https://{PUBLIC_HOST}/twilio",   # points to app.py webhook
)

print(f"✅ Call initiated! SID: {call.sid}"
