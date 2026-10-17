# Project context: Wi-Fi sensing game for SwampHacks

This file is read by Claude Code. It holds the decisions made while planning this project.
Treat it as the plan of record; update it as decisions change.

## The idea in one line
A real person hidden behind a curtain plays Red Light, Green Light, and **Wi-Fi signals** (ESP32 CSI)
decide whether they moved. The same sensing (presence, motion, breathing, falls) is then shown in
several real-world use cases, each backed by a trained ML model and a measured accuracy number.
A **Roblox** world mirrors the real person as an avatar, and online players can call "red light".

Pitch line: "One pair of $5 Wi-Fi chips, no cameras: a game, a rescue sweep, a hot-car alarm, lights
that know you're still there, and fall detection for grandparents. If Wi-Fi can catch you holding your
breath behind a curtain, it can find someone who's still in a room after a disaster."

**Team: Arwa, solo** (as of 2026-10-17; the original team moved to another project). Scope below is
sized for one person; cut from the bottom up.

## Why this project (the goal)
Beat past winners like Farsight (rover + VR + Gaussian splatting) and Permanence (3D VLM + object
tracking + AR "x-ray"). What made them win: an "impossible" moment visible in a 3-minute demo, recent
research, real hardware, measured numbers, and judges taking part. Judges score: technical difficulty,
usefulness, wow/creativity, completeness (works live), presentation. Line count does not matter.

## Hardware we have / plan to buy
- ESP32 dev boards (classic ESP32, e.g. 3-pack ESP-WROOM-32 with CP2102). Classic ESP32 supports CSI.
  Start with 2 (one TX, one RX). 4-5 ESP32-S3 boards only if we attempt pose/location.
- MG90S servos, motors (one becomes the booth fan), wires, sensors. **No 3D printer** (use cardboard/foam board).
- Laptop does all processing. Phones available. Speaker. LED strip.
- Optional: MAX30102 fingertip pulse sensor (~$5) for ground truth; MQ-2 / ENS160 gas sensors;
  vibration motor; small travel router (do not rely on venue Wi-Fi); phone hotspot.
- **Plan B sensors:** HLK-LD2410 24 GHz radar (~$5-10, motion + still presence),
  Seeed MR60BHA2 60 GHz radar (~$30, breathing + heart rate).

## Use cases (one detector, several stories)
Like Permanence (one tracking pipeline, framed as several applications), every use case reuses the same
signals. Use cases are screens/framings on one pipeline, not separate builds.

| Use case | What Wi-Fi detects | Demo | ML model that proves it |
|---|---|---|---|
| **Red Light, Green Light** (+ Wi-Fi Heist) | motion vs frozen | judge behind the curtain; Roblox avatar mirrors them | state classifier EMPTY / STILL / MOVING |
| **Disaster / firefighter room sweep** | someone still present + breathing | after a round: thunder + flashing LEDs, dashboard "Survivor detected, breathing, not moving, Priority 1" | presence + breathing-present classifier |
| **Hot car alarm** (child/pet left in a parked car) | still person breathing in an enclosed space | person sits frozen in a cardboard "car seat"; alert fires | same presence + breathing model |
| **Smart lights that stay on when you sit still** | presence without motion | LED strip = room light; stays on while the person is frozen (where a PIR motion sensor would switch off), turns off when they leave | presence classifier |
| **Guardian fall detection** | sudden spike, then lying still | Arwa falls onto a mat (never a judge) -> "Fall detected, breathing" | activity classifier: walk / sit down / lie down / fall |

Notes:
- "Hot car" is a real requirement area (Euro NCAP rewards child presence detection; cars mostly use
  60 GHz radar). Our version is a low-cost Wi-Fi alternative; say so.
- "Smart lights" = presence (breathing-level micro-motion), NOT heartbeat.
- Stretch: **occupancy count 0-3 people** ("how many are still in this room?" for evacuations), ML
  classifier, medium-low confidence; show only if the measured accuracy is good.

