import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")
CHANNEL_ID = os.getenv("CHANNEL_ID")

# sanity check
if not API_KEY or not CHANNEL_ID:
    print("Missing API_KEY or CHANNEL_ID in .env")
    exit()

# Step 1: get channel details
url = f"https://www.googleapis.com/youtube/v3/channels?part=contentDetails&id={CHANNEL_ID}&key={API_KEY}"
response = requests.get(url)
data = response.json()

# debug print (temporary)
print("RAW RESPONSE:", data)

# Step 2: safe handling
if "items" not in data or len(data["items"]) == 0:
    print("❌ Error: No channel found or API issue")
    print("Check your CHANNEL_ID and API_KEY")
    exit()

# Step 3: extract uploads playlist
uploads_playlist = data['items'][0]['contentDetails']['relatedPlaylists']['uploads']

print("✅ Uploads Playlist ID:", uploads_playlist)