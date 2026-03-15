import pytest
from datetime import date, datetime, time, timedelta

# Update import path to match your project structure:
from solution import TimeWindow, BusyInterval, Slot, suggest_slots


# ---------- Helpers ----------

def combine(d: date, t: time) -> datetime:
    return datetime.combine(d, t)


def overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


def in_window(win: TimeWindow, t: time) -> bool:
    return win.start <= t < win.end


def assert_slots_basic_constraints(
    slots,
    day,
    working_hours,
    busy_intervals,
    duration,
    n,
    buffer,
    candidate_window,
):
    # Return type / length
    assert isinstance(slots, list)
    assert len(slots) <= n

    # Deterministic ordering: start_time ascending
    assert slots == sorted(slots, key=lambda s: s.start_time)

    # Each slot start must be within working_hours and candidate_window (if any)
    for s in slots:
        assert in_window(working_hours, s.start_time)
        if candidate_window is not None:
            assert in_window(candidate_window, s.start_time)

    # Each slot must fit fully inside working_hours and candidate_window
    for s in slots:
        start_dt = combine(day, s.start_time)
        end_dt = start_dt + duration

        wh_end = combine(day, working_hours.end)
        assert end_dt <= wh_end

        if candidate_window is not None:
            cw_end = combine(day, candidate_window.end)
            assert end_dt <= cw_end

    # No overlap with busy intervals, considering buffer:
    # busy interval is expanded to [start-buffer, end+buffer)
    for s in slots:
        slot_start = combine(day, s.start_time)
        slot_end = slot_start + duration

        for b in busy_intervals:
            b_start = combine(day, b.start) - buffer
            b_end = combine(day, b.end) + buffer
            assert not overlaps(slot_start, slot_end, b_start, b_end)


# ---------- Tests ----------

def test_a1_no_busy_simple_slots():
    """
    Like original "single med exact times": here, no busy events.
    Expect earliest slots within working hours (we only assert constraints + non-empty).
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(12, 0))
    busy = []
    duration = timedelta(minutes=30)

    out = suggest_slots(
        day=day,
        working_hours=working,
        busy_intervals=busy,
        duration=duration,
        n=3,
        buffer=timedelta(0),
        candidate_window=None
    )

    assert_slots_basic_constraints(out, day, working, busy, duration, 3, timedelta(0), None)
    # Should at least return 1 slot if implementation uses a reasonable slot step
    assert len(out) > 0
    # Earliest slot should be at or after working start
    assert out[0].start_time >= time(9, 0)


def test_a2_deterministic_same_inputs_same_outputs():
    """
    Like original tie/determinism check: same inputs must return identical outputs.
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(17, 0))
    busy = [
        BusyInterval(time(10, 0), time(10, 30)),
        BusyInterval(time(13, 0), time(14, 0)),
    ]
    duration = timedelta(minutes=30)
    buffer = timedelta(minutes=0)

    out1 = suggest_slots(day, working, busy, duration, n=10, buffer=buffer, candidate_window=None)
    out2 = suggest_slots(day, working, busy, duration, n=10, buffer=buffer, candidate_window=None)

    assert [s.start_time for s in out1] == [s.start_time for s in out2]
    assert_slots_basic_constraints(out1, day, working, busy, duration, 10, buffer, None)


def test_a3_overlapping_and_unsorted_busy_intervals_handled():
    """
    Busy intervals may be unsorted/overlapping; suggestions must still avoid conflicts.
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(12, 0))
    busy = [
        BusyInterval(time(10, 30), time(11, 0)),
        BusyInterval(time(10, 0), time(10, 45)),   # overlaps with above
        BusyInterval(time(9, 30), time(9, 45)),    # unsorted relative order
    ]
    duration = timedelta(minutes=15)

    out = suggest_slots(day, working, busy, duration, n=8, buffer=timedelta(0), candidate_window=None)
    assert_slots_basic_constraints(out, day, working, busy, duration, 8, timedelta(0), None)


def test_a4_candidate_window_respected():
    """
    Like original allowed_window respected: here we add an extra candidate window restriction.
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(17, 0))
    candidate = TimeWindow(time(13, 0), time(15, 0))
    busy = []
    duration = timedelta(minutes=30)

    out = suggest_slots(day, working, busy, duration, n=5, buffer=timedelta(0), candidate_window=candidate)
    assert_slots_basic_constraints(out, day, working, busy, duration, 5, timedelta(0), candidate)

    # Every slot must start within candidate window
    assert all(candidate.start <= s.start_time < candidate.end for s in out)


def test_a5_buffer_eliminates_small_gaps():
    """
    Like original rate-limit constraint: here buffer is the key extra constraint.
    With buffer, some slots that would otherwise fit should be invalid.
    """
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(11, 0))
    # Two busy intervals leaving a 20-minute gap between them
    busy = [
        BusyInterval(time(9, 30), time(9, 50)),
        BusyInterval(time(10, 10), time(10, 30)),
    ]
    duration = timedelta(minutes=20)

    # Without buffer: the gap 9:50–10:10 is exactly 20 minutes -> potentially valid
    out_no_buffer = suggest_slots(day, working, busy, duration, n=10, buffer=timedelta(0), candidate_window=None)
    assert_slots_basic_constraints(out_no_buffer, day, working, busy, duration, 10, timedelta(0), None)

    # With 5-min buffer: effective busy expands, gap shrinks -> should reduce or remove those slots
    buf = timedelta(minutes=5)
    out_with_buffer = suggest_slots(day, working, busy, duration, n=10, buffer=buf, candidate_window=None)
    assert_slots_basic_constraints(out_with_buffer, day, working, busy, duration, 10, buf, None)

    # Buffer should not increase number of available slots (monotonicity)
    assert len(out_with_buffer) <= len(out_no_buffer)


