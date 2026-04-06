# scripts/03_load_db.py
# Phase 4: Storage
# Loads cleaned CSVs into a SQLite database with 3 tables:
#   - channels
#   - videos
#   - upload_timeline
# Validates with row counts and sample queries

import os
import sqlite3
import pandas as pd

CLEAN_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "cleaned")
DB_DIR    = os.path.join(os.path.dirname(__file__), "..", "data", "db")
DB_PATH   = os.path.join(DB_DIR, "dnd_youtube.db")
os.makedirs(DB_DIR, exist_ok=True)


def load_csvs():
    channels = pd.read_csv(os.path.join(CLEAN_DIR, "channels.csv"))
    videos   = pd.read_csv(os.path.join(CLEAN_DIR, "videos.csv"))
    timeline = pd.read_csv(os.path.join(CLEAN_DIR, "upload_timeline.csv"))
    return channels, videos, timeline


def create_schema(conn):
    conn.executescript("""
        DROP TABLE IF EXISTS upload_timeline;
        DROP TABLE IF EXISTS videos;
        DROP TABLE IF EXISTS channels;

        CREATE TABLE channels (
            channel_id          TEXT PRIMARY KEY,
            channel_name        TEXT NOT NULL,
            tier                TEXT NOT NULL,
            subscriber_count    INTEGER,
            total_view_count    INTEGER,
            total_video_count   INTEGER,
            channel_created_at  TEXT,
            country             TEXT
        );

        CREATE TABLE videos (
            video_id            TEXT PRIMARY KEY,
            channel_id          TEXT NOT NULL,
            channel_name        TEXT NOT NULL,
            tier                TEXT NOT NULL,
            title               TEXT,
            published_at        TEXT,
            duration_sec        REAL,
            duration_min        REAL,
            duration_bucket     TEXT,
            view_count          INTEGER,
            like_count          INTEGER,
            comment_count       INTEGER,
            comments_disabled   INTEGER,
            engagement_rate     REAL,
            publish_year        INTEGER,
            publish_month       TEXT,
            days_since_publish  INTEGER,
            views_per_day       REAL,
            FOREIGN KEY (channel_id) REFERENCES channels(channel_id)
        );

        CREATE TABLE upload_timeline (
            channel_name    TEXT NOT NULL,
            tier            TEXT NOT NULL,
            publish_month   TEXT NOT NULL,
            upload_count    INTEGER NOT NULL,
            PRIMARY KEY (channel_name, publish_month)
        );
    """)
    conn.commit()
    print("Schema created.")


def insert_data(conn, channels, videos, timeline):
    channels.to_sql("channels",        conn, if_exists="append", index=False)
    videos.to_sql("videos",            conn, if_exists="append", index=False)
    timeline.to_sql("upload_timeline", conn, if_exists="append", index=False)
    conn.commit()
    print("Data inserted.")


def validate(conn):
    print("\n--- Validation: row counts ---")
    for table in ["channels", "videos", "upload_timeline"]:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count} rows")

    print("\n--- Sample Query 1: Avg engagement rate by tier ---")
    q1 = conn.execute("""
        SELECT tier,
               ROUND(AVG(engagement_rate), 4) AS avg_engagement,
               COUNT(*)                        AS video_count
        FROM   videos
        WHERE  engagement_rate IS NOT NULL
        GROUP  BY tier
        ORDER  BY avg_engagement DESC
    """)
    for row in q1.fetchall():
        print(f"  {row}")

    print("\n--- Sample Query 2: Top 5 most viewed videos ---")
    q2 = conn.execute("""
        SELECT channel_name, title, view_count, duration_min
        FROM   videos
        ORDER  BY view_count DESC
        LIMIT  5
    """)
    for row in q2.fetchall():
        print(f"  {row}")

    print("\n--- Sample Query 3: Avg video duration by channel ---")
    q3 = conn.execute("""
        SELECT channel_name,
               tier,
               ROUND(AVG(duration_min), 1) AS avg_duration_min,
               COUNT(*)                    AS video_count
        FROM   videos
        GROUP  BY channel_name
        ORDER  BY avg_duration_min DESC
    """)
    for row in q3.fetchall():
        print(f"  {row}")

    print("\n--- Sample Query 4: Upload counts by tier (all time) ---")
    q4 = conn.execute("""
        SELECT tier,
               SUM(upload_count)            AS total_uploads,
               ROUND(AVG(upload_count), 2)  AS avg_monthly_uploads
        FROM   upload_timeline
        GROUP  BY tier
    """)
    for row in q4.fetchall():
        print(f"  {row}")


def main():
    print("=" * 60)
    print("PHASE 4 -- SQLite Storage")
    print("=" * 60)

    print("\nLoading cleaned CSVs...")
    channels, videos, timeline = load_csvs()

    print(f"  channels:  {len(channels)} rows")
    print(f"  videos:    {len(videos)} rows")
    print(f"  timeline:  {len(timeline)} rows")

    print(f"\nConnecting to {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)

    create_schema(conn)
    insert_data(conn, channels, videos, timeline)
    validate(conn)

    conn.close()
    print(f"\nDatabase saved to: {os.path.abspath(DB_PATH)}")
    print("Done.")


if __name__ == "__main__":
    main()