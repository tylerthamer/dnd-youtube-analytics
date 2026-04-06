# scripts/05_analysis.py
# Phase 6: Information Extraction
# Answers the three analytics questions from the proposal:
#   Q1: Does upload frequency correlate with growth?
#   Q2: Does video length affect engagement?
#   Q3: What content patterns separate large from small channels?

import os
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from scipy import stats
import numpy as np

DB_PATH     = os.path.join(os.path.dirname(__file__), "..", "data", "db", "dnd_youtube.db")
FIGURES_DIR = os.path.join(os.path.dirname(__file__), "..", "reports", "figures")
os.makedirs(FIGURES_DIR, exist_ok=True)

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
# Q1: Does upload frequency correlate with channel growth?
# Approach: compute avg monthly uploads per channel, compare to subscriber
# count and total views. Also plot cumulative upload timeline.
# ════════════════════════════════════════════════════════════════════════════
def q1_upload_frequency_vs_growth(channels, timeline):
    print("\n" + "="*60)
    print("Q1: Upload Frequency vs Channel Growth")
    print("="*60)

    # Avg monthly uploads per channel
    avg_uploads = (timeline.groupby("channel_name")["upload_count"]
                   .mean().reset_index()
                   .rename(columns={"upload_count": "avg_monthly_uploads"}))

    df = channels.merge(avg_uploads, on="channel_name")

    print("\n-- Avg monthly uploads vs subscriber count --")
    print(df[["channel_name","tier","avg_monthly_uploads","subscriber_count"]].to_string(index=False))

    # Correlation: uploads vs subscribers
    r_subs, p_subs = stats.pearsonr(df["avg_monthly_uploads"], df["subscriber_count"])
    r_views, p_views = stats.pearsonr(df["avg_monthly_uploads"], df["total_view_count"])
    print(f"\nPearson r (uploads vs subscribers): r={r_subs:.3f}, p={p_subs:.3f}")
    print(f"Pearson r (uploads vs total views):  r={r_views:.3f}, p={p_views:.3f}")

    # ── Plot 1: scatter uploads vs subscribers ─────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("Q1: Does Upload Frequency Drive Growth?", fontsize=13, fontweight="bold")

    for ax, metric, label in zip(
        axes,
        ["subscriber_count", "total_view_count"],
        ["Subscriber Count", "Total View Count"]
    ):
        for _, row in df.iterrows():
            ax.scatter(row["avg_monthly_uploads"], row[metric],
                       color=TIER_COLORS[row["tier"]], s=120, zorder=3)
            ax.annotate(row["channel_name"].split()[0],
                        (row["avg_monthly_uploads"], row[metric]),
                        fontsize=7, ha="left", va="bottom",
                        xytext=(4, 4), textcoords="offset points")

        m, b, r, p, _ = stats.linregress(df["avg_monthly_uploads"], df[metric])
        x_line = np.linspace(df["avg_monthly_uploads"].min(),
                             df["avg_monthly_uploads"].max(), 100)
        ax.plot(x_line, m*x_line + b, color="black", linewidth=1.5, linestyle="--",
                label=f"r={r:.2f}, p={p:.3f}")
        ax.set_xlabel("Avg Monthly Uploads")
        ax.set_ylabel(label)
        ax.set_title(f"Uploads vs {label}")
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x/1e6:.1f}M"))
        ax.legend()

    from matplotlib.patches import Patch
    legend_els = [Patch(facecolor=TIER_COLORS["large"], label="Large"),
                  Patch(facecolor=TIER_COLORS["small"], label="Small")]
    axes[0].legend(handles=legend_els + [plt.Line2D([0],[0], color="black",
                   linestyle="--", label=f"r={r_subs:.2f}")], fontsize=8)

    plt.tight_layout()
    save_fig("08_q1_uploads_vs_growth.png")

    # ── Plot 2: cumulative uploads over time ───────────────────────────────
    fig, axes = plt.subplots(2, 1, figsize=(16, 10))
    fig.suptitle("Q1: Cumulative Upload Volume Over Time", fontsize=13, fontweight="bold")

    for ax, tier, label in zip(axes, ["large", "small"], ["Large Channels", "Small Channels"]):
        subset = timeline[timeline["tier"] == tier].copy()
        subset["publish_month"] = pd.to_datetime(subset["publish_month"])
        subset = subset.sort_values(["channel_name", "publish_month"])

        for ch in subset["channel_name"].unique():
            ch_data = subset[subset["channel_name"] == ch].copy()
            ch_data["cumulative"] = ch_data["upload_count"].cumsum()
            ax.plot(ch_data["publish_month"], ch_data["cumulative"],
                    linewidth=2, label=ch)

        ax.set_ylabel("Cumulative Uploads")
        ax.set_title(label)
        ax.legend(fontsize=8)
        ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter("%Y"))

    plt.tight_layout()
    save_fig("09_q1_cumulative_uploads.png")

    return df


