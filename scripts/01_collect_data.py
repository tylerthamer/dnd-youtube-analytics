
import os
import json
import time
from datetime import datetime
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
API_KEY = os.getenv("YOUTUBE_API_KEY")
if not API_KEY:
    raise ValueError("No API key found. Make sure your .env file has YOUTUBE_API_KEY=...")

youtube = build("youtube", "v3", developerKey=API_KEY)

CHANNELS = {
    "Critical Role":          {"id": "UCpXBGqwsBkpvcYjsJBQ7LEQ", "tier": "large"},
    "Dimension 20":           {"id": "UCC8zWIx8aBQme-x1nX9iZ0A", "tier": "large"},  # verify
    "Legends of Avantris":    {"id": "UCiER8p540j2SosO7OX7E0VA", "tier": "large"},
    "High Rollers DnD":       {"id": "UC3qtZRMtWNaD2Q96STxgOrA", "tier": "large"},
    "Narrative Declaration":  {"id": "UCDP6Ob4_eVR4meY7S5fTYUg", "tier": "small"},
    "Unexpectables":          {"id": "UCB9zFd3_X5A9XAxeHBIjudQ", "tier": "small"},
    "VibeCheckDND":           {"id": "UChvmHyl5CVxV8--0qU5e9xQ", "tier": "small"},
    "Just Roll With It":      {"id": "UCssTrx7qnoG5ufeBEF4dezg", "tier": "small"},
}

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

def save_raw(filename, data):
    filepath = os.path.join(RAW_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"  Saved: {filename}")


# ── Step 1: Fetch channel-level stats ──────────────────────────────────────
def fetch_channel_stats(channel_name, channel_id):
    print(f"\nFetching channel stats: {channel_name}")
    response = youtube.channels().list(
        part="snippet,statistics,contentDetails",
        id=channel_id
    ).execute()


    return response

def fetch_all_video_ids(uploads_playlist_id):
    video_ids = []
    next_page_token = None

    while True:
        response = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=uploads_playlist_id,
            maxResults=50,
            pageToken=next_page_token
        ).execute()

        for item in response["items"]:
            video_ids.append(item["contentDetails"]["videoId"])

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

        time.sleep(0.1) 

    return video_ids


def fetch_video_details(video_ids):
    all_videos = []

    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        response = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=",".join(batch)
        ).execute()

        all_videos.extend(response.get("items", []))
        print(f"  Fetched videos {i+1}–{min(i+50, len(video_ids))} of {len(video_ids)}")
        time.sleep(0.1)

    return all_videos


def main():
    collection_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"Starting collection at {collection_timestamp}")
    print("=" * 60)

    summary = {} 

    for channel_name, info in CHANNELS.items():
        channel_id = info["id"]
        tier = info["tier"]

        if channel_id == "FILL_IN":
            print(f"\n Skipping {channel_name} — channel ID not filled in yet")
            continue

        try:
            #Channel stats
            channel_data = fetch_channel_stats(channel_name, channel_id)
            channel_data["_meta"] = {
                "channel_name": channel_name,
                "tier": tier,
                "collected_at": collection_timestamp
            }

            safe_name = channel_name.lower().replace(" ", "_")
            save_raw(f"{safe_name}_channel.json", channel_data)

            #Extract uploads playlist Id
            uploads_playlist_id = (
                channel_data["items"][0]["contentDetails"]
                ["relatedPlaylists"]["uploads"]
            )
            print(f"  Uploads playlist: {uploads_playlist_id}")

            #All video IDs
            print(f"  Fetching video IDs...")
            video_ids = fetch_all_video_ids(uploads_playlist_id)
            print(f"  Found {len(video_ids)} videos")

            #Video details
            print(f"  Fetching video details...")
            videos = fetch_video_details(video_ids)

            videos_payload = {
                "_meta": {
                    "channel_name": channel_name,
                    "channel_id": channel_id,
                    "tier": tier,
                    "video_count": len(videos),
                    "collected_at": collection_timestamp
                },
                "videos": videos
            }
            save_raw(f"{safe_name}_videos.json", videos_payload)

            summary[channel_name] = len(videos)

        except Exception as e:
            print(f"  X ERROR on {channel_name}: {e}")
 
   
    print("\n" + "=" * 60)
    print("Collection complete. Video counts:")
    for name, count in summary.items():
        print(f"  {name}: {count} videos")
    print(f"\nRaw files saved to: {os.path.abspath(RAW_DIR)}")


if __name__ == "__main__":
    main()
