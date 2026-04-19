import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")
HANDLE = os.getenv("CHANNEL_HANDLE")  # store handle in .env

if not API_KEY or not HANDLE:
    print("Missing API key or handle in .env")
    exit()

# remove @ if user included it
HANDLE = HANDLE.replace("@", "")

url = f"https://www.googleapis.com/youtube/v3/channels?part=id&forHandle={HANDLE}&key={API_KEY}"
response = requests.get(url)
data = response.json()

print("RAW RESPONSE:", data)

if "items" in data and len(data["items"]) > 0:
    channel_id = data["items"][0]["id"]
    print("\n✅ CHANNEL_ID:", channel_id)
else:
    print("\n❌ Could not find channel. Check handle.")