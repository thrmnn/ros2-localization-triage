"""A cited hypothesis per incident, with every citation checked against the recording.

The detectors do the detection. This asks a small local model for one thing they
cannot give: a short account linking flagged events into a plausible cause. That
account is only worth anything if its citations are real, so every one is
verified against the bag before the hypothesis is shown, and a hypothesis whose
citations do not check out is *downgraded and labelled* rather than dropped --
silently discarding the model's failures would make the output look better than
the method is.

The model is deliberately small. The honest public answer to "what model powers
this" is: a small local model sized for a fast demo; for production work I would
size up.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from .signals import Signals

OLLAMA = "http://127.0.0.1:11434/api/generate"
DEFAULT_MODEL = "qwen3:8b-16k"

# Constrained decoding, not just a prompt asking nicely. A model free to emit
# prose will emit prose exactly when the window is hardest to explain.
CITATION_SCHEMA = {
    "type": "object",
    "required": ["hypothesis", "confidence", "citations"],
    "properties": {
        "hypothesis": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low", "unresolved"]},
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["claim", "cited_timestamp", "cited_topic"],
                "properties": {
                    "claim": {"type": "string"},
                    "cited_timestamp": {"type": "number"},
                    "cited_topic": {"type": "string"},
                    "cited_node": {"type": "string"},
                },
            },
        },
    },
}

TOLERANCE_S = 1.0  # a citation may name a time this far from a real message


@dataclass
class CitationCheck:
    claim: str
    topic: str
    timestamp: float
    topic_exists: bool
    time_in_range: bool
    near_a_message: bool
    relevant: bool = True

    @property
    def verified(self) -> bool:
        return self.topic_exists and self.time_in_range and self.near_a_message and self.relevant

    @property
    def why(self) -> str:
        if not self.topic_exists:
            return f"no topic {self.topic} in this recording"
        if not self.time_in_range:
            return f"{self.timestamp:.2f}s is outside the recording"
        if not self.near_a_message:
            return f"no message on {self.topic} within {TOLERANCE_S}s of {self.timestamp:.2f}s"
        if not self.relevant:
            return f"{self.topic} is real but is not a topic any flagged event came from"
        return "verified"


@dataclass
class Hypothesis:
    text: str
    stated_confidence: str
    citations: list[CitationCheck] = field(default_factory=list)
    error: str | None = None

    @property
    def verified_confidence(self) -> str:
        """Confidence after checking. A model cannot talk its way up: any failed
        citation caps it, and no citations at all is unresolved by definition."""
        if self.error or not self.citations:
            return "unresolved"
        if all(c.verified for c in self.citations):
            return self.stated_confidence
        if any(c.verified for c in self.citations):
            return "low"
        return "unresolved"

    @property
    def downgraded(self) -> bool:
        return self.verified_confidence != self.stated_confidence


def verify(citation: dict, signals: Signals, relevant_topics: set[str] | None = None) -> CitationCheck:
    """Existence is not relevance.

    A first version checked only that the cited topic and time were real. A model
    then cited /particle_cloud for a covariance claim that comes from /amcl_pose,
    and it passed -- because /particle_cloud is a real topic with messages at that
    moment. Verifying existence alone lets a confident, wrong hypothesis through
    wearing four green ticks, which is worse than no verification at all.
    """
    topic = str(citation.get("cited_topic", ""))
    ts = float(citation.get("cited_timestamp", -1))
    arrivals = signals.arrivals.get(topic)
    exists = arrivals is not None and len(arrivals) > 0
    in_range = 0.0 <= ts <= signals.duration_s
    near = bool(exists and in_range and min(abs(a - ts) for a in arrivals) <= TOLERANCE_S)
    rel = True if relevant_topics is None else topic in relevant_topics
    return CitationCheck(str(citation.get("claim", "")), topic, ts, exists, in_range, near, rel)


def _prompt(window: dict, signals: Signals) -> str:
    topics = ", ".join(sorted(signals.arrivals))
    return (
        "You are reading detector output from a robot's navigation logs.\n\n"
        f"Recording length: {signals.duration_s:.1f} s. Topics present: {topics}\n\n"
        f"Flagged events in this window:\n{json.dumps(window['detections'], indent=1)}\n\n"
        "Give one short hypothesis linking these events into a plausible cause. "
        "Cite every claim with a timestamp inside the recording and a topic from "
        "the list above. Do not cite a topic that is not listed. If the events do "
        "not support a single cause, say so and set confidence to unresolved."
    )


def explain(window: dict, signals: Signals, model: str = DEFAULT_MODEL,
            timeout_s: float = 120.0) -> Hypothesis:
    body = json.dumps({
        "model": model,
        "prompt": _prompt(window, signals),
        "format": CITATION_SCHEMA,
        "stream": False,
        "options": {"temperature": 0.0},
    }).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as r:
            raw = json.loads(r.read())["response"]
        parsed = json.loads(raw)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return Hypothesis("", "unresolved", error=f"model unreachable: {e}")
    except (json.JSONDecodeError, KeyError) as e:
        return Hypothesis("", "unresolved", error=f"unparseable response: {e}")

    return Hypothesis(
        text=str(parsed.get("hypothesis", "")),
        stated_confidence=str(parsed.get("confidence", "unresolved")),
        citations=[verify(c, signals, window.get("topics")) for c in parsed.get("citations", [])],
    )
