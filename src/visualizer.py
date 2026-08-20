import matplotlib
from matplotlib.figure import Figure

from .analyzer import ChannelAnalysis


matplotlib.use("Agg")

DARK_BG = "#1a1a1a"
PANEL_BG = "#242424"
TEXT_COLOR = "#e8e8e8"
GRID_COLOR = "#3a3a3a"
BAR_COLORS = ["#e94560", "#ff6b6b", "#ffa500", "#ffd93d", "#6bcf7f",
              "#4d9de0", "#7b68ee", "#c86bfa", "#e94560", "#ff6b6b"]


def create_metrics_figure(analysis: ChannelAnalysis) -> Figure:
    """Cria uma figura com 3 subplots: views, likes e comments dos vídeos."""
    fig = Figure(figsize=(9, 6), dpi=100, facecolor=DARK_BG)

    videos = analysis.videos
    if not videos:
        ax = fig.add_subplot(111, facecolor=PANEL_BG)
        ax.text(0.5, 0.5, "Sem vídeos para exibir",
                ha="center", va="center", color=TEXT_COLOR, fontsize=14)
        ax.set_xticks([])
        ax.set_yticks([])
        return fig

    labels = [f"#{v.rank}" for v in videos]
    views = [v.video.views for v in videos]
    likes = [v.video.likes for v in videos]
    comments = [v.video.comments for v in videos]

    _plot_bars(fig, 311, "Views por vídeo (ordenado por viralidade)", labels, views, "#e94560")
    _plot_bars(fig, 312, "Curtidas por vídeo", labels, likes, "#4d9de0")
    _plot_bars(fig, 313, "Comentários por vídeo", labels, comments, "#6bcf7f")

    fig.tight_layout(pad=2.0)
    return fig


def _plot_bars(fig: Figure, position: int, title: str,
               labels: list[str], values: list[int], color: str) -> None:
    ax = fig.add_subplot(position, facecolor=PANEL_BG)
    bars = ax.bar(labels, values, color=color, edgecolor="none", width=0.7)

    ax.set_title(title, color=TEXT_COLOR, fontsize=11, pad=10, loc="left")
    ax.tick_params(colors=TEXT_COLOR, labelsize=9)

    for spine in ax.spines.values():
        spine.set_color(GRID_COLOR)
    ax.grid(axis="y", color=GRID_COLOR, linewidth=0.5, alpha=0.6)
    ax.set_axisbelow(True)

    max_v = max(values) if values else 0
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + max_v * 0.02,
            _humanize(value),
            ha="center", va="bottom",
            color=TEXT_COLOR, fontsize=8,
        )
    ax.set_ylim(top=max_v * 1.18 if max_v else 1)


def _humanize(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)
