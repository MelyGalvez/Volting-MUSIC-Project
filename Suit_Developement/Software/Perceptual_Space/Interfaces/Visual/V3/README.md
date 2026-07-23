# Visual_V2 — 3D Skeleton Viewer

Renders the suit as an articulated skeleton (OpenGL, 60 FPS) and
records sessions to CSV.

## Run

```
pip install -r requirements.txt
python main.py
```

| Input | Action |
|---|---|
| Mouse drag | Orbit camera |
| Scroll wheel | Zoom |
| `C` | Software re-zero (hold T-pose; needs fresh data) |
| `R` | CSV recording on/off (`capture_YYYYMMDD_HHMMSS.csv`) |
| `ESC` | Exit |

The window title shows the live connection state
(`LIVE` / `STALE` / `DISCONNECTED`, plus `REC` while recording).
On data loss the skeleton holds its last pose.

## Orientation pipeline

1. Firmware sends per-sensor **local delta** quaternions
   (rotation since T-pose, in the sensor's calibration frame —
   see `../PROTOCOL.md`).
2. `calibration.py` optionally re-zeros against the pose captured
   with `C` (`conj(ref) * q`, same local convention, so the two
   calibrations compose exactly).
3. `imu_mapping.py` re-expresses the rotation around body axes
   with the per-sensor mounting correction `C · q · C*`. The
   mounting table (`MOUNT_CORRECTION`) states where each sensor
   axis points on the body in T-pose — edit it when a sensor is
   remounted.
4. `orientation_filter.py` smooths with SLERP (τ = 50 ms),
   rejects isolated implausible jumps, and accepts genuinely fast
   motion immediately when two consecutive samples agree.
5. `skeleton.py` runs forward kinematics and draws.
