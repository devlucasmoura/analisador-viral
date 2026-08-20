import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path


from ._secret import SECRET as _SECRET

_LICENSE_FILE = Path.home() / ".analisador-viral" / "license.json"
_KEY_PREFIX = "ANLV"


@dataclass
class LicenseInfo:
    key: str
    expires_on: date
    activated_on: date
    days_remaining: int

    @property
    def is_expired(self) -> bool:
        return self.days_remaining < 0


def _sign(payload: str) -> str:
    signature = hmac.new(_SECRET, payload.encode("utf-8"), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(signature)[:16].decode("ascii")


def _format_key(payload_b64: str, signature: str) -> str:
    raw = f"{payload_b64}{signature}"
    chunks = [raw[i:i + 4] for i in range(0, len(raw), 4)]
    return f"{_KEY_PREFIX}-" + "-".join(chunks)


def _parse_key(key: str) -> tuple[str, str]:
    key = key.strip().replace(" ", "")
    if not key.upper().startswith(f"{_KEY_PREFIX}-"):
        raise ValueError("Formato de chave inválido")
    body = key[len(_KEY_PREFIX) + 1:].replace("-", "")
    if len(body) < 20:
        raise ValueError("Chave muito curta")
    signature = body[-16:]
    payload_b64 = body[:-16]
    return payload_b64, signature


def generate_key(days_valid: int) -> str:
    """Gera uma nova chave com validade de `days_valid` dias a partir da ativação."""
    if days_valid < 1:
        raise ValueError("A duração deve ser de pelo menos 1 dia")

    payload = {
        "d": days_valid,
        "n": secrets.token_hex(4),
    }
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("ascii").rstrip("=")
    signature = _sign(payload_b64)
    return _format_key(payload_b64, signature)


def _decode_payload(key: str) -> dict:
    payload_b64, signature = _parse_key(key)
    expected_signature = _sign(payload_b64)
    if not hmac.compare_digest(signature, expected_signature):
        raise ValueError("Assinatura da chave inválida")

    padding = "=" * (-len(payload_b64) % 4)
    payload_json = base64.urlsafe_b64decode(payload_b64 + padding).decode("utf-8")
    return json.loads(payload_json)


def _load_state() -> dict | None:
    if not _LICENSE_FILE.exists():
        return None
    try:
        raw = _LICENSE_FILE.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (json.JSONDecodeError, OSError):
        return None

    payload = data.get("payload")
    signature = data.get("signature")
    if not payload or not signature:
        return None
    expected = _sign(json.dumps(payload, separators=(",", ":"), sort_keys=True))
    if not hmac.compare_digest(signature, expected):
        return None
    return payload


def _save_state(payload: dict) -> None:
    _LICENSE_FILE.parent.mkdir(parents=True, exist_ok=True)
    signature = _sign(json.dumps(payload, separators=(",", ":"), sort_keys=True))
    _LICENSE_FILE.write_text(
        json.dumps({"payload": payload, "signature": signature}),
        encoding="utf-8",
    )


def activate_key(key: str) -> LicenseInfo:
    """Ativa uma chave nova, salvando o momento de ativação."""
    payload = _decode_payload(key)
    days = int(payload["d"])
    today = date.today()
    expires_on = today + timedelta(days=days)

    state = {
        "key": key.strip(),
        "activated_on": today.isoformat(),
        "expires_on": expires_on.isoformat(),
        "last_seen": today.isoformat(),
    }
    _save_state(state)
    return _to_license_info(state)


def _to_license_info(state: dict) -> LicenseInfo:
    expires_on = date.fromisoformat(state["expires_on"])
    activated_on = date.fromisoformat(state["activated_on"])
    days_remaining = (expires_on - date.today()).days
    return LicenseInfo(
        key=state["key"],
        expires_on=expires_on,
        activated_on=activated_on,
        days_remaining=days_remaining,
    )


def current_license() -> LicenseInfo | None:
    """Retorna a licença atual, atualizando a 'catraca' anti-fraude.
    Retorna None se não houver licença ativa OU se foi detectada manipulação de data."""
    state = _load_state()
    if state is None:
        return None

    today = date.today()
    last_seen = date.fromisoformat(state["last_seen"])

    # Catraca: se o relógio voltou no tempo, invalida a licença
    if today < last_seen:
        _LICENSE_FILE.unlink(missing_ok=True)
        return None

    # Atualiza a última data vista
    if today > last_seen:
        state["last_seen"] = today.isoformat()
        _save_state(state)

    return _to_license_info(state)


def clear_license() -> None:
    _LICENSE_FILE.unlink(missing_ok=True)
