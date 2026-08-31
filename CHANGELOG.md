# Changelog

All notable changes to BLITZ are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.2.1] - 2026-08-31

### Fixed

- Timeline dock opens at a usable height when a time series arrives (EVT sidecar, live ring, video). After the splash `hide()`, `show()` alone left a collapsed splitter strip that first-time users could not discover.
- RGB stacks (event-camera OFF=red / ON=green, or photos) keep the encoded LUT range — 0…1 for float, 0…255 for uint8 — instead of a plasma/bipolar stretch. Leave File-tab Normalize off.

## [2.2.0] - 2026-08-23

### Changed

- Full-frame Shade: Preview and Pre-cache compute the whole frame once; pan/zoom only transform the ViewBox.
- Pixel identity: no 1600-px working copy for Shade/Flow math.
- Zoom paint: debounced display downsample after the gesture (analysis stays full-res).
- LUT HUD shows UI event-loop lag under IDLE instead of paint FPS.

### Removed

- In-core File-tab test patterns.

[Unreleased]: https://github.com/PiMaV/BLITZ/compare/build-v2.2.1...HEAD
[2.2.1]: https://github.com/PiMaV/BLITZ/compare/build-v2.2.0...build-v2.2.1
[2.2.0]: https://github.com/PiMaV/BLITZ/releases/tag/build-v2.2.0
