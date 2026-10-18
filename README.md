# InterviewIQ 🎙️👁️
> **Real-Time Multimodal AI Mock Interviewer**
> Powered by FastAPI, WebSockets, Python OpenCV, Google MediaPipe, and Web Speech Intelligence.

---

## 1. Overview

**InterviewIQ** is an end-to-end, real-time interview coaching application built for Windows 11. It opens your webcam and microphone upon explicit permission, conducts a timed 60-second interview, analyzes observable facial framing, head orientation, and posture stability in real time, adapts its questions based on your responses, and generates an evidence-based performance report.

### Key Highlights
- **100% Zero Paid APIs & Offline-Ready**: Operates entirely locally. No OpenAI keys, no external cloud databases, and no monthly fees.
- **Real Computer Vision**: Real OpenCV and MediaPipe Tasks Vision process actual webcam frames streamed over WebSockets. No simulated metrics, no fake numbers, and no prerecorded video.
- **Authoritative 60-Second Clock**: The session timer is strictly governed on the server and synchronised with the browser.
- **Explainable 4-Category Rubric**: Transparent scoring with proportional dynamic re-weighting when hardware signals are unavailable. Missing data is never converted into a zero.
- **Ethical Coaching Focus**: Strictly evaluates observable communication behaviors (framing, pace, structure, word choice, posture stability). Does **not** attempt to detect deception, emotion, honesty, or internal psychological traits.

---

## 2. Architecture & Modular Layout

```
interviewIQ/
├── backend/
│   ├── config.py                 # Central configurations, model paths, duration (60s)
│   ├── main.py                   # FastAPI server, static mounts, WebSocket endpoint
│   ├── vision/
│   │   ├── frame_processor.py    # Base64 decoder, luminance, Laplacian blur variance
│   │   ├── face_analyzer.py      # FaceLandmarker (478 pts) / Haar cascade, tilt, framing
│   │   └── posture_analyzer.py   # PoseLandmarker (33 pts), shoulder tilt, upright check
│   ├── speech/
│   │   ├── speech_evaluator.py   # Speaking duration, WPM calculation, filler word regex
│   │   └── answer_relevance.py   # Heuristic scoring: STAR structure, examples, word depth
│   ├── interview/
│   │   ├── question_bank.py      # Deterministic local question banks across 4 categories
│   │   ├── adaptive_engine.py    # Adaptive probe triggers (short answers, missing action)
│   │   └── session_manager.py    # Authoritative session state machine & clock
│   ├── scoring/
│   │   ├── rubric.py             # 4-category rubric with proportional re-weighting
│   │   └── report_generator.py   # Evidence-backed report, 3 strengths, 3 improvements, plan
│   └── models/
│       ├── download_models.py    # One-click model downloader
│       ├── haarcascade_frontalface_default.xml
│       ├── haarcascade_eye.xml
│       ├── face_landmarker.task
│       └── pose_landmarker_lite.task
├── frontend/
│   ├── index.html                # Accessible semantic HTML5 interface
│   └── static/
│       ├── css/
│       │   ├── style.css         # Design system (Vanilla CSS, light & dark themes)
│       │   └── animations.css    # Countdown ring, radar pulse, micro-animations
│       └── js/
│           ├── websocket.js      # WebSocket client and event dispatcher
│           ├── camera.js         # getUserMedia, frame throttling, HUD canvas renderer
│           ├── speech.js         # Web Speech Recognition & SpeechSynthesis
│           ├── report.js         # Report dashboard renderer and JSON exporter
│           └── app.js            # Coordinator, state machine, theme toggle
├── tests/
│   ├── test_session_timer.py     # Authoritative 60-second timer tests
│   ├── test_adaptive_engine.py   # Question adaptation tests
│   ├── test_scoring_rubric.py    # Proportional weight normalization tests
│   ├── test_speech_evaluator.py  # WPM, fillers, and heuristic tests
│   ├── test_vision_metrics.py    # OpenCV luminance & Laplacian sharpness tests
│   └── test_e2e_websocket.py     # Full WebSocket client-server integration test
├── requirements.txt              # Pinned Python 3.14-compatible dependencies
├── run.ps1                       # Windows 11 PowerShell launch script
├── run.bat                       # Windows 11 Command Prompt batch script
└── README.md
```

