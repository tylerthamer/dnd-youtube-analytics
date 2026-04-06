# scripts/04_eda.py
# Phase 5: Exploratory Data Analysis
# Produces summary stats and plots saved to reports/figures/

import os
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from scipy import stats

DB_PATH     = os.path.join(os.path.dirname(__file__), "..", "data", "db", "dnd_youtube.db")
FIGURES_DIR = os.path.join(os.path.dirname(__file__), "..", "reports", "figures")
os.makedirs(FIGURES_DIR, exist_ok=True)

# ── Consistent style ────────────────────────────────────────────────────────
sns.set_theme(style="whitegrid", palette="muted")
TIER_COLORS = {"large": "#4C72B0", "small": "#DD8452"}

def save_fig(name):
    path = os.path.join(FIGURES_DIR, name)
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {name}")

def load_data(conn):
    channels = pd.read_sql("SELECT * FROM channels", conn)
    videos   = pd.read_sql("SELECT * FROM videos",   conn)
    timeline = pd.read_sql("SELECT * FROM upload_timeline", conn)
    return channels, videos, timeline


# ════════════════════════════════════════════════════════════════════════════
# 1. SUMMARY STATISTICS
# ════════════════════════════════════════════════════════════════════════════
def summary_stats(channels, videos):
    print("\n=== SUMMARY STATISTICS ===")

    print("\n-- Channel-level --")
    print(channels[[
        "channel_name","tier","subscriber_count",
        "total_view_count","total_video_count"
    ]].to_string(index=False))

    print("\n-- Video-level numeric summary --")
    print(videos[[
        "duration_min","view_count","like_count",
        "comment_count","engagement_rate","views_per_day"
    ]].describe().round(2).to_string())

    print("\n-- Missingness --")
    print(videos.isnull().sum().to_string())

    print("\n-- Comments disabled --")
    disabled = videos["comments_disabled"].sum()
    print(f"  {disabled} videos ({disabled/len(videos)*100:.1f}%) have comments disabled")

    print("\n-- Duration bucket counts --")
    print(videos["duration_bucket"].value_counts().to_string())


# ════════════════════════════════════════════════════════════════════════════
# 2. DISTRIBUTION PLOTS
# ════════════════════════════════════════════════════════════════════════════
def plot_duration_distribution(videos):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("Video Duration Distribution", fontsize=14, fontweight="bold")

    # Histogram — all videos
    axes[0].hist(videos["duration_min"], bins=60, color="#4C72B0", edgecolor="white", linewidth=0.4)
    axes[0].set_xlabel("Duration (minutes)")
    axes[0].set_ylabel("Number of Videos")
    axes[0].set_title("All Channels Combined")
    axes[0].axvline(videos["duration_min"].median(), color="red",
                    linestyle="--", label=f'Median: {videos["duration_min"].median():.0f} min')
    axes[0].legend()

    # Box plot by channel
    order = (videos.groupby("channel_name")["duration_min"]
             .median().sort_values(ascending=False).index)
    tier_map = videos.drop_duplicates("channel_name").set_index("channel_name")["tier"]
    palette  = {ch: TIER_COLORS[tier_map[ch]] for ch in order}

    sns.boxplot(data=videos, x="channel_name", y="duration_min",
                order=order, palette=palette, ax=axes[1])
    axes[1].set_xlabel("")
    axes[1].set_ylabel("Duration (minutes)")
    axes[1].set_title("By Channel (sorted by median)")
    axes[1].tick_params(axis="x", rotation=35)

    # Legend for tier colours
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=TIER_COLORS["large"], label="Large"),
                       Patch(facecolor=TIER_COLORS["small"], label="Small")]
    axes[1].legend(handles=legend_elements, title="Tier")

    plt.tight_layout()
    save_fig("01_duration_distribution.png")


