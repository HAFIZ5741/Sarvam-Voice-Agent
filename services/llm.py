from sarvamai import SarvamAI
from dotenv import load_dotenv
import os

load_dotenv()

client = SarvamAI(
    api_subscription_key=os.getenv("SARVAM_API_KEY")
)

def generate_response(text):

    try:

        response = client.chat.completions(
            model="sarvam-30b",
            messages=[
                {
                    "role": "user",
                    "content": text
                }
            ]
        )

        return response.choices[0].message.content

    except Exception as e:
        print("LLM Error:", e)
        return None