# Sound_V2 — Body Motion MIDI

Turns suit motion into live MIDI:

| Control | Body motion | Source field |
|---|---|---|
| Octave (2–6) | Torso lean | back IMUs, `roll` |
| Note (C-major degree) | Arm raise | arm IMUs, `roll` |
| Volume (CC 7) | Hand pronation | hand IMUs, `pitch` |
| Reverb (CC 91) | Elbow flexion | forearm IMUs, `heading` |
| Drums (ch 10) | Piezo strikes | firmware hit counters, velocity from hit peak |

Which anatomical motion lands on which Euler field depends on how
each IMU is mounted; the field/sign assignments live in
`config.py` and are the only thing to retune after remounting a
sensor.

## Run

```
pip install -r requirements.txt
python main.py
```

Requires a MIDI output device (the system default is picked
automatically; set `MIDI_DEVICE_ID` in `config.py` to override —
on startup the log prints the device that was chosen, and lists
all devices when none is usable).

## Architecture

- `client.py` — background polling thread (keep-alive session,
  timeouts, exponential backoff, packet validation).
- `mapping.py` — pure, unit-testable angle→music logic
  (hysteresis bin selectors, velocity mapping).
- `player.py` — `MidiEngine`: note/CC state, scheduled drum
  note-offs, all-notes-off safety.
- `interface.py` — Tk UI (`AppUI`), real connection status.
- `main.py` — 50 Hz Tk after-loop orchestration; silences all
  voices when data goes stale and while the ESP32 calibrates.

Note flutter at bin boundaries is prevented by hysteresis
(`NOTE_HYSTERESIS_DEG`); CC jitter by a ±2-step deadband.