def plot_engagement_distribution(videos):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("Engagement Rate Distribution", fontsize=14, fontweight="bold")

    v = videos.dropna(subset=["engagement_rate"])
    # Cap at 99th percentile to avoid extreme outlier stretching the axis
    cap = v["engagement_rate"].quantile(0.99)
    v   = v[v["engagement_rate"] <= cap]

    axes[0].hist(v["engagement_rate"], bins=50, color="#DD8452", edgecolor="white", linewidth=0.4)
    axes[0].set_xlabel("Engagement Rate ((likes+comments)/views)")
    axes[0].set_ylabel("Number of Videos")
    axes[0].set_title("All Channels (capped at 99th pct)")

    sns.boxplot(data=v, x="tier", y="engagement_rate",
                palette=TIER_COLORS, ax=axes[1])
    axes[1].set_xlabel("Tier")
    axes[1].set_ylabel("Engagement Rate")
    axes[1].set_title("Large vs Small Channels")

    plt.tight_layout()
    save_fig("02_engagement_distribution.png")


def plot_view_distribution(videos):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("View Count Distribution", fontsize=14, fontweight="bold")

    axes[0].hist(videos["view_count"], bins=60, color="#55A868", edgecolor="white", linewidth=0.4)
    axes[0].set_xlabel("Views")
    axes[0].set_ylabel("Number of Videos")
    axes[0].set_title("All Channels (raw)")
    axes[0].xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/1e6:.1f}M"))

    # Log scale version — more informative for power-law distributions
    axes[1].hist(videos["view_count"], bins=60, color="#55A868", edgecolor="white", linewidth=0.4)
    axes[1].set_yscale("log")
    axes[1].set_xlabel("Views")
    axes[1].set_ylabel("Number of Videos (log scale)")
    axes[1].set_title("All Channels (log y-scale)")
    axes[1].xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/1e6:.1f}M"))

    plt.tight_layout()
    save_fig("03_view_distribution.png")


# ════════════════════════════════════════════════════════════════════════════
# 3. RELATIONSHIP ANALYSIS
# ════════════════════════════════════════════════════════════════════════════
def plot_duration_vs_engagement(videos):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("Duration vs Engagement Rate", fontsize=14, fontweight="bold")

    v = videos.dropna(subset=["engagement_rate"])
    cap = v["engagement_rate"].quantile(0.99)
    v   = v[v["engagement_rate"] <= cap]

    for ax, tier, label in zip(axes, ["large", "small"], ["Large Channels", "Small Channels"]):
        subset = v[v["tier"] == tier]
        ax.scatter(subset["duration_min"], subset["engagement_rate"],
                   alpha=0.3, s=12, color=TIER_COLORS[tier])

        # Trend line
        m, b, r, p, _ = stats.linregress(subset["duration_min"], subset["engagement_rate"])
        x_line = pd.Series([subset["duration_min"].min(), subset["duration_min"].max()])
        ax.plot(x_line, m * x_line + b, color="black", linewidth=1.5,
                label=f"r={r:.2f}, p={p:.3f}")

        ax.set_xlabel("Duration (minutes)")
        ax.set_ylabel("Engagement Rate")
        ax.set_title(label)
        ax.legend()

    plt.tight_layout()
    save_fig("04_duration_vs_engagement.png")


def plot_upload_timeline(timeline):
    fig, axes = plt.subplots(2, 1, figsize=(16, 10), sharex=False)
    fig.suptitle("Monthly Upload Frequency by Channel", fontsize=14, fontweight="bold")

    for ax, tier, label in zip(axes, ["large", "small"], ["Large Channels", "Small Channels"]):
        subset = timeline[timeline["tier"] == tier].copy()
        subset["publish_month"] = pd.to_datetime(subset["publish_month"])
        subset = subset.sort_values("publish_month")

        for channel in subset["channel_name"].unique():
            ch_data = subset[subset["channel_name"] == channel]
            ax.plot(ch_data["publish_month"], ch_data["upload_count"],
                    marker=".", linewidth=1, markersize=4, label=channel)

        ax.set_ylabel("Uploads per Month")
        ax.set_title(label)
        ax.legend(loc="upper left", fontsize=8)
        ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%Y"))

    plt.tight_layout()
    save_fig("05_upload_timeline.png")


