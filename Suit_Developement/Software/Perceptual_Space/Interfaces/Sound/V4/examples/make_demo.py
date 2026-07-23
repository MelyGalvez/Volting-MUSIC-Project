# =================================================
# DEMO SCORE GENERATOR
#
# Writes demo_song.mid next to this script: a small
# two-track piece exercising everything Sound_Track
# supports — chords, a humanized (spread) chord,
# cross-step polyphony (held pad under a moving
# melody), a program change per track, a mid-piece
# tempo change, sustain pedal, pitch bend and
# section markers.
#
#   python examples/make_demo.py
#   python main.py examples/demo_song.mid
# =================================================

from pathlib import Path

import mido


TPB = 480          # ticks per quarter note
Q = TPB            # quarter
H = 2 * TPB        # half
W = 4 * TPB        # whole


def build():
    midi = mido.MidiFile(type=1, ticks_per_beat=TPB)

    # ---- track 0: meta (name, tempo, markers) ----

    meta = mido.MidiTrack()
    meta.append(mido.MetaMessage(
        "track_name", name="Sound_Track Demo", time=0))
    meta.append(mido.MetaMessage(
        "set_tempo", tempo=500_000, time=0))          # 120 BPM
    meta.append(mido.MetaMessage(
        "marker", text="Intro", time=0))
    meta.append(mido.MetaMessage(
        "marker", text="Theme", time=4 * W))
    meta.append(mido.MetaMessage(                     # 90 BPM
        "set_tempo", tempo=666_667, time=2 * W))
    meta.append(mido.MetaMessage(
        "marker", text="Coda", time=2 * W))
    midi.tracks.append(meta)

    # ---- track 1: piano (channel 0) ----

    def events_to_track(events):
        track = mido.MidiTrack()
        previous = 0
        for tick, message in sorted(
            events, key=lambda e: e[0]
        ):
            track.append(message.copy(time=tick - previous))
            previous = tick
        return track

    piano = []
    t = 0

    def note(events, key, start, length, vel=80, ch=0):
        events.append((start, mido.Message(
            "note_on", note=key, velocity=vel, channel=ch)))
        events.append((start + length, mido.Message(
            "note_off", note=key, velocity=0, channel=ch)))

    piano.append((0, mido.Message(
        "program_change", program=0, channel=0)))     # piano

    # Intro: C major arpeggio, quarters.
    for i, key in enumerate((60, 64, 67, 72)):
        note(piano, key, t + i * Q, Q)
    t += W

    # Whole-note bass under four quarters (polyphony
    # across steps).
    note(piano, 48, t, W, vel=70)
    for i, key in enumerate((64, 65, 67, 71)):
        note(piano, key, t + i * Q, Q)
    t += W

    # Two block chords, the second humanized (spread over
    # ~20 ms so the chord window must group it).
    for key in (60, 64, 67):
        note(piano, key, t, H, vel=90)
    for spread, key in enumerate((62, 65, 69)):
        note(piano, key, t + H + spread * 9, H, vel=90)
    t += 2 * H

    # Staccato pair (short written durations — timed mode
    # keeps them short) with sustain pedal underneath.
    piano.append((t, mido.Message(
        "control_change", control=64, value=127, channel=0)))
    note(piano, 72, t, Q // 4, vel=100)
    note(piano, 74, t + Q, Q // 4, vel=100)
    piano.append((t + 2 * Q, mido.Message(
        "control_change", control=64, value=0, channel=0)))
    t += H

    # Theme (tempo change happened at 2*W in the meta
    # track): melody with a pitch bend swell on the last
    # note, then release.
    for i, key in enumerate((67, 69, 71, 72)):
        note(piano, key, t + i * Q, Q, vel=85)
    t += W
    piano.append((t, mido.Message(
        "pitchwheel", pitch=0, channel=0)))
    note(piano, 76, t, W, vel=95)
    piano.append((t + H, mido.Message(
        "pitchwheel", pitch=2048, channel=0)))
    piano.append((t + W, mido.Message(
        "pitchwheel", pitch=0, channel=0)))
    t += W

    # Coda: final chord.
    for key in (48, 60, 64, 67, 72):
        note(piano, key, t, W, vel=75)

    midi.tracks.append(events_to_track(piano))

    # ---- track 2: strings pad (channel 1) ----

    pad = []
    pad.append((0, mido.Message(
        "program_change", program=48, channel=1)))    # strings
    pad.append((0, mido.Message(
        "control_change", control=7, value=90, channel=1)))

    # Long pads overlapping many piano steps.
    note(pad, 36, 0, 2 * W, vel=60, ch=1)
    note(pad, 43, 2 * W, 2 * W, vel=60, ch=1)
    note(pad, 40, 4 * W, 2 * W, vel=60, ch=1)
    note(pad, 36, 6 * W, W, vel=60, ch=1)

    midi.tracks.append(events_to_track(pad))

    return midi


def main():
    target = Path(__file__).parent / "demo_song.mid"
    build().save(str(target))
    print(f"Wrote {target}")


if __name__ == "__main__":
    main()
