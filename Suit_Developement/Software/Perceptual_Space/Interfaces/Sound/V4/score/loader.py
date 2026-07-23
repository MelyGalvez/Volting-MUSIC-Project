# =================================================
# SCORE LOADER
#
# MIDI file -> Score. This is the only module that
# touches the MIDI file format (through mido) and it
# runs entirely at load time: tempo integration,
# note on/off pairing, chord grouping and control
# attachment are all precomputed here so playback
# never parses, pairs or searches anything.
#
# Pipeline:
#   1. preflight the raw header (clear errors for
#      non-MIDI, SMPTE division, format 2)
#   2. merge all tracks into one absolute-tick stream
#      with provenance (track index, file order)
#   3. build the tempo map and a tick -> seconds
#      converter (nominal file time)
#   4. pair note-ons with note-offs (retrigger and
#      dangling notes handled deterministically)
#   5. group onsets into Steps (chords) by a time
#      window anchored at the first note of the group
#   6. attach non-note channel messages and labels to
#      the surrounding steps
# =================================================

from bisect import bisect_right
from pathlib import Path

import mido

from score.model import ControlEvent, Note, Score, ScoreError, Step


DEFAULT_TEMPO_US = 500_000     # MIDI default: 120 BPM

# mido message type -> ControlEvent kind for every
# non-note channel message we preserve.
_CONTROL_KINDS = {
    "program_change": "program",
    "control_change": "control",
    "pitchwheel": "pitchwheel",
    "aftertouch": "aftertouch",
    "polytouch": "polytouch",
}


# ------------------- Preflight --------------------


def _preflight(path):
    """
    Validate the raw SMF header before handing the file to
    mido, so unsupported variants fail with a precise
    message instead of a parser traceback deep inside
    playback preparation.
    """

    try:
        with open(path, "rb") as fh:
            head = fh.read(14)
    except OSError as exc:
        raise ScoreError(f"Cannot read file: {exc}") from exc

    if len(head) < 14 or head[:4] != b"MThd":
        raise ScoreError(
            "Not a Standard MIDI File (missing MThd header)."
        )

    header_len = int.from_bytes(head[4:8], "big")
    if header_len < 6:
        raise ScoreError("Corrupt MIDI header.")

    fmt = int.from_bytes(head[8:10], "big")
    division = int.from_bytes(head[12:14], "big")

    if fmt == 2:
        raise ScoreError(
            "SMF format 2 (independent sequences) is not "
            "supported; export as format 0 or 1."
        )

    if division & 0x8000:
        raise ScoreError(
            "SMPTE time division is not supported; export "
            "with metrical (ticks per beat) timing."
        )


# ------------------ Tempo mapping ------------------


class _TempoMap:
    """
    tick -> nominal seconds converter built from the
    set_tempo events. Segments store the cumulative time
    at each tempo change so conversion is a binary search
    plus one multiplication.
    """

    def __init__(self, tempo_events, ticks_per_beat):
        # tempo_events: [(tick, us_per_beat)] in file order;
        # the last event wins on duplicate ticks.
        self._tpb = ticks_per_beat

        merged = {0: DEFAULT_TEMPO_US}
        for tick, tempo in tempo_events:
            merged[tick] = tempo

        self._ticks = []
        self._seconds = []
        self._tempos = []

        seconds = 0.0
        prev_tick = 0
        prev_tempo = merged[0]

        for tick in sorted(merged):
            tempo = merged[tick]
            seconds += (
                (tick - prev_tick) * prev_tempo
                / (ticks_per_beat * 1e6)
            )
            self._ticks.append(tick)
            self._seconds.append(seconds)
            self._tempos.append(tempo)
            prev_tick, prev_tempo = tick, tempo

        self.entries = tuple(zip(self._ticks, self._tempos))

    def to_seconds(self, tick):
        i = bisect_right(self._ticks, tick) - 1
        return self._seconds[i] + (
            (tick - self._ticks[i]) * self._tempos[i]
            / (1e6 * self._tpb)
        )


