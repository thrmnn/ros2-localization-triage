"""The model half of the pipeline cannot be unit-tested; the checking half must be.

These cover the property that matters: a hypothesis cannot claim more confidence
than its citations survive.
"""

from __future__ import annotations

import numpy as np
import pytest

from localization_triage.reasoning import CitationCheck, Hypothesis, verify
from localization_triage.signals import Signals


@pytest.fixture
def signals() -> Signals:
    return Signals(
        path="test", start_ns=0, duration_s=100.0,
        topic_types={"/scan": "sensor_msgs/msg/LaserScan", "/amcl_pose": "x", "/particle_cloud": "y"},
        topic_counts={"/scan": 3, "/amcl_pose": 3, "/particle_cloud": 3},
        arrivals={"/scan": np.array([10.0, 20.0, 30.0]),
                  "/amcl_pose": np.array([10.0, 20.0, 30.0]),
                  "/particle_cloud": np.array([10.0, 20.0, 30.0])},
        stamps={}, tf_edges={}, amcl=None, odom=None,
    )


def test_citation_on_a_real_topic_at_a_real_time_verifies(signals):
    c = verify({"claim": "c", "cited_topic": "/scan", "cited_timestamp": 10.0}, signals)
    assert c.verified and c.why == "verified"


def test_citation_to_a_topic_not_in_the_recording_fails(signals):
    c = verify({"claim": "c", "cited_topic": "/nope", "cited_timestamp": 10.0}, signals)
    assert not c.verified and "no topic" in c.why


def test_citation_outside_the_recording_fails(signals):
    c = verify({"claim": "c", "cited_topic": "/scan", "cited_timestamp": 500.0}, signals)
    assert not c.verified and "outside the recording" in c.why


def test_citation_far_from_any_message_fails(signals):
    c = verify({"claim": "c", "cited_topic": "/scan", "cited_timestamp": 15.0}, signals)
    assert not c.verified and "within" in c.why


def test_real_topic_that_no_flagged_event_used_is_not_relevant(signals):
    """The failure this exists for: a model cited /particle_cloud for a covariance
    claim that comes from /amcl_pose. The topic is real and has messages at that
    instant, so an existence-only check passed it."""
    c = verify({"claim": "c", "cited_topic": "/particle_cloud", "cited_timestamp": 10.0},
               signals, relevant_topics={"/amcl_pose", "/scan"})
    assert not c.verified and "not a topic any flagged event came from" in c.why


def _c(ok: bool) -> CitationCheck:
    return CitationCheck("c", "/scan", 10.0, ok, ok, ok, ok)


def test_confidence_survives_when_every_citation_holds():
    assert Hypothesis("t", "high", [_c(True), _c(True)]).verified_confidence == "high"


def test_partial_citation_failure_caps_confidence_at_low():
    h = Hypothesis("t", "high", [_c(True), _c(False)])
    assert h.verified_confidence == "low" and h.downgraded


def test_total_citation_failure_is_unresolved():
    assert Hypothesis("t", "high", [_c(False)]).verified_confidence == "unresolved"


def test_a_hypothesis_with_no_citations_cannot_be_confident():
    assert Hypothesis("t", "high", []).verified_confidence == "unresolved"


def test_an_unreachable_model_is_unresolved_not_silently_dropped():
    h = Hypothesis("", "unresolved", error="model unreachable")
    assert h.verified_confidence == "unresolved"
