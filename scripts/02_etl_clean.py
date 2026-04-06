# scripts/02_etl_clean.py
# Phase 3: ETL & Cleaning
# Reads raw JSON from data/raw/, cleans and transforms it,
# and saves cleaned CSVs to data/cleaned/
# Raw files are never modified.

import os
import json
import isodate
import pandas as pd
from datetime import datetime, timezone

RAW_DIR   = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
CLEAN_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "cleaned")
os.makedirs(CLEAN_DIR, exist_ok=True)

CHANNELS = [
    {"name": "Critical Role",         "slug": "critical_role",         "tier": "large"},
    {"name": "Dimension 20",           "slug": "dimension_20",           "tier": "large"},
    {"name": "Legends of Avantris",    "slug": "legends_of_avantris",    "tier": "large"},
    {"name": "High Rollers DnD",       "slug": "high_rollers_dnd",       "tier": "large"},
    {"name": "Narrative Declaration",  "slug": "narrative_declaration",  "tier": "small"},
    {"name": "Unexpectables",          "slug": "unexpectables",          "tier": "small"},
    {"name": "VibeCheckDND",           "slug": "vibecheckdnd",           "tier": "small"},
    {"name": "Just Roll With It",      "slug": "just_roll_with_it",      "tier": "small"},
]


# ── Helper: safely cast to int (some counts are missing/disabled) ──────────
def safe_int(val, default=0):
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