---

## 3. Environment & Prerequisites

- **Operating System**: Windows 11 (or Windows 10)
- **Python**: Python 3.14 (or Python 3.11+) installed on the system.
- **Hardware**: Standard laptop webcam and microphone.
- **Browser**: Google Chrome, Microsoft Edge, or any Chromium-based browser supporting the Web Speech API and MediaDevices.

---

## 4. Quick Start (Windows 11)

### Option A: Using PowerShell (Recommended)
Open PowerShell in the project directory and run:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\run.ps1
```

### Option B: Using Command Prompt
Double-click `run.bat` or run:
```cmd
run.bat
```

### Option C: Manual Setup & Execution
If you prefer manual control:
```powershell
# 1. Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Ensure offline vision models are downloaded (already bundled)
python backend/models/download_models.py

# 4. Start the application server
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
Open your browser and navigate to: **`http://127.0.0.1:8000`**

---

## 5. Core User Flow

1. **Landing & Category Selection**:
   - Choose one of 4 interview tracks:
     - **General**: Career journey, key strengths, problem-solving.
     - **HR & Culture**: Collaboration, feedback, conflict resolution.
     - **Communication**: Simplifying complexity, executive persuasion, clarity.
     - **Technical Fundamentals**: System design, debugging, code quality.
2. **Permission Check**:
   - Clicking **Start 60s Interview** requests camera and microphone permissions.
3. **Live 60-Second Interview**:
   - The browser streams webcam frames to Python OpenCV over WebSockets at ~4 FPS.
   - Python computes real face framing, luminance, sharpness, head tilt, and shoulder posture.
   - Real-time HUD reticles and status badges are rendered directly over the live preview.
   - The interviewer asks questions via text and browser speech synthesis.
   - Your spoken answer is transcribed live; speaking pace (WPM) and filler words are calculated.
4. **Adaptive Questioning**:
   - If an answer is brief (< 15 words), the system asks for a concrete example.
   - If a challenge is described without personal action or result, it probes for what you did and the outcome.
   - When remaining time hits ≤ 15 seconds, it poses a graceful wrap-up question.
5. **Session Teardown & Report**:
   - Exactly at 60 seconds, the session concludes, the camera and microphone are released, and the comprehensive assessment report is displayed.
   - Download as a structured JSON file or print as a PDF.

---

## 6. Scoring Methodology

The assessment evaluates performance across **four explainable categories**:

| Category | Base Weight | Observation Criteria |
| :--- | :---: | :--- |
| **Answer Quality** | **35%** | Completeness, concrete example citations, STAR structure alignment (Situation, Action, Result), and relevance heuristics. |
| **Verbal Delivery** | **25%** | Speaking pace (optimal: 120–160 WPM), filler word rate per 100 words (`um`, `uh`, `like`, `you know`), and continuity. |
| **Camera Engagement** | **20%** | Face visibility percentage, framing centering stability, mean lighting luminance, and focus sharpness. |
| **Posture & Presence** | **20%** | MediaPipe shoulder levelness (tilt < 5°), upright torso posture, and absence of slouching. |

### Proportional Dynamic Re-weighting
If a signal cannot be reliably measured (e.g., microphone permission denied, webcam cropped tightly above shoulders, or speech recognition unavailable):
- The category is explicitly labeled **"Not measured"**.
- Missing categories are **never treated as zero**.
- Remaining measured categories are normalized proportionally so their weights sum to 100%:
  $$\text{Effective Weight}_i = \frac{\text{Base Weight}_i}{\sum_{j \in \text{Measured}} \text{Base Weight}_j} \times 100\%$$
