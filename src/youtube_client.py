import re
from dataclasses import dataclass
from datetime import datetime

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


@dataclass
class VideoData:
    video_id: str
    title: str
    published_at: datetime
    duration_seconds: int
    views: int
    likes: int
    comments: int
    thumbnail_url: str
    tags: list[str]
    description: str

    @property
    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.video_id}"


@dataclass
class ChannelData:
    channel_id: str
    title: str
    subscribers: int
    total_videos: int
    videos: list[VideoData]


class YouTubeError(Exception):
    pass


class YouTubeClient:
    def __init__(self, api_key: str):
        self._service = build("youtube", "v3", developerKey=api_key, cache_discovery=False)

    def analyze_channel(self, url_or_id: str, max_videos: int = 10) -> ChannelData:
        channel_id = self._resolve_channel_id(url_or_id)
        channel_info = self._fetch_channel_info(channel_id)
        uploads_playlist = channel_info["contentDetails"]["relatedPlaylists"]["uploads"]
        video_ids = self._fetch_recent_video_ids(uploads_playlist, max_videos)
        videos = self._fetch_videos(video_ids)

        snippet = channel_info["snippet"]
        stats = channel_info["statistics"]
        return ChannelData(
            channel_id=channel_id,
            title=snippet["title"],
            subscribers=int(stats.get("subscriberCount", 0)),
            total_videos=int(stats.get("videoCount", 0)),
            videos=videos,
        )

    def _resolve_channel_id(self, url_or_id: str) -> str:
        text = url_or_id.strip()

        if re.fullmatch(r"UC[\w-]{22}", text):
            return text

        channel_match = re.search(r"youtube\.com/channel/(UC[\w-]{22})", text)
        if channel_match:
            return channel_match.group(1)

        handle = self._extract_handle(text)
        if handle:
            return self._lookup_by_handle(handle)

        legacy_user = re.search(r"youtube\.com/(?:user|c)/([^/?#]+)", text)
        if legacy_user:
            return self._lookup_by_username(legacy_user.group(1))

        if text.startswith("@"):
            return self._lookup_by_handle(text[1:])

        raise YouTubeError(
            "Formato de link não reconhecido. Use um link de canal ou o handle @nome."
        )

    def _extract_handle(self, text: str) -> str | None:
        match = re.search(r"youtube\.com/@([^/?#]+)", text)
        if match:
            return match.group(1)
        return None

    def _lookup_by_handle(self, handle: str) -> str:
        try:
            response = self._service.channels().list(
                part="id",
                forHandle=f"@{handle}",
            ).execute()
        except HttpError as exc:
            raise YouTubeError(self._friendly_error(exc)) from exc

        items = response.get("items", [])
        if not items:
            raise YouTubeError(f"Nenhum canal encontrado para o handle @{handle}")
        return items[0]["id"]

    def _lookup_by_username(self, username: str) -> str:
        try:
            response = self._service.channels().list(
                part="id",
                forUsername=username,
            ).execute()
        except HttpError as exc:
            raise YouTubeError(self._friendly_error(exc)) from exc

        items = response.get("items", [])
        if not items:
            raise YouTubeError(f"Nenhum canal encontrado para o usuário {username}")
        return items[0]["id"]

    def _fetch_channel_info(self, channel_id: str) -> dict:
        try:
            response = self._service.channels().list(
                part="snippet,statistics,contentDetails",
                id=channel_id,
            ).execute()
        except HttpError as exc:
            raise YouTubeError(self._friendly_error(exc)) from exc

        items = response.get("items", [])
        if not items:
            raise YouTubeError(f"Canal {channel_id} não encontrado")
        return items[0]

    def _fetch_recent_video_ids(self, uploads_playlist: str, max_videos: int) -> list[str]:
        try:
            response = self._service.playlistItems().list(
                part="contentDetails",
                playlistId=uploads_playlist,
                maxResults=max_videos,
            ).execute()
        except HttpError as exc:
            raise YouTubeError(self._friendly_error(exc)) from exc

        return [item["contentDetails"]["videoId"] for item in response.get("items", [])]

    def _fetch_videos(self, video_ids: list[str]) -> list[VideoData]:
        if not video_ids:
            return []

        try:
            response = self._service.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(video_ids),
            ).execute()
        except HttpError as exc:
            raise YouTubeError(self._friendly_error(exc)) from exc

        videos = []
        for item in response.get("items", []):
            snippet = item["snippet"]
            stats = item.get("statistics", {})
            details = item.get("contentDetails", {})

            thumbnails = snippet.get("thumbnails", {})
            best_thumb = (
                thumbnails.get("maxres")
                or thumbnails.get("high")
                or thumbnails.get("medium")
                or thumbnails.get("default")
                or {}
            )

            videos.append(VideoData(
                video_id=item["id"],
                title=snippet["title"],
                published_at=datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00")),
                duration_seconds=_parse_iso_duration(details.get("duration", "PT0S")),
                views=int(stats.get("viewCount", 0)),
                likes=int(stats.get("likeCount", 0)),
                comments=int(stats.get("commentCount", 0)),
                thumbnail_url=best_thumb.get("url", ""),
                tags=snippet.get("tags", []),
                description=snippet.get("description", ""),
            ))
        return videos

    @staticmethod
    def _friendly_error(exc: HttpError) -> str:
        status = exc.resp.status if exc.resp else 0
        if status == 403:
            return (
                "Acesso negado (403). Sua chave pode estar inválida, sem permissão "
                "para a YouTube Data API v3, ou a cota diária de 10.000 unidades foi "
                "atingida."
            )
        if status == 400:
            return "Requisição inválida (400). Verifique a API key ou o link do canal."
        if status == 404:
            return "Recurso não encontrado (404)."
        return f"Erro na API do YouTube ({status}): {exc}"


def _parse_iso_duration(iso: str) -> int:
    """Converte duração ISO 8601 do YouTube (ex: PT1H2M30S) para segundos."""
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    if not match:
        return 0
    hours, minutes, seconds = (int(g) if g else 0 for g in match.groups())
    return hours * 3600 + minutes * 60 + seconds