# ════════════════════════════════════════════════════════════════════════════
# Q2: Does video length affect engagement?
# Approach: bucket analysis + ANOVA across buckets + per-channel breakdown
# ════════════════════════════════════════════════════════════════════════════
def q2_duration_vs_engagement(videos):
    print("\n" + "="*60)
    print("Q2: Video Length vs Engagement")
    print("="*60)

    v = videos.dropna(subset=["engagement_rate"])
    bucket_order = ["under_60", "60_to_120", "120_to_180", "180_plus"]

    # Summary stats per bucket
    bucket_stats = (v.groupby("duration_bucket")["engagement_rate"]
                    .agg(["mean","median","std","count"])
                    .reindex(bucket_order).round(4))
    print("\n-- Engagement rate by duration bucket --")
    print(bucket_stats.to_string())

    # ANOVA — are differences statistically significant?
    groups = [v[v["duration_bucket"]==b]["engagement_rate"].values for b in bucket_order]
    f_stat, p_val = stats.f_oneway(*groups)
    print(f"\nOne-way ANOVA: F={f_stat:.3f}, p={p_val:.6f}")
    print(f"Result: {'Significant difference between buckets' if p_val < 0.05 else 'No significant difference'}")

    # Also: avg views per bucket
    bucket_views = (v.groupby("duration_bucket")["view_count"]
                    .mean().reindex(bucket_order).round(0))
    print("\n-- Avg views by duration bucket --")
    print(bucket_views.to_string())

    # ── Plot: engagement + views by bucket, split by tier ─────────────────
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Q2: How Does Video Length Affect Performance?",
                 fontsize=13, fontweight="bold")

    metrics = [
        ("engagement_rate", "Engagement Rate", axes[0][0], axes[0][1]),
        ("view_count",       "View Count",      axes[1][0], axes[1][1]),
    ]

    for metric, ylabel, ax_large, ax_small in metrics:
        for ax, tier, label in zip(
            [ax_large, ax_small], ["large","small"], ["Large Channels","Small Channels"]
        ):
            subset = v[v["tier"] == tier]
            means  = (subset.groupby("duration_bucket")[metric]
                      .mean().reindex(bucket_order))
            ax.bar(bucket_order, means.values, color=TIER_COLORS[tier], edgecolor="white")
            ax.set_title(f"{label} — {ylabel}")
            ax.set_xlabel("Duration Bucket")
            ax.set_ylabel(ylabel)
            ax.tick_params(axis="x", rotation=20)
            if metric == "view_count":
                ax.yaxis.set_major_formatter(
                    mticker.FuncFormatter(lambda x, _: f"{x/1e3:.0f}K"))

    plt.tight_layout()
    save_fig("10_q2_length_vs_performance.png")

    # ── Plot: scatter duration vs engagement per channel ──────────────────
    channels_list = v["channel_name"].unique()
    n = len(channels_list)
    fig, axes = plt.subplots(2, 4, figsize=(18, 8), sharey=False)
    fig.suptitle("Q2: Duration vs Engagement Rate — Per Channel",
                 fontsize=13, fontweight="bold")

    for ax, ch in zip(axes.flat, channels_list):
        subset = v[v["channel_name"] == ch]
        tier   = subset["tier"].iloc[0]
        cap    = subset["engagement_rate"].quantile(0.99)
        subset = subset[subset["engagement_rate"] <= cap]

        ax.scatter(subset["duration_min"], subset["engagement_rate"],
                   alpha=0.4, s=15, color=TIER_COLORS[tier])

        if len(subset) > 2:
            m, b, r, p, _ = stats.linregress(
                subset["duration_min"], subset["engagement_rate"])
            x_line = np.linspace(subset["duration_min"].min(),
                                 subset["duration_min"].max(), 100)
            ax.plot(x_line, m*x_line+b, color="black", linewidth=1.2,
                    label=f"r={r:.2f}")
            ax.legend(fontsize=7)

        ax.set_title(ch, fontsize=8, fontweight="bold")
        ax.set_xlabel("Duration (min)", fontsize=7)
        ax.set_ylabel("Engagement", fontsize=7)

    plt.tight_layout()
    save_fig("11_q2_per_channel_scatter.png")


