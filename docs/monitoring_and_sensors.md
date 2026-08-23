# Monitoring, CPU peak and sensors

## What BLITZ shows

- **CPU %**: Bench shows **avg** over all cores and the **busiest core**.
  `psutil.cpu_percent(percpu=True)` each tick (~0.5 s) while the Bench tab is
  open. A 10% system average on 16 cores is often **one core at ~100%** —
  Shade/Flow ∇z and D8 are single-thread NumPy, not a multicore kernel.
- **UI lag** (LUT HUD under IDLE, always on): median Qt event-loop lag over
  ~1 s (label) from a 250 ms probe timer; amp shows the last **30 s** with a
  fixed Y range **0–300 ms** and traffic-light bands (green &lt;100 ms smooth,
  yellow 100–300, red &gt;300 clips at top). Near 0 ms when the GUI thread is
  free; rises when pan/zoom, BUSY work, or overlays block the loop. Not paint
  FPS (Qt has no hidden 60 Hz loop), not capture FPS, not Shade/Flow `1/dt`.
  No CPU/RAM on that first-page HUD — those stay on the Bench tab.
- **Overlay compute** (Bench tab + Shade/Flow status): last hillshade/D8 time
  as milliseconds and theoretical `1/dt` at the current crop.
- **CPU peak**: Rolling maximum over the last N samples in the Bench sparkline. If the current value is lower than a recent peak, the label shows e.g. `CPU: 8.2% (peak 47%)` so short load spikes are visible even when the average stays low.
- **RAM, Disk I/O**: From psutil on the Bench tab only; same on all platforms.

## Why “low CPU” can still mean loud fans

1. **Averaging**: Task Manager and our CPU % average over time and over all cores. Brief spikes (e.g. one core at 100% for 200 ms) get diluted — e.g. 32 cores × 1 s → one core at 100% for 0.2 s looks like ~0.6% in a 1 s average.
2. **GPU**: Fans often react to GPU load and temperature. Task Manager shows GPU separately; high GPU use can spin fans even when CPU % is low.
3. **Thermal inertia**: After a load, the CPU stays warm; the fan curve may keep RPM high until temperatures drop.

Use the **CPU peak** in the Bench tab to see if there were recent spikes that could explain fan activity.

## Fan speed and temperatures on Windows

**Under Windows, psutil does not provide fan speeds or hardware temperatures.**  
`psutil.sensors_fans()` and `psutil.sensors_temperatures()` are only implemented on Linux (and partly FreeBSD). On Windows they are not available, so BLITZ cannot show fan RPM or CPU/GPU temperatures from the OS without extra drivers or tools.

If you need to correlate fan noise with actual values:

- Use **Task Manager → Performance** and check both **CPU** and **GPU**.
- Use a hardware monitor that talks to the firmware/drivers (e.g. HWiNFO64, Open Hardware Monitor, or the vendor’s tool) for fan RPM and temperatures.

The codebase exposes:

- `get_sensors_fans()` / `get_sensors_temperatures()` in `blitz/tools.py`: on Windows they return `{}`; on Linux they return psutil’s sensor data so we could show it in the UI later if needed.
- `get_cpu_freq_mhz()`: current CPU frequency in MHz (on Windows often the nominal/base frequency only).
