"""Chart generator — creates comparison charts from CSV experiment results.

Generates publication-quality figures from actual experimental data.
Does NOT generate fake charts or fabricate results.
"""

import logging
import os
from typing import Dict, List, Optional

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import seaborn as sns

logger = logging.getLogger(__name__)

# Publication style
plt.rcParams.update({
    "figure.dpi": 150,
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "legend.fontsize": 10,
    "figure.figsize": (8, 5),
})


class ChartGenerator:
    """Generates charts from CSV result files."""

    def __init__(self, output_dir: str = "results/figures"):
        self._output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def comparison_bar_chart(
        self,
        csv_path: str,
        metrics: List[str],
        model_column: str = "model",
        title: str = "Model Comparison",
        filename: str = "comparison.png",
    ) -> Optional[str]:
        """Generate a grouped bar chart comparing models across metrics."""
        try:
            df = pd.read_csv(csv_path)
            # Filter out N/A rows
            df = df.replace("N/A", pd.NA).dropna(subset=metrics, how="all")

            if df.empty:
                logger.warning(f"No valid data in {csv_path} for chart generation")
                return None

            for col in metrics:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            df_melted = df.melt(
                id_vars=[model_column], value_vars=metrics,
                var_name="Metric", value_name="Value",
            )

            fig, ax = plt.subplots(figsize=(10, 6))
            sns.barplot(data=df_melted, x="Metric", y="Value",
                       hue=model_column, ax=ax)
            ax.set_title(title)
            ax.set_ylabel("Score")
            ax.legend(title="Model")
            plt.tight_layout()

            save_path = os.path.join(self._output_dir, filename)
            fig.savefig(save_path)
            plt.close(fig)
            logger.info(f"Chart saved: {save_path}")
            return save_path
        except Exception as e:
            logger.error(f"Chart generation failed: {e}")
            return None

    def ablation_chart(
        self,
        csv_path: str,
        metric: str = "f1",
        config_column: str = "configuration",
        title: str = "Ablation Study",
        filename: str = "ablation.png",
    ) -> Optional[str]:
        """Generate ablation study bar chart."""
        try:
            df = pd.read_csv(csv_path)
            df = df.replace("N/A", pd.NA).dropna(subset=[metric])
            df[metric] = pd.to_numeric(df[metric], errors="coerce")

            if df.empty:
                logger.warning(f"No valid data for ablation chart")
                return None

            fig, ax = plt.subplots(figsize=(12, 6))
            colors = sns.color_palette("viridis", len(df))
            bars = ax.bar(range(len(df)), df[metric], color=colors)
            ax.set_xticks(range(len(df)))
            ax.set_xticklabels(df[config_column], rotation=45, ha="right")
            ax.set_ylabel(metric.upper())
            ax.set_title(title)

            for bar, val in zip(bars, df[metric]):
                if pd.notna(val):
                    ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                           f"{val:.3f}", ha="center", va="bottom", fontsize=9)

            plt.tight_layout()
            save_path = os.path.join(self._output_dir, filename)
            fig.savefig(save_path)
            plt.close(fig)
            logger.info(f"Ablation chart saved: {save_path}")
            return save_path
        except Exception as e:
            logger.error(f"Ablation chart generation failed: {e}")
            return None

    def roc_curve(
        self,
        fpr: list, tpr: list, auc_score: float,
        label: str = "Model",
        filename: str = "roc_curve.png",
    ) -> Optional[str]:
        """Generate ROC curve plot."""
        try:
            fig, ax = plt.subplots()
            ax.plot(fpr, tpr, label=f"{label} (AUC={auc_score:.3f})")
            ax.plot([0, 1], [0, 1], "k--", alpha=0.3)
            ax.set_xlabel("False Positive Rate")
            ax.set_ylabel("True Positive Rate")
            ax.set_title("ROC Curve")
            ax.legend()
            plt.tight_layout()

            save_path = os.path.join(self._output_dir, filename)
            fig.savefig(save_path)
            plt.close(fig)
            return save_path
        except Exception as e:
            logger.error(f"ROC curve generation failed: {e}")
            return None

    def latency_breakdown(
        self,
        csv_path: str,
        filename: str = "latency_breakdown.png",
    ) -> Optional[str]:
        """Generate latency breakdown stacked bar chart."""
        try:
            df = pd.read_csv(csv_path)
            latency_cols = [c for c in df.columns if "latency" in c.lower()]
            df_lat = df[latency_cols].apply(pd.to_numeric, errors="coerce")

            if df_lat.empty:
                return None

            fig, ax = plt.subplots(figsize=(10, 6))
            df_lat.mean().plot(kind="barh", ax=ax, color=sns.color_palette("Set2"))
            ax.set_xlabel("Latency (ms)")
            ax.set_title("Pipeline Latency Breakdown")
            plt.tight_layout()

            save_path = os.path.join(self._output_dir, filename)
            fig.savefig(save_path)
            plt.close(fig)
            return save_path
        except Exception as e:
            logger.error(f"Latency chart failed: {e}")
            return None