# ------------------- Note pairing -------------------


class _OpenNote:
    __slots__ = ("key", "velocity", "channel", "track", "tick")

    def __init__(self, key, velocity, channel, track, tick):
        self.key = key
        self.velocity = velocity
        self.channel = channel
        self.track = track
        self.tick = tick


def _close(open_note, end_tick, to_s):
    """
    Turn an open note into a finished Note. Zero-length
    notes (same-tick on/off, present in quantized files)
    get a one-tick minimum so end > start always holds and
    the deterministic release rule stays well ordered.
    """

    end_tick = max(end_tick, open_note.tick + 1)
    start_s = to_s(open_note.tick)
    end_s = to_s(end_tick)

    if end_s <= start_s:
        end_s = start_s + 1e-3

    return Note(
        key=open_note.key,
        velocity=open_note.velocity,
        channel=open_note.channel,
        track=open_note.track,
        start_tick=open_note.tick,
        end_tick=end_tick,
        start_s=start_s,
        end_s=end_s,
    )


# --------------------- Loading ----------------------


def load_score(
    path,
    *,
    chord_window_s=0.030,
    channel_filter=None,
    track_filter=None,
):
    """
    Load a Standard MIDI File into an immutable Score.

    chord_window_s: onsets within this window of the first
    note of a group form one Step (chord).
    channel_filter / track_filter: optional sets restricting
    which channel messages are kept. Tempo and labels are
    global and always honored.

    Raises ScoreError with a readable message on any file
    that cannot be navigated.
    """

    path = str(path)
    _preflight(path)

    try:
        midi = mido.MidiFile(path, clip=True)
    except ScoreError:
        raise
    except Exception as exc:
        raise ScoreError(f"Cannot parse MIDI file: {exc}") from exc

    ticks_per_beat = midi.ticks_per_beat
    if not ticks_per_beat or ticks_per_beat <= 0:
        raise ScoreError("Invalid ticks-per-beat division.")

    # ---- 1. merge to absolute ticks with provenance ----

    events = []          # (tick, track_idx, seq, message)
    track_names = []
    max_tick = 0
    seq = 0

    for track_idx, track in enumerate(midi.tracks):
        tick = 0
        name = ""

        for message in track:
            tick += message.time

            if message.is_meta and message.type == "track_name" \
                    and not name:
                name = message.name

            events.append((tick, track_idx, seq, message))
            seq += 1

        max_tick = max(max_tick, tick)
        track_names.append(name)

    # Same tick: keep track order then file order, so
    # multi-track files replay channel messages in a stable,
    # file-faithful order.
    events.sort(key=lambda e: (e[0], e[1], e[2]))

    # ---- 2. tempo map (global, ignores filters) ----

    tempo_events = [
        (tick, msg.tempo)
        for tick, _t, _s, msg in events
        if msg.is_meta and msg.type == "set_tempo"
    ]
    tempo_map = _TempoMap(tempo_events, ticks_per_beat)
    to_s = tempo_map.to_seconds

    # ---- 3. pair notes, collect controls and labels ----

    def wanted(track_idx, channel):
        if track_filter is not None and track_idx not in track_filter:
            return False
        if channel_filter is not None and channel not in channel_filter:
            return False
        return True

    notes = []
    open_notes = {}      # (channel, key) -> _OpenNote
    controls = []        # ControlEvent, in merged order
    markers = {}         # tick -> text
    lyrics = {}          # tick -> text
    channels = set()

    for tick, track_idx, _s, msg in events:
        if msg.is_meta:
            if msg.type == "marker" and msg.text.strip():
                base = markers.get(tick)
                markers[tick] = (
                    f"{base} / {msg.text.strip()}" if base
                    else msg.text.strip()
                )
            elif msg.type == "lyrics" and msg.text.strip():
                lyrics.setdefault(tick, msg.text.strip())
            continue

        channel = getattr(msg, "channel", None)
        if channel is None:
            continue                     # sysex etc.: not navigable state

        if not wanted(track_idx, channel):
            continue

        if msg.type == "note_on" and msg.velocity > 0:
            slot = (channel, msg.note)
            previous = open_notes.pop(slot, None)
            if previous is not None:
                # Retrigger before the off arrived: the
                # audible reality is that the first note
                # ends where the second starts.
                notes.append(_close(previous, tick, to_s))

            open_notes[slot] = _OpenNote(
                msg.note, msg.velocity, channel, track_idx, tick
            )
            channels.add(channel)

        elif msg.type == "note_off" or (
            msg.type == "note_on" and msg.velocity == 0
        ):
            slot = (channel, msg.note)
            opened = open_notes.pop(slot, None)
            if opened is not None:
                notes.append(_close(opened, tick, to_s))
            # Unmatched note-off: silently ignored (harmless
            # and present in real-world files).

        elif msg.type in _CONTROL_KINDS:
            kind = _CONTROL_KINDS[msg.type]

            if kind == "program":
                data1, data2 = msg.program, 0
            elif kind == "control":
                data1, data2 = msg.control, msg.value
            elif kind == "pitchwheel":
                data1, data2 = msg.pitch + 8192, 0
            elif kind == "aftertouch":
                data1, data2 = msg.value, 0
            else:  # polytouch
                data1, data2 = msg.note, msg.value

            controls.append(ControlEvent(
                kind=kind, channel=channel,
                data1=data1, data2=data2,
                tick=tick, time_s=to_s(tick),
            ))
            channels.add(channel)

    # Dangling note-ons (missing note-off): close at the
    # end of the file so they exist and terminate.
    for opened in open_notes.values():
        notes.append(_close(opened, max_tick, to_s))

    if not notes:
        raise ScoreError(
            "The file contains no notes"
            + (" (after channel/track filters)."
               if channel_filter or track_filter else ".")
        )

    # ---- 4. group onsets into steps (chords) ----

    notes.sort(key=lambda n: (n.start_tick, n.channel, n.key))

    groups = []
    anchor_s = None

    for note in notes:
        if anchor_s is None or \
                note.start_s - anchor_s > chord_window_s:
            groups.append([note])
            anchor_s = note.start_s
        else:
            groups[-1].append(note)

    # ---- 5. attach controls / labels, build steps ----

    first_tick = groups[0][0].start_tick
    setup = tuple(c for c in controls if c.tick <= first_tick)
    remaining = [c for c in controls if c.tick > first_tick]

    label_ticks = sorted(set(markers) | set(lyrics))

    def label_at(tick_lo, tick_hi):
        """Labels with tick in (tick_lo, tick_hi]; marker wins."""
        texts = []
        for t in label_ticks:
            if tick_lo < t <= tick_hi:
                texts.append(markers.get(t) or lyrics.get(t))
        return " · ".join(texts) if texts else None

    steps = []
    cursor = 0
    prev_tick = -1
    section = None

    for index, group in enumerate(groups):
        tick = group[0].start_tick

        attached = []
        while cursor < len(remaining) and \
                remaining[cursor].tick <= tick:
            attached.append(remaining[cursor])
            cursor += 1

        label = label_at(prev_tick, tick) if index else \
            label_at(-1, tick)
        if label:
            section = label

        steps.append(Step(
            index=index,
            tick=tick,
            time_s=group[0].start_s,
            notes=tuple(group),
            controls=tuple(attached),
            label=label,
            section=section,
        ))
        prev_tick = tick

    tail_controls = tuple(remaining[cursor:])

    name = track_names[0].strip() if track_names and \
        track_names[0].strip() else Path(path).stem

    return Score(
        name=name,
        source_path=path,
        ticks_per_beat=ticks_per_beat,
        steps=tuple(steps),
        setup=setup,
        tail_controls=tail_controls,
        tempo_map=tempo_map.entries,
        duration_s=to_s(max_tick),
        channels=frozenset(channels),
        track_names=tuple(track_names),
    )
