"""Learn beat preferences from local 👍/👎 ratings (lightweight sklearn ranker).

Ratings append to ``user_data/beat_ratings.jsonl``. After enough samples the
model retrains and ``beat_quality.evaluate`` blends proxy score with the
learned reward prediction.

Env:
    PLG_USE_BEAT_REWARD=1|0|auto   (auto = on when sklearn is installed)
    PLG_BEAT_REWARD_WEIGHT=0.35    blend weight for reward vs proxy (0–1)
    PLG_BEAT_REWARD_MIN_SAMPLES=6  minimum ratings before model is used
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pattern_features import FEATURE_ORDER, features_vector
from plg_paths import user_data_dir

logger = logging.getLogger("plg.beat_reward")

_MIN_SAMPLES_DEFAULT = 6
_MODEL_FILE = "beat_reward.pkl"
_LOG_FILE = "beat_ratings.jsonl"


def _env_flag(name: str, default: str = "auto") -> str:
    return os.environ.get(name, default).strip().lower()


def reward_enabled() -> bool:
    flag = _env_flag("PLG_USE_BEAT_REWARD", "auto")
    if flag in ("0", "false", "no", "off"):
        return False
    if flag in ("1", "true", "yes", "on"):
        return _sklearn_available()
    return _sklearn_available()


def reward_weight() -> float:
    try:
        return max(0.0, min(1.0, float(os.environ.get("PLG_BEAT_REWARD_WEIGHT", "0.35"))))
    except ValueError:
        return 0.35


def min_train_samples() -> int:
    try:
        return max(4, int(os.environ.get("PLG_BEAT_REWARD_MIN_SAMPLES", str(_MIN_SAMPLES_DEFAULT))))
    except ValueError:
        return _MIN_SAMPLES_DEFAULT


def _sklearn_available() -> bool:
    try:
        import sklearn  # noqa: F401

        return True
    except ImportError:
        return False


def _data_dir() -> Path:
    path = user_data_dir() / "beat_reward"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ratings_log_path() -> Path:
    return _data_dir() / _LOG_FILE


def model_path() -> Path:
    return _data_dir() / _MODEL_FILE


def load_ratings() -> list[dict[str, Any]]:
    path = ratings_log_path()
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and row.get("rating") in (1, -1):
            rows.append(row)
    return rows


def _append_rating(row: dict[str, Any]) -> None:
    path = ratings_log_path()
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _save_model(model: Any, meta: dict[str, Any]) -> None:
    try:
        import joblib
    except ImportError:
        from sklearn.externals import joblib  # type: ignore[import-not-found,no-redef]

    payload = {"model": model, "meta": meta, "features": list(FEATURE_ORDER)}
    joblib.dump(payload, model_path())


def _load_model() -> tuple[Any, dict[str, Any]] | None:
    path = model_path()
    if not path.is_file():
        return None
    try:
        import joblib
    except ImportError:
        from sklearn.externals import joblib  # type: ignore[import-not-found,no-redef]
    try:
        payload = joblib.load(path)
    except Exception as exc:
        logger.warning("Could not load beat reward model: %s", exc)
        return None
    if not isinstance(payload, dict) or "model" not in payload:
        return None
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    return payload["model"], meta


def train_model() -> dict[str, Any] | None:
    """Retrain logistic ranker from the ratings log. Returns training meta or None."""
    if not _sklearn_available():
        return None

    rows = load_ratings()
    if len(rows) < min_train_samples():
        return None

    from sklearn.linear_model import LogisticRegression
    import numpy as np

    x_rows: list[list[float]] = []
    y_rows: list[int] = []
    for row in rows:
        feats = row.get("features")
        if not isinstance(feats, list) or len(feats) != len(FEATURE_ORDER):
            continue
        x_rows.append([float(v) for v in feats])
        y_rows.append(1 if int(row["rating"]) > 0 else 0)

    if len(x_rows) < min_train_samples():
        return None
    if len(set(y_rows)) < 2:
        logger.info("Beat reward: need both 👍 and 👎 before training")
        return None

    x = np.array(x_rows, dtype=float)
    y = np.array(y_rows, dtype=int)
    model = LogisticRegression(max_iter=800, class_weight="balanced")
    model.fit(x, y)
    acc = float(model.score(x, y))
    meta = {
        "samples": len(x_rows),
        "accuracy_in_sample": round(acc, 3),
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_model(model, meta)
    logger.info("Beat reward model trained on %s samples (acc=%.2f)", len(x_rows), acc)
    return meta


def predict_reward_score(pattern: dict[str, Any]) -> float | None:
    """Return 0–100 reward score, or None if no trained model."""
    if not reward_enabled():
        return None
    loaded = _load_model()
    if loaded is None:
        return None
    model, meta = loaded
    if int(meta.get("samples", 0)) < min_train_samples():
        return None

    import numpy as np

    vec = np.array([features_vector(pattern)], dtype=float)
    try:
        if hasattr(model, "predict_proba"):
            prob = float(model.predict_proba(vec)[0][1])
        else:
            prob = float(model.predict(vec)[0])
    except Exception as exc:
        logger.warning("Beat reward predict failed: %s", exc)
        return None
    return round(max(0.0, min(100.0, prob * 100.0)), 2)


def record_rating(pattern: dict[str, Any], rating: int) -> dict[str, Any]:
    """Persist one rating and retrain when enough data is available."""
    rating = 1 if int(rating) > 0 else -1
    beat_id = str(pattern.get("plg_beat_id") or "")
    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "beat_id": beat_id,
        "rating": rating,
        "bpm": pattern.get("bpm"),
        "style": pattern.get("style"),
        "genre": (pattern.get("plg_quality") or {}).get("genre"),
        "proxy_score": (pattern.get("plg_quality") or {}).get("score"),
        "prompt": str(pattern.get("user_prompt") or "")[:240],
        "features": features_vector(pattern),
    }
    _append_rating(row)
    total = len(load_ratings())
    train_meta = train_model()
    return {
        "rating": rating,
        "total_ratings": total,
        "model_trained": train_meta is not None,
        "model_samples": (train_meta or {}).get("samples"),
    }


def model_status() -> dict[str, Any]:
    loaded = _load_model()
    meta = loaded[1] if loaded else {}
    return {
        "enabled": reward_enabled(),
        "ratings": len(load_ratings()),
        "min_samples": min_train_samples(),
        "model_ready": loaded is not None and int(meta.get("samples", 0)) >= min_train_samples(),
        "model_samples": meta.get("samples"),
        "trained_at": meta.get("trained_at"),
    }
