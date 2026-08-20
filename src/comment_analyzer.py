"""Análise dos comentários de um vídeo para entender o que o público está gostando."""
import re
from collections import Counter
from dataclasses import dataclass, field
from html import unescape

from .youtube_client import CommentData


STOPWORDS = {
    # Português
    "a", "o", "as", "os", "um", "uma", "uns", "umas", "de", "do", "da", "dos", "das",
    "em", "no", "na", "nos", "nas", "por", "para", "pra", "pro", "com", "sem", "sob",
    "sobre", "e", "ou", "mas", "que", "se", "não", "nao", "sim", "é", "eh", "ser",
    "foi", "era", "são", "sao", "tem", "ter", "tinha", "vai", "vou", "vamos", "eu",
    "você", "voce", "vc", "vcs", "ele", "ela", "eles", "elas", "meu", "minha", "seu",
    "sua", "nosso", "nossa", "isso", "aquilo", "isto", "esse", "essa", "esses", "essas",
    "este", "esta", "estes", "estas", "aqui", "ali", "lá", "la", "como", "quando",
    "onde", "porque", "por que", "porquê", "muito", "muita", "muitos", "muitas",
    "pouco", "pouca", "tudo", "todo", "toda", "todos", "todas", "já", "ja", "ainda",
    "só", "so", "também", "tambem", "mesmo", "mesma", "então", "entao", "aí", "ai",
    "né", "ne", "cara", "gente", "coisa", "vídeo", "video", "canal", "youtube",
    # Inglês
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "have", "has",
    "had", "do", "does", "did", "will", "would", "should", "could", "may", "might",
    "must", "shall", "can", "of", "to", "in", "on", "at", "by", "for", "with", "about",
    "against", "between", "into", "through", "during", "before", "after", "above",
    "below", "from", "up", "down", "out", "off", "over", "under", "again", "further",
    "then", "once", "here", "there", "when", "where", "why", "how", "all", "any",
    "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "just", "and", "or",
    "but", "if", "because", "as", "while", "of", "you", "your", "yours", "he", "she",
    "it", "we", "they", "them", "their", "his", "her", "its", "my", "me", "i",
    "this", "that", "these", "those", "who", "what", "which", "video", "channel",
}

POSITIVE_WORDS = {
    "amei", "adorei", "gostei", "top", "ótimo", "otimo", "excelente", "incrível",
    "incrivel", "sensacional", "perfeito", "maravilhoso", "show", "massa", "demais",
    "bom", "boa", "melhor", "genial", "brabo", "brabíssimo", "sinistro", "foda",
    "gigante", "monstro", "lindo", "linda", "obrigado", "obrigada", "parabéns",
    "parabens", "salvou", "ajudou", "surreal", "épico", "epico", "hilário", "hilario",
    "engraçado", "engracado", "risada", "kkkk", "kkkkk", "kkkkkk", "haha", "hahaha",
    "❤", "❤️", "😍", "🔥", "👏", "🥰", "😂", "🤣", "💯", "🙌",
    "love", "loved", "great", "amazing", "awesome", "best", "perfect", "beautiful",
    "incredible", "insane", "fire", "goat", "wonderful", "brilliant", "thanks",
    "thank", "helpful",
}

NEGATIVE_WORDS = {
    "ruim", "péssimo", "pessimo", "horrível", "horrivel", "chato", "boring",
    "decepção", "decepcao", "decepcionado", "decepcionante", "fraco", "fraca",
    "cringe", "mid", "meh", "não gostei", "nao gostei", "odiei", "detestei", "lixo",
    "porcaria", "besteira", "bosta", "merda", "clickbait", "enganação", "enganacao",
    "mentira", "furada", "😡", "😠", "👎", "🤢",
    "bad", "worst", "terrible", "awful", "boring", "hate", "hated", "trash",
    "garbage", "waste", "disappointing", "disappointed", "overrated",
}