#################################################################################
# Add your own additional tests here to cover more cases and edge cases as needed.
#################################################################################

# Covers C1
def test_slots_are_chronological():

    day = date(2026, 3, 15)

    working_hours = TimeWindow(time(9,0), time(12,0))

    busy_intervals = []

    duration = timedelta(minutes=20)

    slots = suggest_slots(
        day,
        working_hours,
        busy_intervals,
        duration,
        5,
        timedelta(0)
    )

    start_times = [slot.start_time for slot in slots]

    assert start_times == sorted(start_times)


# Covers C1, C6
def test_basicSched():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(12, 0))
    busy = []
    duration = timedelta(minutes=30)

    out = suggest_slots(
        day=day,
        working_hours=working,
        busy_intervals=busy,
        duration=duration,
        n=3,
        buffer=timedelta(0),
        candidate_window=None,
    )

    assert_slots_basic_constraints(out, day, working, busy, duration, 3, timedelta(0), None)
    assert len(out) > 0
    assert out[0].start_time == time(9, 0)


# Covers C3,C6
def test_basicSched2():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(17, 0))
    busy = [
        BusyInterval(time(10, 0), time(10, 30)),
        BusyInterval(time(13, 0), time(14, 0)),
    ]
    duration = timedelta(minutes=30)
    buffer = timedelta(0)

    out1 = suggest_slots(day, working, busy, duration, n=10, buffer=buffer, candidate_window=None)
    out2 = suggest_slots(day, working, busy, duration, n=10, buffer=buffer, candidate_window=None)

    assert [s.start_time for s in out1] == [s.start_time for s in out2]
    assert_slots_basic_constraints(out1, day, working, busy, duration, 10, buffer, None)


# Covers AC8, C2
def test_busyInterval():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(17, 0))
    busy = [
        BusyInterval(time(10, 30), time(11, 0)),
        BusyInterval(time(10, 0), time(10, 45)),
        BusyInterval(time(9, 30), time(9, 45)),
    ]
    duration = timedelta(minutes=15)

    out = suggest_slots(
        day=day,
        working_hours=working,
        busy_intervals=busy,
        duration=duration,
        n=8,
        buffer=timedelta(0),
        candidate_window=None,
    )

    assert_slots_basic_constraints(out, day, working, busy, duration, 8, timedelta(0), None)

# Covers C4, AC6
def test_invalidWorkhour():
    day = date(2026, 2, 24)

    with pytest.raises(ValueError):
        suggest_slots(
            day=day,
            working_hours=TimeWindow(time(17, 0), time(9, 0)),  # start time greater than end time
            busy_intervals=[],
            duration=timedelta(minutes=30),
            n=5,
            buffer=timedelta(0),
            candidate_window=None,
        )


# Covers C4, A3, AC6
def test_invalidN():
    day = date(2026, 2, 24)

    with pytest.raises(ValueError):
        suggest_slots(
            day=day,
            working_hours=TimeWindow(time(9, 0), time(17, 0)),
            busy_intervals=[],
            duration=timedelta(minutes=30), 
            n=-1,                                   # neg n val
            buffer=timedelta(0),
            candidate_window=None,
        )


# Covers C4, AC6
def test_invalidBusy():
    day = date(2026, 2, 24)

    with pytest.raises(ValueError):
        suggest_slots(
            day=day,
            working_hours=TimeWindow(time(9, 0), time(17, 0)),
            busy_intervals=[BusyInterval(time(11, 0), time(10, 0))],  # start time greater than end time
            duration=timedelta(minutes=30),
            n=5,
            buffer=timedelta(0),
            candidate_window=None,
        )


# Covers C4, AC6
def test_invalidBuffer():
    day = date(2026, 2, 24)

    with pytest.raises(ValueError):
        suggest_slots(
            day=day,
            working_hours=TimeWindow(time(9, 0), time(17, 0)),
            busy_intervals=[],
            duration=timedelta(minutes=30),
            n=5,
            buffer=timedelta(minutes=-5),       #neg value invalid for buffer time
            candidate_window=None,
        )

# Covers C5, AC7
def test_emptyList():
    day = date(2026, 2, 24)
    working = TimeWindow(time(9, 0), time(10, 0))
    busy = [BusyInterval(time(9, 20), time(9, 40))]
    duration = timedelta(minutes=25)                # no available gap so no available times possible

    out = suggest_slots(
        day=day,
        working_hours=working,
        busy_intervals=busy,
        duration=duration,
        n=10,
        buffer=timedelta(0),
        candidate_window=None,
    )

    assert out == []

# Covers C2, AC4, make sure candidate window time slot outputs are valid
def test_candidate_window_restriction():

    day = date(2026, 3, 15)

    working_hours = TimeWindow(time(9,0), time(17,0))

    candidate_window = TimeWindow(time(13,0), time(15,0))       # window from 13:00 to 15:00 so slots should lie between these

    busy_intervals = []

    duration = timedelta(minutes=30)

    slots = suggest_slots(
        day,
        working_hours,
        busy_intervals,
        duration,
        5,
        timedelta(0),
        candidate_window
    )

    for slot in slots:
        assert slot.start_time >= candidate_window.start
        assert (datetime.combine(day, slot.start_time) + duration).time() <= candidate_window.end