def plot_engagement_by_bucket(videos):
    v = videos.dropna(subset=["engagement_rate"])
    cap = v["engagement_rate"].quantile(0.99)
    v   = v[v["engagement_rate"] <= cap]

    bucket_order = ["under_60", "60_to_120", "120_to_180", "180_plus"]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("Engagement Rate by Duration Bucket", fontsize=14, fontweight="bold")

    for ax, tier, label in zip(axes, ["large", "small"], ["Large Channels", "Small Channels"]):
        subset = v[v["tier"] == tier]
        sns.boxplot(data=subset, x="duration_bucket", y="engagement_rate",
                    order=bucket_order, color=TIER_COLORS[tier], ax=ax)
        ax.set_xlabel("Duration Bucket")
        ax.set_ylabel("Engagement Rate")
        ax.set_title(label)
        ax.tick_params(axis="x", rotation=20)

    plt.tight_layout()
    save_fig("06_engagement_by_bucket.png")


def plot_correlation_heatmap(videos):
    cols = ["duration_min", "view_count", "like_count",
            "comment_count", "engagement_rate", "views_per_day"]
    corr = videos[cols].corr()

    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm",
                center=0, ax=ax, square=True, linewidths=0.5)
    ax.set_title("Correlation Matrix — Video Metrics", fontsize=13, fontweight="bold")
    plt.tight_layout()
    save_fig("07_correlation_heatmap.png")


# ════════════════════════════════════════════════════════════════════════════
# 4. KEY INSIGHT SUMMARY (printed)
# ════════════════════════════════════════════════════════════════════════════
def print_key_insights(videos, timeline):
    print("\n=== KEY INSIGHTS ===")

    # Insight 1: engagement by tier
    eng = videos.dropna(subset=["engagement_rate"]).groupby("tier")["engagement_rate"].mean()
    print(f"\n1. Avg engagement rate — large: {eng['large']:.4f} | small: {eng['small']:.4f}")
    t, p = stats.ttest_ind(
        videos[videos["tier"]=="large"]["engagement_rate"].dropna(),
        videos[videos["tier"]=="small"]["engagement_rate"].dropna()
    )
    print(f"   t-test: t={t:.3f}, p={p:.4f} ({'significant' if p < 0.05 else 'not significant'})")

    # Insight 2: avg duration by tier
    dur = videos.groupby("tier")["duration_min"].mean()
    print(f"\n2. Avg video duration — large: {dur['large']:.1f} min | small: {dur['small']:.1f} min")

    # Insight 3: avg monthly uploads by tier
    uploads = timeline.groupby("tier")["upload_count"].mean()
    print(f"\n3. Avg monthly uploads — large: {uploads['large']:.2f} | small: {uploads['small']:.2f}")

    # Insight 4: duration vs engagement correlation
    v = videos.dropna(subset=["engagement_rate"])
    r, p = stats.pearsonr(v["duration_min"], v["engagement_rate"])
    print(f"\n4. Duration vs engagement correlation: r={r:.3f}, p={p:.4f}")

    # Insight 5: best performing duration bucket by avg views
    bucket_views = videos.groupby("duration_bucket")["view_count"].mean().sort_values(ascending=False)
    print(f"\n5. Avg views by duration bucket:")
    print(bucket_views.round(0).to_string())


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 60)
    print("PHASE 5 -- EDA")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    channels, videos, timeline = load_data(conn)
    conn.close()

    summary_stats(channels, videos)

    print("\nGenerating plots...")
    plot_duration_distribution(videos)
    plot_engagement_distribution(videos)
    plot_view_distribution(videos)
    plot_duration_vs_engagement(videos)
    plot_upload_timeline(timeline)
    plot_engagement_by_bucket(videos)
    plot_correlation_heatmap(videos)

    print_key_insights(videos, timeline)

    print(f"\nAll figures saved to: {os.path.abspath(FIGURES_DIR)}")
    print("Done.")


if __name__ == "__main__":
    main()