# ── Helper: parse ISO 8601 duration to total seconds ──────────────────────
def parse_duration(iso_str):
    try:
        return int(isodate.parse_duration(iso_str).total_seconds())
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
# PART 1 — Build channels DataFrame
# ══════════════════════════════════════════════════════════════════════════════
def build_channels_df():
    rows = []
    for ch in CHANNELS:
        path = os.path.join(RAW_DIR, f"{ch['slug']}_channel.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        item  = data["items"][0]
        stats = item["statistics"]
        snip  = item["snippet"]

        rows.append({
            "channel_id":         item["id"],
            "channel_name":       ch["name"],
            "tier":               ch["tier"],
            "subscriber_count":   safe_int(stats.get("subscriberCount")),
            "total_view_count":   safe_int(stats.get("viewCount")),
            "total_video_count":  safe_int(stats.get("videoCount")),
            "channel_created_at": pd.to_datetime(snip["publishedAt"], utc=True),
            "country":            snip.get("country", "unknown"),
        })

    df = pd.DataFrame(rows)
    print(f"Channels: {len(df)} rows")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# PART 2 — Build videos DataFrame
# ══════════════════════════════════════════════════════════════════════════════
def build_videos_df():
    all_rows = []

    for ch in CHANNELS:
        path = os.path.join(RAW_DIR, f"{ch['slug']}_videos.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        for v in data["videos"]:
            snip  = v.get("snippet",        {})
            stats = v.get("statistics",     {})
            cdet  = v.get("contentDetails", {})

            duration_sec = parse_duration(cdet.get("duration", ""))
            view_count   = safe_int(stats.get("viewCount"))
            like_count   = safe_int(stats.get("likeCount"))
            comment_count = safe_int(stats.get("commentCount"))

            # comments disabled when key is absent entirely
            comments_disabled = "commentCount" not in stats

            # engagement rate: (likes + comments) / views  — avoid div/0
            if view_count > 0:
                engagement_rate = (like_count + comment_count) / view_count
            else:
                engagement_rate = None

            all_rows.append({
                "video_id":           v["id"],
                "channel_id":         snip.get("channelId"),
                "channel_name":       ch["name"],
                "tier":               ch["tier"],
                "title":              snip.get("title", ""),
                "published_at":       pd.to_datetime(snip.get("publishedAt"), utc=True),
                "duration_sec":       duration_sec,
                "view_count":         view_count,
                "like_count":         like_count,
                "comment_count":      comment_count,
                "comments_disabled":  comments_disabled,
                "engagement_rate":    engagement_rate,
            })

    df = pd.DataFrame(all_rows)
    print(f"Videos (raw): {len(df)} rows")
    return df


# ══════════════════════════════════════════════════════════════════════════════
# PART 3 — Clean the videos DataFrame
# ══════════════════════════════════════════════════════════════════════════════
def clean_videos(df):
    original_count = len(df)

    # ── Drop rows with missing duration (unparseable) ──────────────────────
    df = df.dropna(subset=["duration_sec"])
    print(f"  After dropping null duration: {len(df)} rows")

    # ── Drop duplicates by video_id ────────────────────────────────────────
    df = df.drop_duplicates(subset=["video_id"])
    print(f"  After dropping duplicates: {len(df)} rows")

    # ── Filter out Shorts and trailers: keep videos >= 5 minutes (300 sec) ─
    # D&D content is long-form; sub-5-min uploads are clips/trailers/shorts
    df = df[df["duration_sec"] >= 300]
    print(f"  After filtering shorts/trailers (<5 min): {len(df)} rows")

    # ── Add derived columns ────────────────────────────────────────────────

    # Duration in minutes (easier to read)
    df["duration_min"] = (df["duration_sec"] / 60).round(1)

    # Duration bucket for Q2 analysis
    def duration_bucket(mins):
        if mins < 60:   return "under_60"
        if mins < 120:  return "60_to_120"
        if mins < 180:  return "120_to_180"
        return "180_plus"

    df["duration_bucket"] = df["duration_min"].apply(duration_bucket)

    # Publish year and month for timeline analysis
    df["publish_year"]  = df["published_at"].dt.year
    df["publish_month"] = df["published_at"].dt.to_period("M").astype(str)

    # Views per day (normalises older vs newer videos)
    today = pd.Timestamp.now(tz="UTC")
    df["days_since_publish"] = (today - df["published_at"]).dt.days
    df["views_per_day"] = (
        df["view_count"] / df["days_since_publish"].replace(0, 1)
    ).round(2)

    print(f"\nCleaning summary: {original_count} raw -> {len(df)} cleaned rows")
    print(f"Removed: {original_count - len(df)} rows")
    return df.reset_index(drop=True)


# ══════════════════════════════════════════════════════════════════════════════
# PART 4 — Build upload timeline DataFrame
# ══════════════════════════════════════════════════════════════════════════════
def build_timeline(df):
    # Count uploads per channel per month
    timeline = (
        df.groupby(["channel_name", "tier", "publish_month"])
        .size()
        .reset_index(name="upload_count")
    )
    print(f"Timeline: {len(timeline)} rows")
    return timeline


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 60)
    print("PHASE 3 — ETL & Cleaning")
    print("=" * 60)

    # Build
    channels_df = build_channels_df()
    videos_raw  = build_videos_df()

    # Clean
    print("\nCleaning videos...")
    videos_clean = clean_videos(videos_raw)

    # Timeline
    print("\nBuilding upload timeline...")
    timeline_df = build_timeline(videos_clean)

    # Save
    channels_path = os.path.join(CLEAN_DIR, "channels.csv")
    videos_path   = os.path.join(CLEAN_DIR, "videos.csv")
    timeline_path = os.path.join(CLEAN_DIR, "upload_timeline.csv")

    channels_df.to_csv(channels_path,  index=False)
    videos_clean.to_csv(videos_path,   index=False)
    timeline_df.to_csv(timeline_path,  index=False)

    print(f"\nSaved:")
    print(f"  {channels_path}")
    print(f"  {videos_path}")
    print(f"  {timeline_path}")

    # Quick sanity check
    print("\n--- Channels summary ---")
    print(channels_df[["channel_name", "tier", "subscriber_count", "total_video_count"]].to_string(index=False))

    print("\n--- Videos per channel (cleaned) ---")
    print(videos_clean.groupby(["channel_name", "tier"]).size().reset_index(name="video_count").to_string(index=False))

    print("\n--- Duration bucket distribution ---")
    print(videos_clean["duration_bucket"].value_counts().to_string())

    print("\nDone.")


if __name__ == "__main__":
    main()