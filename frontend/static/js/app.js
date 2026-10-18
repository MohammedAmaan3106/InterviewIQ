/**
 * InterviewIQ Main Application Coordinator.
 * Manages screen transitions, authoritative timer synchronization,
 * user interactions, and clean hardware teardown.
 */
document.addEventListener('DOMContentLoaded', () => {
  // Screen Elements
  const landingScreen = document.getElementById('landing-screen');
  const workspaceScreen = document.getElementById('workspace-screen');
  const reportScreen = document.getElementById('report-screen');

  // Interactive UI Elements
  const startBtn = document.getElementById('btn-start-interview');
  const endEarlyBtn = document.getElementById('btn-end-interview');
  const nextQuestionBtn = document.getElementById('btn-next-question');
  const replayVoiceBtn = document.getElementById('btn-replay-voice');
  const restartBtn = document.getElementById('btn-restart');
  const downloadReportBtn = document.getElementById('btn-download-json');
  const printReportBtn = document.getElementById('btn-print-report');
  const themeToggleBtn = document.getElementById('btn-theme-toggle');

  // Question & Transcript Elements
  const questionTextEl = document.getElementById('current-question-text');
  const transcriptContentEl = document.getElementById('transcript-content');
  const manualInputEl = document.getElementById('manual-answer-input');
  const manualSubmitBtn = document.getElementById('btn-submit-manual');

  // Status & Timer Elements
  const connectionPill = document.getElementById('status-connection-pill');
  const timerDigitsEl = document.getElementById('countdown-digits');
  const timerCircleProgress = document.getElementById('timer-circle-progress');
  const timerCard = document.getElementById('countdown-card');
  const sessionStatusPill = document.getElementById('status-session-pill');
  const categoryLabelEl = document.getElementById('session-category-label');

  // Live Metric Pills
  const liveWpmEl = document.getElementById('live-metric-wpm');
  const liveFillersEl = document.getElementById('live-metric-fillers');
  const liveFramingEl = document.getElementById('live-metric-framing');

  // Categories
  let selectedCategory = 'General';
  const categoryCards = document.querySelectorAll('.category-card');
  categoryCards.forEach(card => {
    card.addEventListener('click', () => {
      categoryCards.forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      selectedCategory = card.getAttribute('data-category') || 'General';
      if (categoryLabelEl) categoryLabelEl.textContent = selectedCategory;
    });
  });

  // Theme Management
  const savedTheme = localStorage.getItem('interviewiq_theme');
  if (savedTheme === 'dark') {
    document.documentElement.classList.add('dark-theme');
  }
  themeToggleBtn.addEventListener('click', () => {
    document.documentElement.classList.toggle('dark-theme');
    const isDark = document.documentElement.classList.contains('dark-theme');
    localStorage.setItem('interviewiq_theme', isDark ? 'dark' : 'light');
  });

  // Subsystem Controllers
  const ws = new InterviewWebSocket();
  const camera = new CameraController(
    document.getElementById('webcam-video'),
    document.getElementById('overlay-canvas')
  );
  const speech = new SpeechController({
    onTranscriptUpdate: (text, isFinal) => {
      if (transcriptContentEl) {
        transcriptContentEl.textContent = text || 'Listening to your response...';
      }
      ws.send('transcript_update', { text, is_final: isFinal });
      updateLiveSpeechPills(text);
    },
    onStatusChange: (status) => {
      updateInterviewerState(status);
    }
  });
  const reportRenderer = new ReportRenderer();

  // Authoritative Timer Constants
  const TOTAL_DURATION = 60;
  const CIRCLE_CIRCUMFERENCE = 2 * Math.PI * 22; // radius 22
  if (timerCircleProgress) {
    timerCircleProgress.style.strokeDasharray = `${CIRCLE_CIRCUMFERENCE}`;
    timerCircleProgress.style.strokeDashoffset = '0';
  }

  let currentQuestionText = '';

  // ==========================================================================
  // Navigation & Screen Switches
  // ==========================================================================

  function showScreen(screenId) {
    landingScreen.classList.remove('active');
    workspaceScreen.classList.remove('active');
    reportScreen.classList.remove('active');

    if (screenId === 'landing') landingScreen.classList.add('active');
    if (screenId === 'workspace') workspaceScreen.classList.add('active');
    if (screenId === 'report') reportScreen.classList.add('active');
  }

  function resetStartButton() {
    startBtn.disabled = false;
    startBtn.innerHTML = `
      <span>Start 60s Interview</span>
      <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3"/>
      </svg>
    `;
  }

  // ==========================================================================
  // Start Interview Flow
  // ==========================================================================

  startBtn.addEventListener('click', async () => {
    startBtn.disabled = true;
    startBtn.textContent = 'Connecting to Server...';

    try {
      // 1. Establish WebSocket connection
      await ws.connect(6000);

      // 2. Request and start live webcam video stream
      startBtn.textContent = 'Awaiting Camera Permission...';
      // Switch screen so video has active layout geometry
      showScreen('workspace');
      if (categoryLabelEl) categoryLabelEl.textContent = selectedCategory;

      await camera.start((base64Frame) => {
        ws.send('video_frame', { frame: base64Frame });
      });

      // 3. Send start_session message to backend
      ws.send('start_session', { category: selectedCategory });

    } catch (err) {
      console.error('Failed to start interview session:', err);
      showScreen('landing');
      resetStartButton();
      alert(`Could not start interview:\n${err.message || err}`);
      camera.stop();
      speech.stopAll();
      ws.disconnect();
    }
  });

  // ==========================================================================
  // WebSocket Event Handlers
  // ==========================================================================

  ws.on('connected', () => {
    if (connectionPill) {
      connectionPill.className = 'status-pill connected';
      connectionPill.querySelector('.status-text').textContent = 'Connected';
    }
  });

  ws.on('session_started', (data) => {
    if (sessionStatusPill) {
      sessionStatusPill.style.display = 'inline-flex';
      sessionStatusPill.className = 'status-pill listening';
      sessionStatusPill.querySelector('.status-text').textContent = 'In Progress';
    }
    const q = data.question;
    setNewQuestion(q.text);
  });

  ws.on('timer_tick', (data) => {
    const rem = data.time_remaining_seconds;
    updateAuthoritativeTimer(rem);
  });

  ws.on('vision_telemetry', (telemetry) => {
    camera.updateTelemetry(telemetry);
    updateLiveVisionPills(telemetry);
  });

  ws.on('question_advanced', (data) => {
    speech.resetCurrentAnswer();
    if (transcriptContentEl) {
      transcriptContentEl.innerHTML = '<span class="transcript-placeholder">Listening for your answer...</span>';
    }
    const nextQ = data.next_question;
    if (nextQ && nextQ.text) {
      setNewQuestion(nextQ.text);
    }
  });

  ws.on('session_completed', (finalReport) => {
    teardownActiveSession();
    showScreen('report');
    reportRenderer.render(finalReport);
  });

  // ==========================================================================
  // Question Transitions & Interactions
  // ==========================================================================

  function setNewQuestion(text) {
    currentQuestionText = text;
    if (questionTextEl) {
      questionTextEl.textContent = text;
    }
    // Speak question aloud using browser speech synthesis
    speech.speakQuestion(text, () => {
      // Start listening for candidate's spoken response
      speech.startListening();
    });
  }

  nextQuestionBtn.addEventListener('click', () => {
    speech.stopListening();
    ws.send('advance_question', {});
  });

  replayVoiceBtn.addEventListener('click', () => {
    if (currentQuestionText) {
      speech.speakQuestion(currentQuestionText);
    }
  });

  manualSubmitBtn.addEventListener('click', () => {
    const text = (manualInputEl.value || '').trim();
    if (text) {
      ws.send('advance_question', { manual_transcript: text });
      manualInputEl.value = '';
    }
  });

  endEarlyBtn.addEventListener('click', () => {
    if (confirm('Are you sure you want to end the interview early?')) {
      ws.send('stop_session', {});
    }
  });

  // ==========================================================================
  // Timer & Status Updates
  // ==========================================================================

  function updateAuthoritativeTimer(secondsRemaining) {
    const sec = Math.max(0, Math.ceil(secondsRemaining));
    const mins = Math.floor(sec / 60);
    const remainderSec = sec % 60;
    const timeFormatted = `0${mins}:${remainderSec < 10 ? '0' : ''}${remainderSec}`;

    if (timerDigitsEl) {
      timerDigitsEl.textContent = timeFormatted;
    }

    // Circular progress stroke calculation
    if (timerCircleProgress) {
      const progressRatio = Math.max(0, secondsRemaining) / TOTAL_DURATION;
      const offset = CIRCLE_CIRCUMFERENCE * (1 - progressRatio);
      timerCircleProgress.style.strokeDashoffset = `${offset}`;
    }

    // Urgency pulse below 15s
    if (secondsRemaining <= 15.0) {
      if (timerCard && !timerCard.classList.contains('urgent')) {
        timerCard.classList.add('urgent');
      }
    } else {
      if (timerCard) timerCard.classList.remove('urgent');
    }
  }

  function updateInterviewerState(status) {
    const avatar = document.getElementById('interviewer-state-indicator');
    if (!avatar) return;

    if (status === 'speaking') {
      avatar.textContent = '🗣️';
      avatar.title = 'Interviewer is speaking question';
    } else if (status === 'listening') {
      avatar.textContent = '🎙️';
      avatar.title = 'Interviewer is listening to you';
    }
  }

  function updateLiveSpeechPills(text) {
    if (!text) return;
    const words = text.trim().split(/\s+/).filter(w => w.length > 0);
    const count = words.length;

    // Detect basic fillers
    const fillers = (text.match(/\b(um|uh|like|you know|actually|basically)\b/gi) || []).length;
    if (liveFillersEl) {
      liveFillersEl.textContent = `${fillers} detected`;
    }
  }

  function updateLiveVisionPills(telemetry) {
    if (telemetry.face && liveFramingEl) {
      const score = telemetry.face.framing_score;
      liveFramingEl.textContent = score !== null ? `${Math.round(score)}%` : '--';
    }
  }

  // ==========================================================================
  // Teardown & Reporting
  // ==========================================================================

  function teardownActiveSession() {
    camera.stop();
    speech.stopAll();
    ws.disconnect();

    if (sessionStatusPill) {
      sessionStatusPill.className = 'status-pill';
      sessionStatusPill.querySelector('.status-text').textContent = 'Completed';
    }
  }

  restartBtn.addEventListener('click', () => {
    teardownActiveSession();
    resetStartButton();
    showScreen('landing');
  });

  downloadReportBtn.addEventListener('click', () => {
    reportRenderer.downloadJson();
  });

  printReportBtn.addEventListener('click', () => {
    window.print();
  });
});
