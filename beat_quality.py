"""Post-humanize beat quality gate — pattern_score + midi_validate.

Used by ``backend_core.run_pipeline`` to retry LLM generation when a beat
scores below ``PLG_MIN_BEAT_SCORE`` or fails structural validation.

Env:
    PLG_USE_BEAT_SCORER=1|0|auto   (auto = on)
    PLG_BEAT_RETRIES=1             extra LLM attempts after the first (max 3)
    PLG_MIN_BEAT_SCORE=48          minimum proxy score to accept
    PLG_USE_BEAT_REWARD=1|0|auto   blend in learned 👍/👎 ranker
    PLG_BEAT_REWARD_WEIGHT=0.35    reward vs proxy blend weight
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Any

from genre_profiles import PROFILES, detect_genre
from midi_validate import validate_pattern
from pattern_score import score_humanized_pattern

try:
    from beat_reward import predict_reward_score, reward_enabled, reward_weight
except ImportError:
    def reward_enabled() -> bool:  # type: ignore[misc]
        return False

    def reward_weight() -> float:  # type: ignore[misc]
        return 0.0

    def predict_reward_score(pattern: dict[str, Any]) -> float | None:  # type: ignore[misc]
        return None

_HARD_FAIL = (
    "no notes",
    "missing bpm",
    "invalid bpm",
    "tracks missing",
)


def _env_flag(name: str, default: str = "auto") -> str:
    return os.environ.get(name, default).strip().lower()


def scorer_enabled() -> bool:
    flag = _env_flag("PLG_USE_BEAT_SCORER", "auto")
    return flag not in ("0", "false", "no", "off")


def max_retries() -> int:
    if not scorer_enabled():
        return 0
    try:
        return max(0, min(3, int(os.environ.get("PLG_BEAT_RETRIES", "1"))))
    except ValueError:
        return 1


def min_score() -> float:
    try:
        return float(os.environ.get("PLG_MIN_BEAT_SCORE", "48"))
    except ValueError:
        return 48.0


@dataclass(frozen=True)
class QualityReport:
    score: float
    proxy_score: float
    reward_score: float | None
    passed: bool
    hard_fail: bool
    warnings: list[str]
    genre: str


def profile_for_pattern(pattern: dict[str, Any]):
    genre = str(pattern.get("plg_genre") or detect_genre(
        str(pattern.get("style", "")),
        str(pattern.get("user_prompt", "")),
    ))
    return PROFILES.get(genre, PROFILES["trap"]), genre


def evaluate(pattern: dict[str, Any]) -> QualityReport:
    warnings = validate_pattern(pattern)
    hard_fail = any(
        any(snippet in warning for snippet in _HARD_FAIL)
        for warning in warnings
    )
    profile, genre = profile_for_pattern(pattern)
    proxy = score_humanized_pattern(pattern, profile)
    reward = predict_reward_score(pattern) if reward_enabled() else None
    if reward is not None:
        w = reward_weight()
        score = (1.0 - w) * proxy + w * reward
    else:
        score = proxy
    threshold = min_score()
    passed = not hard_fail and score >= threshold
    return QualityReport(
        score=round(score, 2),
        proxy_score=round(proxy, 2),
        reward_score=reward,
        passed=passed,
        hard_fail=hard_fail,
        warnings=warnings,
        genre=genre,
    )


def attach_quality_meta(
    pattern: dict[str, Any],
    report: QualityReport,
    *,
    attempt: int = 0,
    retries_used: int = 0,
) -> None:
    if not pattern.get("plg_beat_id"):
        pattern["plg_beat_id"] = uuid.uuid4().hex[:16]
    pattern["plg_quality"] = {
        "score": report.score,
        "proxy_score": report.proxy_score,
        "reward_score": report.reward_score,
        "reward_blend": reward_weight() if report.reward_score is not None else 0.0,
        "passed": report.passed,
        "hard_fail": report.hard_fail,
        "genre": report.genre,
        "min_score": min_score(),
        "attempt": attempt,
        "retries_used": retries_used,
        "warnings": report.warnings[:10],
        "beat_id": pattern["plg_beat_id"],
    }


def retry_prompt_suffix(attempt: int) -> str:
    return (
        f"\n\n[PLG revision {attempt}: tighten rhythm pocket, stay in key, "
        "keep kick/snare backbeat, no empty tracks, fix any off-scale melody notes.]"
    )
