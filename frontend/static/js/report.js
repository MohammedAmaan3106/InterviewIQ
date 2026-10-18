/**
 * InterviewIQ Assessment Report Renderer.
 * Formats evidence-backed assessment telemetry into a modern coaching view.
 */
class ReportRenderer {
  constructor() {
    this.currentReport = null;
  }

  render(report) {
    this.currentReport = report;

    // 1. Overall Score & Tier
    const scoreVal = report.overall_assessment.score;
    const scoreNumEl = document.getElementById('report-score-num');
    const tierEl = document.getElementById('report-tier-title');
    const summaryEl = document.getElementById('report-summary-text');
    const coverageEl = document.getElementById('report-coverage-badge');

    if (scoreNumEl) {
      scoreNumEl.textContent = scoreVal !== null ? Math.round(scoreVal) : '--';
    }
    if (tierEl) {
      tierEl.textContent = report.overall_assessment.tier;
    }
    if (summaryEl) {
      summaryEl.textContent = report.overall_assessment.summary;
    }
    if (coverageEl) {
      coverageEl.textContent = `📊 Data Coverage: ${report.overall_assessment.coverage_percentage}% (${report.overall_assessment.coverage_explanation})`;
    }

    // 2. Category Score Cards
    this.renderCategoryCards(report.categories);

    // 3. Observed Strengths
    this.renderInsights('report-strengths-list', report.strengths, false);

    // 4. Actionable Improvements
    this.renderInsights('report-improvements-list', report.improvements, true);

    // 5. Diagnostics Grid
    this.renderDiagnostics(report.diagnostics);

    // 6. Practice Plan
    this.renderPracticePlan(report.practice_plan);

    // 7. Q&A History
    this.renderHistory(report.transcript_history);
  }

  renderCategoryCards(categories) {
    const container = document.getElementById('report-categories-container');
    if (!container) return;

    container.innerHTML = '';
    const keys = ['answer_quality', 'verbal_delivery', 'camera_engagement', 'posture_presence'];

    for (const key of keys) {
      const cat = categories[key];
      if (!cat) continue;

      const card = document.createElement('div');
      card.className = 'category-score-card';

      const isMeasured = cat.measured;
      const scoreDisp = isMeasured ? `${Math.round(cat.score)}` : 'Not measured';
      const pct = isMeasured ? Math.min(100, Math.max(0, cat.score)) : 0;
      const weightDisp = `${cat.effective_weight}% weight`;

      const obsList = (cat.observations || []).map(o => `<li>${o}</li>`).join('');

      card.innerHTML = `
        <div class="cat-header">
          <span class="cat-name">${cat.name}</span>
          <span class="cat-weight-pill">${weightDisp}</span>
        </div>
        <div class="cat-score-bar-bg">
          <div class="cat-score-bar-fill" style="width: ${pct}%"></div>
        </div>
        <div class="cat-score-num">${scoreDisp}</div>
        <ul class="cat-obs" style="padding-left: 18px;">
          ${obsList}
        </ul>
      `;
      container.appendChild(card);
    }
  }

  renderInsights(containerId, items, isImprovement) {
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = '';
    for (const item of items) {
      const el = document.createElement('div');
      el.className = `insight-item ${isImprovement ? 'improvement' : ''}`;
      el.innerHTML = `
        <h5>${item.title}</h5>
        <p>${item.evidence}</p>
      `;
      container.appendChild(el);
    }
  }

  renderDiagnostics(diag) {
    const speechEl = document.getElementById('diag-speech-summary');
    const visionEl = document.getElementById('diag-vision-summary');

    if (speechEl && diag.speech) {
      const sp = diag.speech;
      const wpmStr = sp.wpm !== null ? `${sp.wpm} WPM` : 'N/A';
      const fillersStr = sp.filler_count > 0 ? `${sp.filler_count} detected` : 'None detected';
      speechEl.innerHTML = `
        <div><strong>Words Spoken:</strong> ${sp.total_words} words (${sp.speaking_seconds}s)</div>
        <div><strong>Pacing:</strong> ${wpmStr} (${sp.pace_label})</div>
        <div><strong>Filler Words:</strong> ${fillersStr}</div>
      `;
    }

    if (visionEl && diag.vision) {
      const vs = diag.vision;
      const postureStr = vs.posture_measured ? `Upright ${vs.upright_posture_pct}% (tilt: ${vs.average_shoulder_tilt_deg}°)` : 'Not measured';
      visionEl.innerHTML = `
        <div><strong>Frames Processed:</strong> ${vs.frames_processed} frames</div>
        <div><strong>Face Visibility:</strong> ${vs.face_visibility_pct}% (stability: ${vs.average_framing_score || 'N/A'})</div>
        <div><strong>Posture Alignment:</strong> ${postureStr}</div>
      `;
    }
  }

  renderPracticePlan(steps) {
    const container = document.getElementById('report-plan-container');
    if (!container) return;

    container.innerHTML = '';
    for (const step of steps) {
      const box = document.createElement('div');
      box.className = 'plan-step-box';
      box.innerHTML = `
        <span class="step-num">Step ${step.step}</span>
        <h5 class="step-title">${step.title}</h5>
        <p class="step-action">${step.action}</p>
      `;
      container.appendChild(box);
    }
  }

  renderHistory(history) {
    const container = document.getElementById('report-history-container');
    if (!container) return;

    container.innerHTML = '';
    if (!history || history.length === 0) {
      container.innerHTML = '<p class="text-tertiary">No questions recorded.</p>';
      return;
    }

    history.forEach((item, idx) => {
      const row = document.createElement('div');
      row.className = 'qna-accordion-item';
      const ans = item.transcript ? item.transcript : '<em>(No spoken answer captured)</em>';
      const wpmStr = item.wpm ? ` • ${item.wpm} WPM` : '';
      const durStr = `${item.speaking_duration_seconds}s`;

      row.innerHTML = `
        <div class="qna-q-title">Q${idx + 1}: ${item.question_text}</div>
        <div class="qna-ans-text">"${ans}"</div>
        <div class="qna-meta-row">
          <span>Duration: ${durStr}${wpmStr}</span>
          <span>Words: ${item.word_count}</span>
          <span>Fillers: ${item.fillers_count}</span>
        </div>
      `;
      container.appendChild(row);
    });
  }

  downloadJson() {
    if (!this.currentReport) return;

    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(this.currentReport, null, 2));
    const dlAnchor = document.createElement('a');
    const sessionId = this.currentReport.metadata.session_id || 'interviewiq';
    dlAnchor.setAttribute('href', dataStr);
    dlAnchor.setAttribute('download', `InterviewIQ_Report_${sessionId}.json`);
    document.body.appendChild(dlAnchor);
    dlAnchor.click();
    dlAnchor.remove();
  }
}

window.ReportRenderer = ReportRenderer;
