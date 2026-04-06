# scripts/06_data_dictionary.py
# Generates the data dictionary Excel file documenting all fields,
# transformations, and cleaning decisions

import os
import pandas as pd

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data_dictionary.xlsx")

channels_fields = [
    ("channel_id",          "TEXT",    "Raw",     "Unique YouTube channel ID (starts with UC)",                          "None"),
    ("channel_name",        "TEXT",    "Raw",     "Human-readable channel name",                                         "None"),
    ("tier",                "TEXT",    "Derived", "Channel size tier: 'large' (500k+ subs) or 'small' (50k-500k subs)", "Manually assigned based on subscriber count"),
    ("subscriber_count",    "INTEGER", "Raw",     "Total subscribers at time of collection",                             "Cast from string to int; 0 if missing"),
    ("total_view_count",    "INTEGER", "Raw",     "All-time total views across channel",                                 "Cast from string to int"),
    ("total_video_count",   "INTEGER", "Raw",     "Total videos uploaded (includes Shorts/trailers)",                   "Cast from string to int"),
    ("channel_created_at",  "TEXT",    "Raw",     "ISO 8601 datetime channel was created",                              "Parsed to UTC datetime"),
    ("country",             "TEXT",    "Raw",     "Country code from channel snippet",                                   "Defaults to 'unknown' if absent"),
]

videos_fields = [
    ("video_id",           "TEXT",    "Raw",     "Unique YouTube video ID",                                              "None"),
    ("channel_id",         "TEXT",    "Raw",     "Parent channel ID (foreign key to channels)",                         "None"),
    ("channel_name",       "TEXT",    "Raw",     "Channel name (denormalized for convenience)",                         "None"),
    ("tier",               "TEXT",    "Derived", "Inherited tier from channel",                                         "Joined from channel metadata"),
    ("title",              "TEXT",    "Raw",     "Video title as published",                                             "None"),
    ("published_at",       "TEXT",    "Raw",     "ISO 8601 publish datetime",                                           "Parsed to UTC datetime"),
    ("duration_sec",       "REAL",    "Derived", "Video duration in total seconds",                                     "Parsed from ISO 8601 (e.g. PT2H3M10S) using isodate"),
    ("duration_min",       "REAL",    "Derived", "Video duration in minutes (rounded 1dp)",                            "duration_sec / 60"),
    ("duration_bucket",    "TEXT",    "Derived", "Duration category for bucketed analysis",                             "under_60 / 60_to_120 / 120_to_180 / 180_plus (minutes)"),
    ("view_count",         "INTEGER", "Raw",     "Total views at time of collection",                                   "Cast from string to int; 0 if missing"),
    ("like_count",         "INTEGER", "Raw",     "Total likes at time of collection",                                   "Cast from string to int; 0 if missing/disabled"),
    ("comment_count",      "INTEGER", "Raw",     "Total comments at time of collection",                                "Cast from string to int; 0 if disabled"),
    ("comments_disabled",  "INTEGER", "Derived", "1 if comments are disabled on this video, else 0",                   "Detected by absence of commentCount key in API response"),
    ("engagement_rate",    "REAL",    "Derived", "Interaction rate: (likes + comments) / views",                       "None if view_count = 0"),
    ("publish_year",       "INTEGER", "Derived", "Calendar year of publish date",                                       "Extracted from published_at"),
    ("publish_month",      "TEXT",    "Derived", "Year-month string (e.g. 2023-04)",                                   "Extracted from published_at as Period string"),
    ("days_since_publish", "INTEGER", "Derived", "Days between publish date and collection date",                       "Computed at ETL time using UTC today"),
    ("views_per_day",      "REAL",    "Derived", "Normalised view velocity: view_count / days_since_publish",          "days_since_publish floored to 1 to avoid division by zero"),
]

timeline_fields = [
    ("channel_name",  "TEXT",    "Derived", "Channel name",                                        "Grouped from videos table"),
    ("tier",          "TEXT",    "Derived", "Channel tier",                                        "Inherited from videos"),
    ("publish_month", "TEXT",    "Derived", "Year-month string (e.g. 2022-01)",                   "Grouped from publish_month in videos"),
    ("upload_count",  "INTEGER", "Derived", "Number of qualifying videos uploaded in that month", "Count of videos after Shorts/trailer filter"),
]

cleaning_decisions = [
    ("Filter: duration < 5 min",    "Removed 2,600 videos",  "Sub-5-minute uploads are Shorts, trailers, or clips — not D&D sessions. Keeping them would distort duration and engagement analysis."),
    ("Deduplication on video_id",   "0 duplicates found",    "No duplicates present in API response; check retained for reproducibility."),
    ("Null duration handling",       "0 rows dropped",        "All videos returned valid ISO 8601 durations; isodate parsed all successfully."),
    ("Missing engagement metrics",  "0 rows affected",       "All videos had view/like/comment counts. Comments disabled flagged separately rather than dropped."),
    ("Timezone normalization",       "All timestamps UTC",    "All published_at values converted to UTC to ensure consistent date arithmetic."),
    ("VibeCheckDND note",           "6 videos remain post-filter", "Channel posts primarily short-form content. Only 6 videos qualify as long-form. Results for this channel should be interpreted cautiously."),
]

def main():
    with pd.ExcelWriter(OUTPUT_PATH, engine="openpyxl") as writer:

        # Sheet 1: channels table
        pd.DataFrame(channels_fields,
                     columns=["Field","Type","Source","Description","Transformation"]
        ).to_excel(writer, sheet_name="channels", index=False)

        # Sheet 2: videos table
        pd.DataFrame(videos_fields,
                     columns=["Field","Type","Source","Description","Transformation"]
        ).to_excel(writer, sheet_name="videos", index=False)

        # Sheet 3: upload_timeline table
        pd.DataFrame(timeline_fields,
                     columns=["Field","Type","Source","Description","Transformation"]
        ).to_excel(writer, sheet_name="upload_timeline", index=False)

        # Sheet 4: cleaning decisions log
        pd.DataFrame(cleaning_decisions,
                     columns=["Decision","Impact","Justification"]
        ).to_excel(writer, sheet_name="cleaning_decisions", index=False)

    print(f"Data dictionary saved to: {os.path.abspath(OUTPUT_PATH)}")


if __name__ == "__main__":
    main()