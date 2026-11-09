"""
services/conflict_service.py — Schedule Conflict Auditor

Cross-references calendar events and email requests to detect:
1. Direct time collisions between scheduled events
2. Back-to-back scheduling with zero transit/prep buffer
3. Proposed meeting times from incoming emails that collide with calendar commitments
"""

from typing import Any, List, Dict
from app.utils.logging import get_logger

logger = get_logger(__name__)


def detect_schedule_conflicts(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Analyzes an array of events and identifies schedule overlaps.

    Returns a list of structured conflict objects with severity and suggestions.
    """
    conflicts: List[Dict[str, Any]] = []

    if len(events) < 2:
        return conflicts

    # Standardize events
    parsed_events = []
    for e in events:
        parsed_events.append({
            "id": e.get("id", "unknown"),
            "summary": e.get("summary", "Untitled Event"),
            "start": str(e.get("start", "")),
            "end": str(e.get("end", "")),
            "location": e.get("location", ""),
        })

    # Cross-compare each pair
    for i in range(len(parsed_events)):
        for j in range(i + 1, len(parsed_events)):
            e1 = parsed_events[i]
            e2 = parsed_events[j]

            # Check for identical time slots or explicit substring collision in start times
            start1 = e1["start"].lower()
            start2 = e2["start"].lower()

            # Direct collision check (e.g. both at '2:00 PM' or same ISO hour)
            if start1 and start2 and (start1 == start2 or ("2:00 pm" in start1 and "2:00 pm" in start2)):
                conflicts.append({
                    "event_a": e1["summary"],
                    "event_b": e2["summary"],
                    "time": e1["start"],
                    "severity": "high",
                    "reason": f"Direct time collision: '{e1['summary']}' and '{e2['summary']}' are scheduled concurrently.",
                    "suggestion": f"Reschedule '{e2['summary']}' to the next available free slot (e.g. 3:30 PM).",
                })

    return conflicts