**Removed (don't make sense with 2 ESP32s / would be overclaiming):**
- Wi-Fi heart rate (ESP32 CSI too noisy; MAX30102 only as ground truth for testing, never claimed as Wi-Fi).
- Stadium / concert stampede crowd detection (one link can't see hundreds of people).
- Gas sensor, booth fan, servo gator, Zen Master, Roblox rescue operation.

## Roblox scope (decided: keep it simple)
- **In scope:** the real person's avatar moves when they move and freezes/gets knocked out based on
  Wi-Fi; Roblox players can press "red light" (triggers the booth sound/LEDs).
- **Optional stretch:** simple disaster visuals in Roblox (camera shake, falling parts, rising water)
  timed with the disaster twist.
- **Cut / too difficult for now:** a full Roblox rescue operation (multiplayer digging, rescue
  gameplay). Rescue lives on the web dashboard instead.
- Original art only; do not copy the Squid Game doll or other copyrighted assets.

## The cue problem (important)
The hidden player cannot see the screen or anything on the audience side, so "red light / green light"
must reach them inside the hiding spot:
1. **Speaker** announcing green/red + sound effects (primary; also carries the AI gator voice).
2. **LED strip on the player's side** of the curtain (green/red flood; glow is visible to the audience too).
3. Optional: small tablet/old phone inside the booth showing red/green or their Roblox avatar.
4. Optional: vibration motor the player holds.

## Feature list (locked scope, solo)
| Priority | Feature | Est. effort (hours) |
|---|---|---|
| Core | Wi-Fi motion + calibration (`sensing/host`, done; needs real-board testing) | 3-5 |
| Core | Red Light, Green Light web page + speaker cue + Wi-Fi Heist | 5-8 |
| Core | Live "Wi-Fi vision" graph (proves it's real) | 2-3 |
| Core | ML: data collection tool, training script, confusion matrices | 6-10 |
| Surprise | Roblox avatar moves/freezes; Roblox players trigger red light | 6-10 |
| Surprise | Use-case dashboard: rescue sweep, hot car, smart lights, fall alert | 4-6 |
| Stretch | Fall detection model + demo | 3-5 |
| Stretch | LED strip (player-side cue + "smart light" demo) | 2 |
| Stretch | Occupancy count 0-3; camera-vs-Wi-Fi accuracy scoreboard; gator voice lines via macOS `say` | 4-8 |
| Cut | see "Removed" above; full skeleton pose; 3D printed parts | - |

Core + Surprise is ~26-42 hours: more than one person has at a 36 h hackathon, so do the ESP32
bring-up, go/no-go test, and as much data collection as the rules allow BEFORE the event. Always keep
one working demo; record the backup video as soon as Red Light, Green Light works.

## Demo flow (about 3 minutes)
1. Play: judge plays Red Light, Green Light behind the curtain, gets caught; Roblox avatar freezes/gets
   knocked out; replay shows the signal spike.
2. Twist: "Now you're trapped." Thunder + flashing LEDs; dashboard: "Survivor detected, breathing."
3. Same signal, other stories (one screen each, ~15 s): hot car alert, smart light stays on while still.
4. Guardian: Arwa falls onto the mat -> "Fall detected."
5. Proof: confusion matrices / accuracy per use case, measured at the venue. Pitch line.

## Honest confidence
- High: Roblox <-> laptop, ESP32 LEDs/servo/fan, game logic, booth effects.
- Medium-high: Wi-Fi presence/motion behind a curtain at 1-2 m.
- Medium: reliably telling "frozen" from small movements in a crowded hall (core risk).
- Medium: rule-based fall detection (big spike then stillness is a strong pattern).
- Medium-low: breathing in a crowd. Low: full pose on single-antenna ESP32.
- Medium: fall vs sit vs lie down with an ML classifier (well studied: WiFall, RT-Fall), if trained on
  data recorded at the venue spot. Medium-low: counting 0-3 people.
- Wi-Fi heart rate is not reliable on ESP32; use camera rPPG (pyVHR) or MAX30102 if needed.
- Wi-Fi does NOT go through meters of rubble/concrete. Realistic: fabric, drywall, wood, one interior
  wall, a few meters. Frame rescue use as light debris / wood-frame hurricane damage / room sweeps.
  Deep rubble needs radar like NASA JPL's FINDER. Do not overclaim to judges.

## Go/no-go test (do before the hackathon)
Busy place (dining hall/library), person behind a curtain 1-1.5 m from the ESP32 link:
1. Empty vs person present: >= 9/10 correct.
2. Moving vs frozen: >= 9/10 correct.
3. No false eliminations for 30 s while still, with people walking 2-3 m away.
Fail -> switch core sensing to HLK-LD2410 radar (keep Wi-Fi as the research piece / comparison).

## Demo setup at the venue
- Ask organizers for an edge/corner table, ideally next to a real wall or doorway.
- Hiding spot: tablecloth over the table or cardboard boxes; person crouches/sits behind it.
- ESP32s low, 1-2 m apart, person inside the link line. Private ESP32-to-ESP32 link on a fixed channel.
- Recalibrate the empty zone before every player (show it as a visible "Scanning the room..." step).
- Record training data AT the venue spot, with crowd moving in the background. Tape down ESP32
  positions; any move means recalibrate/retrain.
- State machine with named states: EMPTY / MOVING / STILL_BREATHING / FALLEN. Change state only after
  3 consistent readings; keep last known state when a person goes quiet (Permanence-style object
  permanence, see notes below).
- Keep an offline local game screen as backup (Roblox needs internet). Bring a phone hotspot.
  Record a clean backup demo video as soon as the core works.

## Roblox integration details (verified against Roblox docs, Oct 2026)
- Roblox server script polls our laptop with HttpService (GetAsync/PostAsync) ~4x per second.
- Enable "Allow HTTP Requests" in Studio: File > Experience Settings > Security.
- HTTPS only, must be publicly reachable (Roblox servers can't reach localhost): use Cloudflare Tunnel or ngrok.
- Limit: ~500 HTTP requests/minute per game server. Expect ~0.2-0.5 s delay; add a short grace period after "red light".
- Open Cloud Messaging (push into game) is limited to ~120 messages/min per topic with 1 server and
  1 KB messages, so polling is better for live state.
- Send only game state to Roblox (moving/still/out). No names or biometric data (young audience).
- Docs: https://create.roblox.com/docs/en-us/cloud-services/http-service
        https://create.roblox.com/docs/en-us/cloud/guides/usage-messaging

## Architecture
```
ESP32 TX --Wi-Fi packets--> ESP32 RX --USB serial (CSI)--> Python on laptop
  Python: parse CSI -> clean/baseline -> features -> rules + ML models -> state machine -> game logic
  FastAPI: /state (polled by Roblox + local screens), /command (red light from Roblox)
  WebSocket -> local web screens: game, Wi-Fi vision, leaderboard, use-case dashboard
  Laptop --USB serial--> ESP32 for LEDs
  Cloudflare Tunnel -> public HTTPS for Roblox
Training only: webcam + YOLO pose (camera "teacher") auto-labels recorded CSI; camera off in the demo.
```

## ML plan (runs on the laptop CPU; no GPU/Jetson/cloud needed)
- There is no pretrained "YOLO for Wi-Fi": we record our own labelled CSI at the venue spot and train.
- Models: scikit-learn random forest / gradient boosting on window features first (trains in seconds);
  small 1D CNN in PyTorch only if needed (minutes on CPU, or Apple GPU via `device="mps"`).
- Tasks: (1) EMPTY / STILL / MOVING, (2) walk / sit down / lie down / fall, (3) breathing present,
  (4) stretch: people count 0-3.
- Labels: from `record.py` session labels, plus a webcam running YOLO pose (e.g. Ultralytics YOLO11n-pose)
  during collection as ground truth. Same idea as MIT RF-Pose (camera teaches the radio). Webcam is
  for training/evaluation only, which keeps the "no cameras" claim true for the product.
- Evaluate by holding out whole recording sessions (not random windows, which leak). Report confusion
  matrices and compare against the rule-based detector.

## Open-source code to build on (all verified to exist)
Wi-Fi CSI:
- https://github.com/espressif/esp-csi (official, start here)
- https://github.com/StevenMHernandez/ESP32-CSI-Tool (most used community tool)
- https://github.com/heyfinal/wifi-ghost (ESP32-WROOM through-wall presence, motion, breathing; closest to our setup)
- https://github.com/The-Masked-Bear/wifisense-pi (motion/breathing + live browser dashboard; ESP32-S3)
- https://github.com/jussi-modernpath/wisent (ESP32-S3 through-wall localization; documents failures)
- https://github.com/ruvnet/RuView (claims pose/vitals; unverified, previously accused of fake data; S3 boards)
- https://github.com/Marsrocky/Awesome-WiFi-CSI-Sensing (papers, datasets; cite in Devpost)
Camera heart rate: https://github.com/phuselab/pyVHR (simpler), https://github.com/ubicomplab/rPPG-Toolbox
Sensors/servos: SparkFun MAX3010x, SparkFun ENS160, Bosch BSEC2 (BME688), madhephaestus/ESP32Servo.
MQ gas sensors: 5 V heater, analog out needs a voltage divider before the ESP32 (3.3 V max); burn in
24-48 h before first use; show Normal/Warning/Danger, not fake ppm. Demo with hand sanitizer/isopropyl
on a swab; never real toxic gas or lighters.
Check licenses; credit everything used in README and Devpost.

## Research to cite
MIT Wi-Vi (2013), WiTrack (2014), Vital-Radio (2015), RF-Pose (2018); UW WiSee (2013);
CMU Person-in-WiFi (2019), DensePose from WiFi (2022); IEEE 802.11bf Wi-Fi sensing standard;
Espressif ESP-CSI; Wi-Fi fall-detection literature (see Awesome-WiFi-CSI-Sensing).
Note: the big results used special radios / multi-antenna routers, not ESP32s.

## Notes from reviewing past projects
- Permanence (github.com/billpquach/permanence) "memory" = tracking with rules, not AI memory:
  3D scan for a fixed world frame; YOLOE detections -> 3D via depth; Hungarian matching with distance
  gates; alpha-beta filter; when unseen, keep last position and label OUT_OF_VIEW / OCCLUDED / LOST;
  state changes need 3 frames agreeing; shell game rule: ball vanishes next to a resting cup -> INSIDE,
  rides with the cup. Borrow: keep state when a person goes quiet; 3-reading confirmation; named states.
  Permanence did not use Wi-Fi sensing, ESP32, or vitals.
- Farsight (github.com/azizu06/farsight): ~115k lines, but much was AI-agent generated (Devin),
  duplicated Python+Rust, ~35k tests. Size is not why it won.
- Our team's KYU-BOT (github.com/mbarbosa1/knightHacks): disaster triage agents + Databricks scorecard.
  Reuse map/dashboard experience for the Rescue/Guardian dashboard.
- A sign-language learning game ("Sign Hero") was done at a previous SwampHacks; avoid sign-language ideas.

## Build order
1. Before event: flash `sensing/firmware` to 2 ESP32s, `check_link.py`, `go_no_go.py`.
2. Motion detection + calibration at the venue; start recording labelled data immediately.
3. Red Light, Green Light page (offline backup) + speaker cue; Wi-Fi vision; Heist.
4. ML training script + first models; record backup demo video.
5. Roblox avatar moving/freezing, then Roblox players triggering red light.
6. Use-case dashboard (rescue, hot car, smart lights), fall detection.
7. Stretch items in priority order.



## Working style
Team prioritizes understanding the code, testing, and in-person communication. Prefer clear, readable
code with tests over volume. Explain non-obvious signal-processing steps in comments.