# ════════════════════════════════════════════════════════════════════════════
# Q3: What patterns separate large from small channels?
# Approach: full comparative tier profile across all key metrics
# ════════════════════════════════════════════════════════════════════════════
def q3_tier_profile(channels, videos, timeline):
    print("\n" + "="*60)
    print("Q3: Content Strategy Profile — Large vs Small")
    print("="*60)

    v = videos.dropna(subset=["engagement_rate"])

    # Build comprehensive profile
    profile = v.groupby("tier").agg(
        avg_duration_min    = ("duration_min",     "mean"),
        median_duration_min = ("duration_min",     "median"),
        avg_engagement_rate = ("engagement_rate",  "mean"),
        avg_view_count      = ("view_count",       "mean"),
        median_view_count   = ("view_count",       "median"),
        avg_views_per_day   = ("views_per_day",    "mean"),
        video_count         = ("video_id",         "count"),
    ).round(2)

    avg_uploads = timeline.groupby("tier")["upload_count"].mean().round(2)
    profile["avg_monthly_uploads"] = avg_uploads

    print("\n-- Tier profile --")
    print(profile.T.to_string())

    # Bucket share by tier
    print("\n-- Duration bucket share by tier (%) --")
    bucket_share = (v.groupby(["tier","duration_bucket"])
                    .size().unstack().fillna(0))
    bucket_share_pct = bucket_share.div(bucket_share.sum(axis=1), axis=0).round(3) * 100
    print(bucket_share_pct.to_string())

    # ── Plot: radar-style grouped bar comparison ───────────────────────────
    metrics_norm = {
        "Avg Duration (min)":    ("avg_duration_min",    None),
        "Avg Engagement Rate":   ("avg_engagement_rate", None),
        "Avg Views":             ("avg_view_count",      None),
        "Monthly Uploads":       ("avg_monthly_uploads", None),
    }

    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    fig.suptitle("Q3: Large vs Small Channel Comparison", fontsize=13, fontweight="bold")

    for ax, (title, (col, _)) in zip(axes.flat, metrics_norm.items()):
        vals  = [profile.loc["large", col], profile.loc["small", col]]
        bars  = ax.bar(["Large", "Small"], vals,
                       color=[TIER_COLORS["large"], TIER_COLORS["small"]],
                       edgecolor="white", width=0.5)
        ax.set_title(title)
        ax.set_ylabel(title)
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2,
                    bar.get_height() * 1.02,
                    f"{val:,.1f}", ha="center", va="bottom", fontsize=10)

    plt.tight_layout()
    save_fig("12_q3_tier_comparison.png")

    # ── Plot: duration bucket share side by side ───────────────────────────
    bucket_order = ["under_60", "60_to_120", "120_to_180", "180_plus"]
    x = np.arange(len(bucket_order))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x - width/2,
           [bucket_share_pct.loc["large", b] for b in bucket_order],
           width, label="Large", color=TIER_COLORS["large"])
    ax.bar(x + width/2,
           [bucket_share_pct.loc["small", b] for b in bucket_order],
           width, label="Small", color=TIER_COLORS["small"])

    ax.set_xticks(x)
    ax.set_xticklabels(bucket_order)
    ax.set_ylabel("% of Videos")
    ax.set_title("Q3: Duration Bucket Share — Large vs Small")
    ax.legend()
    plt.tight_layout()
    save_fig("13_q3_duration_bucket_share.png")


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 60)
    print("PHASE 6 -- Information Extraction")
    print("=" * 60)

    conn = sqlite3.connect(DB_PATH)
    channels, videos, timeline = load_data(conn)
    conn.close()

    q1_upload_frequency_vs_growth(channels, timeline)
    q2_duration_vs_engagement(videos)
    q3_tier_profile(channels, videos, timeline)

    print(f"\nAll figures saved to: {os.path.abspath(FIGURES_DIR)}")
    print("\nDone.")


if __name__ == "__main__":
    main()