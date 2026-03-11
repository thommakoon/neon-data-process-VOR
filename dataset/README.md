# Dataset

## Workflow

**Neon recording is copied from the Neon Application on the recording phone.** The recording folder is then placed into **Neon Player** on the desktop for playback and export.

1. Record on phone → Neon app produces a recording folder (e.g. timestamped folder with raw data).
2. Copy that folder to the PC and open it in Neon Player.
3. Use Neon Player to export sessions (e.g. gaze, IMU, events) into `neon-player-export/`.

## Directory structure

```
dataset/
├── README.md                 # This file
├── sample/                   # Example/sample exports (tracked in git)
│   ├── gaze.csv
│   ├── imu.csv
│   ├── 3d_eye_states.csv
│   ├── world_timestamps.csv
│   ├── events.csv
│   ├── blinks.csv
│   ├── fixations.csv
│   ├── saccades.csv
│   ├── labels.csv
│   ├── info.json
│   ├── scene_camera.json
│   └── template.csv
├── neon-player-export/       # Exports from Neon Player (one folder per recording)
│   └── <recording-id>/       # e.g. 2026-03-09-18-20-12
│       └── <session>_export/ # e.g. 2026-03-09_21-26-49_export
│           ├── gaze.csv
│           ├── imu.csv
│           ├── events.csv
│           ├── world_timestamps.csv
│           ├── scene_camera_intrinsics.json
│           └── ...
└── <recording-id>/           # Raw recording folders (from phone, opened in Neon Player)
    ├── info.json
    ├── template.json
    ├── wearer.json
    ├── *.dtype, *.raw        # Binary / schema files
    ├── .neon_player/         # Player cache/settings
    └── neon_player/          # Optional player copy of metadata
```

- **`sample/`** — Small example export; use it to test scripts and as a format reference. This folder is versioned.
- **`neon-player-export/<recording-id>/`** — One folder per recording; inside, each `*_export` subfolder is one exported session (gaze, IMU, events, etc.).
- **`<recording-id>/`** (at root of `dataset/`) — Raw recording as produced on the phone and opened in Neon Player; not part of the sample and typically not versioned.