- A **Data Coverage Indicator** displays the exact percentage of signals evaluated.

---

## 7. Real Computer Vision Processing

- **Luminance**: Calculated as the mean grayscale pixel intensity ($Y$). Frames $< 45$ lux are classified as *Low lighting*; frames $> 220$ lux are flagged as *Overexposed*.
- **Sharpness**: Measured via OpenCV Laplacian variance:
  $$\text{Sharpness} = \text{Var}(\nabla^2 I)$$
- **Face Framing**:
  - Primary: MediaPipe Tasks Vision FaceLandmarker (478 3D facial landmarks).
  - Fallback: OpenCV Haar Cascade frontal face detector (`haarcascade_frontalface_default.xml`).
  - Evaluates bounding box area ratio ($w \times h / W \times H$) and center deviation ($|\Delta x - 0.5|$).
- **Head Orientation**: Computes roll angle from eye corner vectors ($\text{atan2}(\Delta y, \Delta x)$) and pitch/yaw from relative 3D nose bridge coordinates.
- **Posture & Presence**: Analyzes MediaPipe PoseLandmarker (landmarks 11 and 12). Evaluates shoulder slope angle and vertical distance from nose to shoulder midpoint. If shoulders are outside the camera boundary, reports *"Posture unavailable"*.

---

## 8. Speech Analysis & Fallbacks

- **Speech Recognition**: Uses Chromium's `webkitSpeechRecognition` API.
- **Pacing**: Real-time Words Per Minute (WPM) computed from actual spoken word count divided by measured speaking duration.
- **Filler Words**: Regex matching with strict word boundaries for `um`, `uh`, `like`, `you know`, `actually`, `basically`, `i mean`, and `so yeah`.
- **Manual Input Fallback**: If browser speech recognition is blocked or unsupported, a visible input field appears immediately, allowing text answers so the session never breaks.

---

## 9. Running Tests

Execute the automated test suite using `pytest`:
```powershell
.\venv\Scripts\pytest.exe -v
```
**Test Suite Coverage (17 Tests)**:
- `test_session_timer.py`: Authoritative 60s countdown, monotonic decay, and session termination.
- `test_adaptive_engine.py`: Probing short answers, STAR gaps, and low-time wrap-ups.
- `test_scoring_rubric.py`: 4-category calculations, proportional re-weighting, and missing metric handling.
- `test_speech_evaluator.py`: WPM formulas, filler word extraction, and relevance heuristics.
- `test_vision_metrics.py`: OpenCV frame decoding, luminance, and Laplacian sharpness.
- `test_e2e_websocket.py`: End-to-end WebSocket handshake, frame streaming, and report generation.

---

## 10. Troubleshooting & FAQ

| Issue | Resolution |
| :--- | :--- |
| **Camera denied in browser** | Click the camera icon in your browser URL bar (e.g. Chrome/Edge) and change permission to **Allow**. Reload `http://127.0.0.1:8000`. |
| **Speech recognition not picking up audio** | Ensure your microphone is selected as default input in Windows Settings (`Settings > System > Sound`). Alternatively, type your response into the visible fallback input box. |
| **Posture marked "Not measured"** | MediaPipe requires your shoulders to be visible in the camera frame. Step back slightly from your webcam so your upper torso is in view. |
| **Python 3.14 wheel warning** | All dependencies (`numpy 2.5`, `opencv 5.0`, `mediapipe 1.1`, `fastapi 0.143`) have been verified and pre-installed in the isolated `venv`. Global Python is unaffected. |

---

## 11. Ethical Coaching Notice

InterviewIQ is an educational communication coaching tool. It does not measure intelligence, honesty, psychological traits, or personality. Observations reflect only measurable framing, pace, structure, and physical stability to help candidates refine their presentation.
