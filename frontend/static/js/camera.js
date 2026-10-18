/**
 * InterviewIQ Camera & Computer Vision HUD Controller.
 * Accesses real laptop webcam, throttles frame transmission,
 * and renders live visual landmarks and telemetry indicators on the overlay canvas.
 */
class CameraController {
  constructor(videoElement, canvasElement) {
    this.video = videoElement;
    this.canvas = canvasElement;
    this.ctx = canvasElement ? canvasElement.getContext('2d') : null;

    this.stream = null;
    this.captureCanvas = document.createElement('canvas');
    this.captureCtx = this.captureCanvas.getContext('2d');

    this.isStreaming = false;
    this.captureInterval = null;
    this.onFrameCallback = null;

    // Telemetry cache for smooth rendering
    this.lastTelemetry = null;
  }

  async start(onFrame) {
    this.onFrameCallback = onFrame;

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error('Your browser does not support webcam access via navigator.mediaDevices.getUserMedia.');
    }

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'user'
        },
        audio: false
      });

      this.video.srcObject = this.stream;

      // Handle video playback without blocking on potential play() delay
      try {
        const playPromise = this.video.play();
        if (playPromise !== undefined) {
          await playPromise;
        }
      } catch (playErr) {
        console.warn('Video play was not immediate, waiting for canplay event:', playErr);
      }

      this.isStreaming = true;

      // Initialize canvas dimensions once metadata is available
      const updateCanvasSize = () => {
        const w = this.video.videoWidth || 640;
        const h = this.video.videoHeight || 480;
        this.canvas.width = w;
        this.canvas.height = h;
        this.captureCanvas.width = w;
        this.captureCanvas.height = h;
      };

      if (this.video.videoWidth) {
        updateCanvasSize();
      } else {
        this.video.onloadedmetadata = updateCanvasSize;
      }

      // Throttle frame streaming to ~3.5 FPS (every 280ms)
      if (this.captureInterval) clearInterval(this.captureInterval);
      this.captureInterval = setInterval(() => {
        this.captureAndEmitFrame();
      }, 280);

      // Start continuous HUD render loop
      this.renderLoop();
      return true;
    } catch (err) {
      console.error('Camera start error:', err);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        throw new Error('Camera access was denied. Please allow camera permissions in your browser URL bar.');
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        throw new Error('No webcam hardware found. Please connect a camera and try again.');
      } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
        throw new Error('Webcam is currently in use by another application (e.g. Zoom, Teams, or another tab).');
      }
      throw err;
    }
  }

  captureAndEmitFrame() {
    if (!this.isStreaming || !this.video || this.video.readyState < 2) return;

    try {
      const w = this.captureCanvas.width || 640;
      const h = this.captureCanvas.height || 480;
      this.captureCtx.drawImage(this.video, 0, 0, w, h);
      // High-performance JPEG compression
      const base64Data = this.captureCanvas.toDataURL('image/jpeg', 0.65);

      if (this.onFrameCallback) {
        this.onFrameCallback(base64Data);
      }
    } catch (e) {
      console.warn('Frame capture error:', e);
    }
  }

  updateTelemetry(telemetry) {
    this.lastTelemetry = telemetry;
    this.updateHudBadges(telemetry);
  }

  renderLoop() {
    if (!this.isStreaming) return;

    this.drawHudOverlay();
    requestAnimationFrame(() => this.renderLoop());
  }

  drawHudOverlay() {
    if (!this.ctx || !this.canvas) return;

    const w = this.canvas.width;
    const h = this.canvas.height;
    this.ctx.clearRect(0, 0, w, h);

    if (!this.lastTelemetry) {
      this.drawSubtleFramingGuide(w, h);
      return;
    }

    const { face, posture } = this.lastTelemetry;

    // 1. Draw Face Bounding Box & Landmarks
    if (face && face.detected && face.bounding_box) {
      const bbox = face.bounding_box;
      const bx = bbox.x * w;
      const by = bbox.y * h;
      const bw = bbox.w * w;
      const bh = bbox.h * h;

      const isGoodFraming = face.framing_state === 'Good framing';
      const boxColor = isGoodFraming ? 'rgba(16, 185, 129, 0.85)' : 'rgba(245, 158, 11, 0.85)';

      this.drawCornerReticles(bx, by, bw, bh, boxColor);

      if (face.landmarks && face.landmarks.length > 0) {
        this.ctx.fillStyle = isGoodFraming ? 'rgba(34, 211, 238, 0.75)' : 'rgba(251, 191, 36, 0.75)';
        for (const pt of face.landmarks) {
          const px = pt.x * w;
          const py = pt.y * h;
          this.ctx.beginPath();
          this.ctx.arc(px, py, 2.2, 0, 2 * Math.PI);
          this.ctx.fill();
        }
      }
    } else {
      this.drawSubtleFramingGuide(w, h);
    }

    // 2. Draw Posture & Shoulder Alignment Line
    if (posture && posture.detected && posture.landmarks) {
      const ls = posture.landmarks.left_shoulder;
      const rs = posture.landmarks.right_shoulder;

      if (ls && rs) {
        const x1 = ls.x * w;
        const y1 = ls.y * h;
        const x2 = rs.x * w;
        const y2 = rs.y * h;

        const isUpright = posture.state === 'Upright';
        const postureColor = isUpright ? 'rgba(99, 102, 241, 0.8)' : 'rgba(245, 158, 11, 0.85)';

        this.ctx.strokeStyle = postureColor;
        this.ctx.lineWidth = 2.5;
        this.ctx.beginPath();
        this.ctx.moveTo(x1, y1);
        this.ctx.lineTo(x2, y2);
        this.ctx.stroke();

        this.ctx.fillStyle = postureColor;
        this.ctx.beginPath();
        this.ctx.arc(x1, y1, 5, 0, 2 * Math.PI);
        this.ctx.arc(x2, y2, 5, 0, 2 * Math.PI);
        this.ctx.fill();
      }
    }
  }

  drawCornerReticles(x, y, w, h, color) {
    const len = Math.min(22, w * 0.2);
    this.ctx.strokeStyle = color;
    this.ctx.lineWidth = 3;
    this.ctx.lineCap = 'round';

    this.ctx.beginPath();
    this.ctx.moveTo(x, y + len);
    this.ctx.lineTo(x, y);
    this.ctx.lineTo(x + len, y);
    this.ctx.stroke();

    this.ctx.beginPath();
    this.ctx.moveTo(x + w - len, y);
    this.ctx.lineTo(x + w, y);
    this.ctx.lineTo(x + w, y + len);
    this.ctx.stroke();

    this.ctx.beginPath();
    this.ctx.moveTo(x, y + h - len);
    this.ctx.lineTo(x, y + h);
    this.ctx.lineTo(x + len, y + h);
    this.ctx.stroke();

    this.ctx.beginPath();
    this.ctx.moveTo(x + w - len, y + h);
    this.ctx.lineTo(x + w, y + h);
    this.ctx.lineTo(x + w, y + h - len);
    this.ctx.stroke();
  }

  drawSubtleFramingGuide(w, h) {
    this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
    this.ctx.lineWidth = 1.5;
    this.ctx.setLineDash([6, 6]);
    this.ctx.beginPath();
    this.ctx.ellipse(w / 2, h * 0.45, w * 0.18, h * 0.28, 0, 0, 2 * Math.PI);
    this.ctx.stroke();
    this.ctx.setLineDash([]);
  }

  updateHudBadges(telemetry) {
    const facePill = document.getElementById('hud-face-pill');
    const lightPill = document.getElementById('hud-lighting-pill');
    const framingPill = document.getElementById('hud-framing-pill');
    const posturePill = document.getElementById('hud-posture-pill');

    if (!facePill || !lightPill || !framingPill || !posturePill) return;

    if (telemetry.face && telemetry.face.detected) {
      facePill.textContent = '✓ Face Detected';
      facePill.className = 'hud-pill good';
    } else {
      facePill.textContent = '⚠ Face Not Visible';
      facePill.className = 'hud-pill alert';
    }

    if (telemetry.quality) {
      const state = telemetry.quality.lighting_state;
      const lux = Math.round(telemetry.quality.luminance);
      if (state === 'Good lighting') {
        lightPill.textContent = `💡 Lighting (${lux})`;
        lightPill.className = 'hud-pill good';
      } else {
        lightPill.textContent = `🌙 ${state}`;
        lightPill.className = 'hud-pill warn';
      }
    }

    if (telemetry.face && telemetry.face.detected) {
      const state = telemetry.face.framing_state;
      framingPill.textContent = state;
      framingPill.className = state === 'Good framing' ? 'hud-pill good' : 'hud-pill warn';
    } else {
      framingPill.textContent = 'Center Face';
      framingPill.className = 'hud-pill alert';
    }

    if (telemetry.posture && telemetry.posture.detected) {
      const tilt = telemetry.posture.shoulder_tilt_deg;
      const tiltStr = tilt !== null ? `${Math.abs(tilt)}°` : '';
      if (telemetry.posture.state === 'Upright') {
        posturePill.textContent = `🧍 Upright (${tiltStr})`;
        posturePill.className = 'hud-pill good';
      } else {
        posturePill.textContent = `⚠️ ${telemetry.posture.state}`;
        posturePill.className = 'hud-pill warn';
      }
    } else {
      posturePill.textContent = 'Posture Unavailable';
      posturePill.className = 'hud-pill';
    }
  }

  stop() {
    this.isStreaming = false;
    if (this.captureInterval) {
      clearInterval(this.captureInterval);
      this.captureInterval = null;
    }
    if (this.stream) {
      this.stream.getTracks().forEach(track => {
        try { track.stop(); } catch (e) {}
      });
      this.stream = null;
    }
    if (this.video) {
      this.video.srcObject = null;
    }
    if (this.ctx && this.canvas) {
      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }
  }
}

window.CameraController = CameraController;
