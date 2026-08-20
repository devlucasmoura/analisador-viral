import re
import statistics
from dataclasses import dataclass, field
from datetime import datetime

from .youtube_client import ChannelData, VideoData


TRIGGER_WORDS = {
    "shocking", "revealed", "truth", "secret", "insane", "crazy", "epic",
    "official", "trailer", "vs", "challenge", "reaction", "world", "record",
    "finally", "exposed", "gone wrong", "must watch", "top", "best", "worst",
    "surpreendente", "revelado", "verdade", "segredo", "inacreditável",
    "chocante", "épico", "oficial", "desafio", "reação", "recorde",
    "finalmente", "melhor", "pior", "assistir",
}


@dataclass
class VideoAnalysis:
    video: VideoData
    viral_score: float
    engagement_rate: float  # likes / views %
    is_viral: bool
    rank: int


@dataclass
class ViralReasons:
    factors: list[str] = field(default_factory=list)
    summary: str = ""


@dataclass
class ChannelAnalysis:
    channel: ChannelData
    videos: list[VideoAnalysis]
    median_views: int
    avg_duration: float
    avg_title_length: float
    top_viral: VideoAnalysis | None
    reasons: ViralReasons

    @property
    def viral_videos(self) -> list[VideoAnalysis]:
        return [v for v in self.videos if v.is_viral]


def analyze_channel(channel: ChannelData) -> ChannelAnalysis:
    if not channel.videos:
        return ChannelAnalysis(
            channel=channel,
            videos=[],
            median_views=0,
            avg_duration=0,
            avg_title_length=0,
            top_viral=None,
            reasons=ViralReasons(summary="Este canal não tem vídeos recentes."),
        )

    videos = channel.videos
    views_list = [v.views for v in videos]
    median_views = int(statistics.median(views_list)) or 1

    analyses: list[VideoAnalysis] = []
    for v in videos:
        engagement = (v.likes / v.views * 100) if v.views else 0
        viral_score = v.views / median_views
        analyses.append(VideoAnalysis(
            video=v,
            viral_score=viral_score,
            engagement_rate=engagement,
            is_viral=viral_score >= 2.0,
            rank=0,
        ))

    analyses.sort(key=lambda a: a.viral_score, reverse=True)
    for i, a in enumerate(analyses, start=1):
        a.rank = i

    avg_duration = statistics.mean(v.duration_seconds for v in videos)
    avg_title_length = statistics.mean(len(v.title) for v in videos)
    avg_engagement = statistics.mean(a.engagement_rate for a in analyses)

    top = analyses[0]
    reasons = _diagnose_viral(top, avg_duration, avg_title_length, avg_engagement, median_views)

    return ChannelAnalysis(
        channel=channel,
        videos=analyses,
        median_views=median_views,
        avg_duration=avg_duration,
        avg_title_length=avg_title_length,
        top_viral=top if top.viral_score >= 1.5 else None,
        reasons=reasons,
    )


def _diagnose_viral(
    top: VideoAnalysis,
    avg_duration: float,
    avg_title_length: float,
    avg_engagement: float,
    median_views: int,
) -> ViralReasons:
    video = top.video
    factors: list[str] = []

    if top.viral_score < 1.5:
        return ViralReasons(
            summary=(
                f"Nenhum vídeo se destacou muito da média do canal. "
                f"O top ({video.title[:60]}...) teve {video.views:,} views, "
                f"aproximadamente na média (mediana: {median_views:,})."
            ).replace(",", ".")
        )

    title = video.title
    words = title.split()

    caps_words = [w for w in words if len(w) > 2 and w.isupper()]
    if caps_words:
        factors.append(f"Título usa {len(caps_words)} palavra(s) em CAIXA ALTA ({', '.join(caps_words[:3])})")

    if any(c.isdigit() for c in title):
        numbers = re.findall(r"\d+", title)
        factors.append(f"Título contém número(s): {', '.join(numbers[:3])}")

    if "?" in title:
        factors.append("Título é uma pergunta (gera curiosidade)")
    if "!" in title:
        factors.append("Título usa exclamação (transmite urgência/empolgação)")

    triggers_found = [
        w for w in TRIGGER_WORDS
        if re.search(rf"\b{re.escape(w)}\b", title.lower())
    ]
    if triggers_found:
        factors.append(f"Título contém palavra-gatilho: {', '.join(triggers_found[:3])}")

    title_len = len(title)
    if title_len > avg_title_length * 1.3:
        factors.append(f"Título é longo ({title_len} chars vs média do canal {avg_title_length:.0f})")
    elif title_len < avg_title_length * 0.6:
        factors.append(f"Título é curto ({title_len} chars vs média do canal {avg_title_length:.0f})")

    if avg_duration > 0:
        duration_ratio = video.duration_seconds / avg_duration
        if duration_ratio > 1.5:
            factors.append(
                f"Vídeo é {duration_ratio:.1f}x mais longo que a média do canal "
                f"({_fmt_duration(video.duration_seconds)} vs {_fmt_duration(int(avg_duration))})"
            )
        elif duration_ratio < 0.5:
            factors.append(
                f"Vídeo é bem mais curto que a média "
                f"({_fmt_duration(video.duration_seconds)} vs {_fmt_duration(int(avg_duration))})"
            )

    if top.engagement_rate > avg_engagement * 1.3:
        factors.append(
            f"Taxa de curtidas alta: {top.engagement_rate:.1f}% "
            f"(média do canal: {avg_engagement:.1f}%)"
        )

    hour = video.published_at.hour
    if 14 <= hour <= 19:
        factors.append(f"Publicado em horário nobre ({hour}h UTC)")
    elif hour < 6 or hour > 22:
        factors.append(f"Publicado em horário incomum ({hour}h UTC)")

    if video.tags and len(video.tags) >= 10:
        factors.append(f"Usa muitas tags ({len(video.tags)}), o que ajuda na descoberta")

    if not factors:
        factors.append("Não identificamos fatores óbvios — provavelmente contexto externo (assunto em alta, colaboração, algoritmo do YouTube)")

    summary = (
        f'O vídeo "{video.title[:80]}" bombou com {video.views:,} views '
        f"({top.viral_score:.1f}x a mediana do canal, que é {median_views:,}). "
        f"Possíveis motivos identificados:"
    ).replace(",", ".")

    return ViralReasons(factors=factors, summary=summary)


def _fmt_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}min{sec:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}min"