REQUEST_PATTERNS = [
    r"faz(em)?\s+um\s+(v[íi]deo|epis[óo]dio|conteudo|conte[úu]do)\s+(sobre|de|com)",
    r"quer[íi]a\s+(muito\s+)?ver",
    r"pod[ei]a?\s+fazer",
    r"pod[ei]a?\s+(reagir|analisar|falar)",
    r"por\s+favor\s+faz",
    r"faz\s+mais",
    r"quando\s+vai\s+ter",
    r"quando\s+(sai|sair|vem)",
    r"me\s+diz",
    r"algu[eé]m\s+sabe",
    r"parte\s+\d+",
    r"segunda\s+parte",
    r"pr[óo]xim[oa]\s+v[íi]deo",
    r"please\s+(make|do)",
    r"can\s+you\s+(do|make|react)",
    r"want\s+to\s+see",
    r"part\s+\d+",
    r"next\s+video",
]


@dataclass
class CommentInsights:
    total_analyzed: int = 0
    top_comments: list[CommentData] = field(default_factory=list)
    top_keywords: list[tuple[str, int]] = field(default_factory=list)
    sentiment: str = "neutro"  # positivo | negativo | neutro | misto
    positive_score: int = 0
    negative_score: int = 0
    requests: list[str] = field(default_factory=list)

    @property
    def has_data(self) -> bool:
        return self.total_analyzed > 0


def analyze_comments(comments: list[CommentData]) -> CommentInsights:
    if not comments:
        return CommentInsights()

    cleaned = [_clean_text(c.text) for c in comments]
    all_text = " ".join(cleaned).lower()

    top_by_likes = sorted(comments, key=lambda c: c.likes, reverse=True)[:5]

    keywords = _extract_keywords(all_text)

    positive = _count_matches(all_text, POSITIVE_WORDS)
    negative = _count_matches(all_text, NEGATIVE_WORDS)
    sentiment = _classify_sentiment(positive, negative, len(comments))

    requests = _extract_requests(comments)

    return CommentInsights(
        total_analyzed=len(comments),
        top_comments=top_by_likes,
        top_keywords=keywords,
        sentiment=sentiment,
        positive_score=positive,
        negative_score=negative,
        requests=requests[:5],
    )


def _clean_text(text: str) -> str:
    text = unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)          # remove tags HTML
    text = re.sub(r"http\S+", " ", text)          # remove URLs
    return text


def _extract_keywords(text: str, top_n: int = 8) -> list[tuple[str, int]]:
    words = re.findall(r"[a-záàâãéêíóôõúüçñ]{4,}", text, flags=re.IGNORECASE)
    filtered = [w.lower() for w in words if w.lower() not in STOPWORDS]
    if not filtered:
        return []
    counter = Counter(filtered)
    return counter.most_common(top_n)


def _count_matches(text: str, vocab: set[str]) -> int:
    count = 0
    for word in vocab:
        if re.search(r"\W", word):
            # expressão com espaço / emoji — busca literal
            count += text.count(word)
        else:
            count += len(re.findall(rf"\b{re.escape(word)}\b", text))
    return count


def _classify_sentiment(positive: int, negative: int, sample_size: int) -> str:
    if positive == 0 and negative == 0:
        return "neutro"
    total = positive + negative
    pos_ratio = positive / total
    if pos_ratio >= 0.7:
        return "positivo"
    if pos_ratio <= 0.3:
        return "negativo"
    return "misto"


def _extract_requests(comments: list[CommentData]) -> list[str]:
    combined = re.compile("|".join(REQUEST_PATTERNS), flags=re.IGNORECASE)
    found: list[str] = []
    seen: set[str] = set()
    for c in comments:
        text = _clean_text(c.text)
        if combined.search(text):
            snippet = text.strip().replace("\n", " ")
            if len(snippet) > 140:
                snippet = snippet[:137] + "..."
            key = snippet.lower()
            if key in seen:
                continue
            seen.add(key)
            found.append(snippet)
    return found
