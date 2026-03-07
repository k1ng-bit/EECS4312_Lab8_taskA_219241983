## Student Name: Daksh Dave
## Student ID: 219241983

"""
Task A: Appointment Timeslot Recommender (Stub)

In this lab, you will design and implement an Appointment Slot Recommender using an LLM assistant
as your primary programming collaborator.

You are asked to implement a Python module that recommends available meeting slots within a
defined working window.

The system must:
  • Accept working hours (start and end time).
  • Accept a list of existing busy intervals.
  • Accept a required meeting duration.
  • Accept an optional buffer time between meetings.
  • Optionally restrict suggestions to a candidate time window.
  • Return chronologically ordered appointment slots that satisfy all constraints.

The system must ensure that:
  • Suggested slots fall within working hours.
  • Suggested slots do not overlap busy intervals.
  • Buffer time is respected when evaluating availability.
  • Output ordering is deterministic under identical inputs.

The module must preserve the following invariants:
  • Returned slots must be at least as long as the required duration.
  • No returned slot may violate buffer constraints.
  • The returned list must reflect the current system state.

The system must correctly handle non-trivial scenarios such as:
  • Adjacent busy intervals.
  • Very small gaps between meetings.
  • Buffers eliminating otherwise valid availability.
  • Overlapping or unsorted busy intervals.
  • A meeting duration longer than any available gap.
  • No availability within the working window.

Output:
  The output consists of the next N valid appointment suggestions in chronological order.
  Behavior must be deterministic under ties (if any).

See the lab handout for full requirements.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, time
from typing import List, Optional, Tuple


# ---------------- Data Models ----------------

@dataclass(frozen=True)
class TimeWindow:
    """
    A daily time window.
    Assumption (unless stated otherwise in handout): non-wrapping window where start < end.
    """
    start: time
    end: time


@dataclass(frozen=True)
class BusyInterval:
    """
    A busy interval on the given day.
    Invariant: start < end
    """
    start: time
    end: time


@dataclass(frozen=True)
class Slot:
    """
    A recommended appointment slot.

    start_time is a time-of-day within the working window.
    Deterministic ordering: sort by start_time ascending.
    """
    start_time: time


class InfeasibleSchedule(Exception):
    """Raised when no valid slots can be produced (if required by handout)."""
    pass

#----------------- Helper Function --------------
def merge_intervals(intervals: List[Tuple[int, int]]) -> List[Tuple[int, int]]:  # incase two busy intervals are overlapping then merge
    if not intervals:
        return []

    intervals = sorted(intervals)
    merged = [intervals[0]]

    for start, end in intervals[1:]:
        last_start, last_end = merged[-1]

        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    return merged

# ---------------- Core Function ----------------

def suggest_slots(
    day: date,
    working_hours: TimeWindow,
    busy_intervals: List[BusyInterval],
    duration: timedelta,
    n: int,
    buffer: timedelta = timedelta(0),
    candidate_window: Optional[TimeWindow] = None
) -> List[Slot]:
    """
    Suggest up to the next n valid appointment slots (start times) for the given day.

    Args:
        day: the calendar day for which to suggest slots.
        working_hours: the allowed working window for meetings (start < end).
        busy_intervals: list of busy time intervals (may be overlapping / unsorted).
        duration: required meeting length (must be > 0).
        n: maximum number of slot suggestions to return (n >= 0).
        buffer: optional buffer time required between meetings (buffer >= 0).
        candidate_window: optional extra restriction on suggestions (must lie within this window too).

    Returns:
        A list of Slot objects, sorted by start_time ascending, deterministic under identical inputs.
        If no suitable time slots are available, return an empty list.

    Notes:
        - Suggested slots must fall within working_hours (and candidate_window if provided).
        - Suggested slots must not overlap busy_intervals, considering buffer time.
        - You are free to choose internal representation; inputs use time-of-day.
        - See lab handout for required slot granularity (e.g., 5-min/15-min steps), if any.
    """

    ##################################################################
    # TODO: Implement as per lab handout requirements and constraints.
    ##################################################################

    if working_hours.start >= working_hours.end:        #if start<end for working hours window constraint
        raise ValueError("working_hours Start Time must be lesser than the End Time !")

    if duration <= timedelta(0):                # duration must not be less than or wqual to 0
        raise ValueError("duration must be greater than 0 !")

    if n < 0:                                   # n must be greater than equal to 0
        raise ValueError("n must be >= 0 !")

    if buffer < timedelta(0):                   # handle the buffer time consraint
        raise ValueError("buffer must be >= 0 !")

    if candidate_window is not None and candidate_window.start >= candidate_window.end:
        raise ValueError("candidate_window Start time must be earlier than End time !")

    for interval in busy_intervals:             #checking for any error in the busy intervals list
        if interval.start >= interval.end:
            raise ValueError("busy interval start must be earlier than end")

    if n == 0:                          # if n is 0, then empty list returned
        return []

    def combine(t: time) -> datetime:
        return datetime.combine(day, t)

    work_start = combine(working_hours.start)       #working hour window
    work_end = combine(working_hours.end)

    start_limit = work_start
    end_limit = work_end

    if candidate_window is not None:        #handlling the limits for the returning time slots
        start_limit = max(start_limit, combine(candidate_window.start))
        end_limit = min(end_limit, combine(candidate_window.end))

    if start_limit >= end_limit:
        return []

    latest_start = end_limit - duration
    if latest_start < start_limit:
        return []

    busy_ranges = []
    for interval in busy_intervals:
        start_dt = combine(interval.start) - buffer
        end_dt = combine(interval.end) + buffer
        busy_ranges.append((start_dt, end_dt))

    merged_busy = merge_intervals(busy_ranges)

    slots = []
    step = timedelta(minutes=1)
    current = start_limit

    while current <= latest_start and len(slots) < n:
        slot_end = current + duration
        conflict = False

        for busy_start, busy_end in merged_busy:
            if current < busy_end and busy_start < slot_end:
                conflict = True
                break

        if not conflict:
            slots.append(Slot(start_time=current.time()))

        current += step

    return slots
