# D&D on YouTube: Dissecting Channel Growth and Content Strategy

**COSC 301 | Tyler Thamer | April 2026**

A full end-to-end data analytics pipeline analyzing 8 Dungeons & Dragons
YouTube channels to understand what separates large channels from small ones.

---

## Research Questions

1. Do channels grow faster from more frequent uploads?
2. Does video length affect engagement (likes, comments, views)?
3. What content patterns separate large channels from small channels?

---

## Key Findings

- **Upload frequency does not drive growth** (r=0.26, p=0.534). The most
  prolific channel (Unexpectables, 13.6 uploads/month) has only 26,500
  subscribers while less frequent channels have millions.
- **Longer videos get fewer interactions** but more total views. Engagement
  rate drops consistently from 4.8% (under 60 min) to 2.4% (180+ min),
  yet 180+ minute videos average the most views (518k).
- **Upload cadence is nearly identical** across tiers (6.44 vs 6.64
  uploads/month), meaning frequency alone does not explain channel size.
- **Small channels go even longer** than large ones (191.6 min avg vs
  155.5 min), with 63.5% of their videos exceeding 3 hours.

---

## Dataset

| Source | YouTube Data API v3 |
|---|---|
| License | YouTube API Terms of Service (public metadata, non-commercial research) |
| Channels | 8 D&D actual-play channels (4 large, 4 small) |
| Videos | 3,246 qualifying videos (filtered from 5,846 raw) |
| Collected | April 2026 |

**Large channels (500k+ subscribers):**
Critical Role, Dimension 20, Legends of Avantris, High Rollers DnD

**Small channels (50k–500k subscribers):**
Narrative Declaration, Unexpectables, VibeCheckDND, Just Roll With It

---

## Tools Used

| Tool | Role |
|---|---|
| Python (pandas, google-api-python-client, isodate, matplotlib, seaborn, scipy) | API collection, ETL, EDA, analysis, visualization |
| SQLite | Cleaned data storage and SQL querying |
| Excel | Data dictionary |
| Tableau Public | Dashboard (see reports/ — publishing blocked by Tableau bug) |

---

## Project Structure
dnd-youtube-analytics/
├── data/
│   ├── raw/              <- raw JSON from YouTube API (not in repo — see below)
│   ├── cleaned/          <- processed CSVs (channels, videos, upload_timeline)
│   └── db/               <- SQLite database (dnd_youtube.db)
├── notebooks/            <- (reserved for future exploration)
├── scripts/
│   ├── 01_collect_data.py       <- Phase 2: API data collection
│   ├── 02_etl_clean.py          <- Phase 3: ETL and cleaning
│   ├── 03_load_db.py            <- Phase 4: SQLite storage
│   ├── 04_eda.py                <- Phase 5: Exploratory data analysis
│   ├── 05_analysis.py           <- Phase 6: Information extraction (Q1/Q2/Q3)
│   └── 06_data_dictionary.py    <- Phase 7: Data dictionary generator
├── reports/
│   ├── figures/          <- all 13 generated plots (PNG)
│   └── dnd_youtube_dashboard.twbx  <- Tableau workbook
├── data_dictionary.xlsx
├── requirements.txt
└── README.md

---
## How to Reproduce

### 1. Clone the repo
```bash
git clone YOUR_REPO_LINK_HERE
cd dnd-youtube-analytics
```

### 2. Install dependencies
```bash
python -m pip install -r requirements.txt
```

### 3. Add your API key
Create a `.env` file in the root folder: "YOUTUBE_API_KEY=AIzaSyA7Qzfw4tFr8TZaDUb5ErkBSirkcP42OtA"

### 4. Run the pipeline in order
```bash
python scripts/01_collect_data.py    # collect raw data (~5 min)
python scripts/02_etl_clean.py       # clean and transform
python scripts/03_load_db.py         # load into SQLite
python scripts/04_eda.py             # EDA + figures 01-07
python scripts/05_analysis.py        # analysis + figures 08-13
python scripts/06_data_dictionary.py # generate data dictionary
```

All outputs will be saved automatically to their respective folders.

> **Note:** `data/raw/` is excluded from this repo (large JSON files).
> Re-running `01_collect_data.py` with a valid API key will regenerate it.

---

## Figures

| File | Description |
|---|---|
| 01_duration_distribution.png | Video duration histogram + box plot by channel |
| 02_engagement_distribution.png | Engagement rate distribution + tier comparison |
| 03_view_distribution.png | View count distribution (raw + log scale) |
| 04_duration_vs_engagement.png | Scatter: duration vs engagement by tier |
| 05_upload_timeline.png | Monthly upload frequency over time |
| 06_engagement_by_bucket.png | Engagement rate by duration bucket |
| 07_correlation_heatmap.png | Correlation matrix of all video metrics |
| 08_q1_uploads_vs_growth.png | Q1: upload frequency vs subscriber/view count |
| 09_q1_cumulative_uploads.png | Q1: cumulative uploads over time by channel |
| 10_q2_length_vs_performance.png | Q2: avg engagement + views by duration bucket |
| 11_q2_per_channel_scatter.png | Q2: duration vs engagement per channel |
| 12_q3_tier_comparison.png | Q3: key metrics large vs small |
| 13_q3_duration_bucket_share.png | Q3: duration bucket share by tier |

---

## Limitations

- English-language channels only; findings may not generalize beyond this sample
- VibeCheckDND only had 6 qualifying long-form videos — results for this
  channel should be interpreted with caution
- Subscriber counts are a snapshot in time, not longitudinal growth data
- Comments disabled on 0 videos in this sample, but like/comment counts
  may still be suppressed on some videos without being flagged by the API
- Sample size of 8 channels is small for channel-level correlations (Q1)

---

## Ethics & Disclosure

- Only public API metadata collected — no user data, no comment contents
- Fully compliant with YouTube API Terms of Service
- Large vs small comparisons reflect statistical patterns only, not quality judgments
- AI disclosure: Claude assisted with code structure and project guidance.
  All analysis, interpretation, and written findings are the student's own work.

---

## References

- Google Developers. YouTube Data API v3. https://developers.google.com/youtube/v3
- YouTube API Terms of Service. https://developers.google.com/youtube/terms/api-services-tos
- isodate Python library. https://pypi.org/project/isodate/

---

*Published at: [Tyler Thamer's DND YouTube Analytics Github](https://github.com/tylerthamer/dnd-youtube-analytics.git)*
