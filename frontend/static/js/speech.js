/**
 * InterviewIQ Speech Controller.
 * Manages browser SpeechRecognition (with visible fallback)
 * and SpeechSynthesis for spoken interviewer questions.
 */
class SpeechController {
  constructor(options = {}) {
    this.onTranscriptUpdate = options.onTranscriptUpdate || null;
    this.onStatusChange = options.onStatusChange || null;

    this.recognition = null;
    this.isRecognizing = false;
    this.isSynthesisSpeaking = false;
    this.isSupported = false;

    this.currentInterimText = '';
    this.currentFinalText = '';

    this.initRecognition();
  }

  initRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      try {
        this.recognition = new SpeechRecognition();
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';

        this.recognition.onresult = (event) => {
          let interim = '';
          for (let i = event.resultIndex; i < event.results.length; ++i) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              this.currentFinalText += (this.currentFinalText ? ' ' : '') + transcript.trim();
            } else {
              interim += transcript;
            }
          }
          this.currentInterimText = interim;
          const fullText = (this.currentFinalText + ' ' + this.currentInterimText).trim();

          if (this.onTranscriptUpdate) {
            this.onTranscriptUpdate(fullText, false);
          }
        };

        this.recognition.onerror = (event) => {
          console.warn('SpeechRecognition error:', event.error);
          if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
            this.showFallbackInput('Microphone permission blocked. You can type answers below.');
          }
        };

        this.recognition.onend = () => {
          // Auto restart if still supposed to be recognizing
          if (this.isRecognizing) {
            try {
              this.recognition.start();
            } catch (e) {}
          }
        };

        this.isSupported = true;
      } catch (err) {
        console.warn('SpeechRecognition failed initialization:', err);
        this.isSupported = false;
      }
    } else {
      this.isSupported = false;
      this.showFallbackInput('Browser speech recognition unavailable. Manual input activated.');
    }
  }

  startListening() {
    this.currentInterimText = '';
    this.currentFinalText = '';

    if (this.isSupported && this.recognition) {
      try {
        this.isRecognizing = true;
        this.recognition.start();
        if (this.onStatusChange) this.onStatusChange('listening');
      } catch (e) {
        console.warn('Recognition start exception:', e);
      }
    } else {
      this.showFallbackInput('Manual text input enabled.');
    }
  }

  stopListening() {
    this.isRecognizing = false;
    if (this.recognition) {
      try {
        this.recognition.stop();
      } catch (e) {}
    }
  }

  resetCurrentAnswer() {
    this.currentInterimText = '';
    this.currentFinalText = '';
  }

  speakQuestion(text, onComplete) {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel(); // Stop any pending speech

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'en-US';
      utterance.rate = 1.0;
      utterance.pitch = 1.0;

      // Select an English voice if available
      const voices = window.speechSynthesis.getVoices();
      const preferred = voices.find(v => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Samantha')));
      if (preferred) utterance.voice = preferred;

      utterance.onstart = () => {
        this.isSynthesisSpeaking = true;
        if (this.onStatusChange) this.onStatusChange('speaking');
      };

      utterance.onend = () => {
        this.isSynthesisSpeaking = false;
        if (this.onStatusChange) this.onStatusChange('listening');
        if (onComplete) onComplete();
      };

      utterance.onerror = () => {
        this.isSynthesisSpeaking = false;
        if (this.onStatusChange) this.onStatusChange('listening');
        if (onComplete) onComplete();
      };

      window.speechSynthesis.speak(utterance);
    } else {
      if (onComplete) onComplete();
    }
  }

  showFallbackInput(reason) {
    const fallbackContainer = document.getElementById('manual-answer-container');
    if (fallbackContainer) {
      fallbackContainer.style.display = 'flex';
      const placeholder = document.getElementById('manual-answer-input');
      if (placeholder && reason) placeholder.placeholder = reason;
    }
  }

  stopAll() {
    this.stopListening();
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
  }
}

window.SpeechController = SpeechController;
