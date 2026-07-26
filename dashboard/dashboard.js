// ============================================================================
// dashboard.js — SafeHire AI Dashboard Logic
// Handles: theme toggle, file upload, API calls, pipeline animation,
// result rendering, accordion, and timeline.
// ============================================================================

(function () {
  'use strict';

  // ---------------------------------------------------------------------------
  // API BASE URL — auto-detect backend port
  // ---------------------------------------------------------------------------
  const API_BASE = window.location.port === '5500'
    ? 'http://127.0.0.1:8000'
    : 'https://gemma4-ai-project-2026-azb0.onrender.com';

  // ---------------------------------------------------------------------------
  // DOM REFERENCES
  // ---------------------------------------------------------------------------
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const dom = {
    themeToggle: $('#themeToggle'),
    heroSection: $('#heroSection'),
    resultsSection: $('#resultsSection'),
    uploadCard: $('#uploadCard'),
    dropzone: $('#dropzone'),
    fileInput: $('#fileInput'),
    pasteTextBtn: $('#pasteTextBtn'),
    pasteArea: $('#pasteArea'),
    pasteInput: $('#pasteInput'),
    pasteCancelBtn: $('#pasteCancelBtn'),
    pasteAnalyzeBtn: $('#pasteAnalyzeBtn'),
    uploadPreview: $('#uploadPreview'),
    previewImg: $('#previewImg'),
    previewFileName: $('#previewFileName'),
    previewRemoveBtn: $('#previewRemoveBtn'),
    analyzeBtn: $('#analyzeBtn'),
    pipeline: $('#pipeline'),
    newAnalysisBtn: $('#newAnalysisBtn'),
  };

  // ---------------------------------------------------------------------------
  // 1. THEME TOGGLE
  // ---------------------------------------------------------------------------
  function initTheme() {
    const saved = localStorage.getItem('jv-theme');
    if (saved === 'light') document.body.classList.add('light');
  }

  function toggleTheme() {
    document.body.classList.toggle('light');
    localStorage.setItem('jv-theme', document.body.classList.contains('light') ? 'light' : 'dark');
  }

  dom.themeToggle.addEventListener('click', toggleTheme);
  initTheme();

  // ---------------------------------------------------------------------------
  // 2. FILE UPLOAD HANDLING
  // ---------------------------------------------------------------------------
  let selectedFile = null;

  // Drag & Drop
  dom.dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dom.dropzone.classList.add('drag-over');
  });
  dom.dropzone.addEventListener('dragleave', () => {
    dom.dropzone.classList.remove('drag-over');
  });
  dom.dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dom.dropzone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) handleFile(file);
  });

  // Click to browse
  dom.dropzone.addEventListener('click', (e) => {
    if (e.target.closest('.upload-paste-btn') || e.target.closest('.upload-browse-btn') || e.target.closest('label')) return;
    dom.fileInput.click();
  });
  dom.fileInput.addEventListener('change', (e) => {
    if (e.target.files[0]) handleFile(e.target.files[0]);
  });

  // Paste text
  dom.pasteTextBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    dom.dropzone.style.display = 'none';
    dom.pasteArea.style.display = 'block';
  });
  dom.pasteCancelBtn.addEventListener('click', () => {
    dom.pasteArea.style.display = 'none';
    dom.dropzone.style.display = 'flex';
    dom.pasteInput.value = '';
  });
  dom.pasteAnalyzeBtn.addEventListener('click', () => {
    const text = dom.pasteInput.value.trim();
    if (text) startAnalysis(null, text);
  });

  // Remove preview
  dom.previewRemoveBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    clearUpload();
  });

  // Analyze button
  dom.analyzeBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    if (selectedFile) startAnalysis(selectedFile, null);
  });

  // New analysis
  dom.newAnalysisBtn.addEventListener('click', resetToUpload);

  function handleFile(file) {
    selectedFile = file;
    dom.dropzone.style.display = 'none';
    dom.uploadPreview.style.display = 'flex';
    dom.previewFileName.textContent = file.name;
    const reader = new FileReader();
    reader.onload = (e) => { dom.previewImg.src = e.target.result; };
    reader.readAsDataURL(file);
  }

  function clearUpload() {
    selectedFile = null;
    dom.fileInput.value = '';
    dom.uploadPreview.style.display = 'none';
    dom.dropzone.style.display = 'flex';
    dom.previewImg.src = '';
  }

  function resetToUpload() {
    clearUpload();
    dom.pasteArea.style.display = 'none';
    dom.dropzone.style.display = 'flex';
    dom.pasteInput.value = '';
    dom.heroSection.style.display = 'flex';
    dom.resultsSection.style.display = 'none';
    dom.pipeline.style.display = 'none';
    $$('.pipeline-step').forEach(s => { s.classList.remove('active', 'complete', 'failed'); });
    $$('.timeline-item').forEach(t => { t.classList.remove('active', 'complete'); });
  }

  // ---------------------------------------------------------------------------
  // 3. PIPELINE STAGE HELPERS
  // ---------------------------------------------------------------------------
  const pipelineStages = ['uploading', 'ocr', 'entity', 'technical', 'content_analysis', 'reasoning', 'report'];

  function resetPipeline() {
    pipelineStages.forEach(stage => {
      const el = $(`.pipeline-step[data-step="${stage}"]`);
      if (!el) return;
      el.classList.remove('active', 'complete', 'failed');
      const label = el.querySelector('.step-label');
      if (label) {
        const activeText = label.getAttribute('data-active');
        if (activeText) label.textContent = activeText;
      }
    });
  }

  function setPipelineStage(stage, status) {
    const el = $(`.pipeline-step[data-step="${stage}"]`);
    if (!el) return;
    el.classList.remove('active', 'complete', 'failed');
    if (status === 'active') el.classList.add('active');
    else if (status === 'complete') el.classList.add('complete');
    else if (status === 'failed') el.classList.add('failed');

    const label = el.querySelector('.step-label');
    if (label) {
      const text = label.getAttribute(`data-${status}`);
      if (text) label.textContent = text;
    }
  }

  function markPreviousComplete(currentStage) {
    const idx = pipelineStages.indexOf(currentStage);
    for (let i = 0; i < idx; i++) {
      setPipelineStage(pipelineStages[i], 'complete');
    }
  }

  // ---------------------------------------------------------------------------
  // 4. ANALYSIS FLOW — SSE STREAMING
  // ---------------------------------------------------------------------------
  async function startAnalysis(file, text) {
    dom.dropzone.style.display = 'none';
    dom.uploadPreview.style.display = 'none';
    dom.pasteArea.style.display = 'none';
    dom.pipeline.style.display = 'block';
    resetPipeline();

    try {
      const formData = new FormData();
      if (file) formData.append('image', file);
      if (text) formData.append('text', text);

      const resp = await fetch(`${API_BASE}/api/analyze-stream`, { method: 'POST', body: formData });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let resultData = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        buffer = parts.pop();

        for (const part of parts) {
          if (!part.trim()) continue;
          let eventType = 'message';
          let eventData = '';

          for (const line of part.split('\n')) {
            if (line.startsWith('event: ')) eventType = line.slice(7).trim();
            else if (line.startsWith('data: ')) eventData += line.slice(6);
          }

          if (!eventData) continue;
          let parsed;
          try { parsed = JSON.parse(eventData); } catch { continue; }

          if (eventType === 'progress') {
            const { stage, status } = parsed;
            if (status === 'active') {
              markPreviousComplete(stage);
              setPipelineStage(stage, 'active');
            } else if (status === 'complete') {
              setPipelineStage(stage, 'complete');
            }
          } else if (eventType === 'error') {
            const stage = parsed.stage || 'unknown';
            markPreviousComplete(stage);
            setPipelineStage(stage, 'failed');
            const stepEl = $(`.pipeline-step[data-step="${stage}"] .step-label`);
            if (stepEl) stepEl.textContent = parsed.message || 'Failed';
            throw new Error(parsed.message || 'Pipeline failed');
          } else if (eventType === 'complete') {
            resultData = parsed;
          }
        }
      }

      if (!resultData) throw new Error('No result received from server');

      dom.heroSection.style.display = 'none';
      dom.resultsSection.style.display = 'block';
      renderResults(resultData);

    } catch (err) {
      console.error('Analysis error:', err);
      alert('Analysis failed: ' + err.message + '\n\nCheck the terminal for details.');
      dom.pipeline.style.display = 'none';
      dom.dropzone.style.display = 'flex';
    }
  }

  // ---------------------------------------------------------------------------
  // 5. RENDER RESULTS
  // ---------------------------------------------------------------------------
  function renderResults(data) {
    // Card 1: Verdict
    renderVerdict(data);

    // Card 2: Job Info
    renderJobInfo(data.job_info || {});

    // Card 3: AI Reasoning
    renderReasoning(data.ai_reasoning || {});

    // Card 4: Content Analysis
    renderContentAnalysis(data.content_analysis || {});

    // Card 5: Technical Investigation
    renderTechnical(data.technical || {});

    // Card 5: Risk Indicators
    renderRiskIndicators(data.risk_indicators || {});

    // Card 6: Evidence
    renderEvidence(data.technical_evidence || {});

    // Re-init Lucide icons for dynamically added elements
    if (window.lucide) lucide.createIcons();

    // Mark all timeline items complete
    markTimelineComplete();
  }

  function renderVerdict(data) {
    const badge = $('#verdictBadge');
    const verdict = (data.verdict || 'SAFE').toUpperCase();
    badge.textContent = verdict;
    badge.className = 'verdict-badge';
    if (verdict.includes('SCAM') || verdict.includes('HIGH')) badge.classList.add('scam');
    else if (verdict.includes('SUSPICIOUS') || verdict.includes('MEDIUM')) badge.classList.add('caution');
    else badge.classList.add('safe');

    $('#scoreNumber').textContent = data.risk_score ?? '--';
    $('#confidenceLevel').textContent = data.confidence || '--';
    $('#generatedTime').textContent = data.timestamp
      ? new Date(data.timestamp).toLocaleString()
      : new Date().toLocaleString();

    const breakdown = data.risk_breakdown || {};
    const components = [
      { key: 'technical_risk', bar: 'riskBarTechnical', val: 'riskValTechnical' },
      { key: 'content_risk', bar: 'riskBarContent', val: 'riskValContent' },
      { key: 'reasoning_risk', bar: 'riskBarReasoning', val: 'riskValReasoning' },
    ];
    components.forEach(({ key, bar, val }) => {
      const score = breakdown[key];
      const barEl = document.getElementById(bar);
      const valEl = document.getElementById(val);
      if (barEl && score != null) {
        barEl.style.width = score + '%';
        const level = score >= 70 ? 'high' : score >= 40 ? 'medium' : 'low';
        barEl.setAttribute('data-level', level);
      }
      if (valEl) valEl.textContent = score != null ? score + '/100' : '--';
    });
  }

  function renderJobInfo(info) {
    $('#infoCompany').textContent = info.company || '--';
    $('#infoTitle').textContent = info.title || info.job_title || '--';
    $('#infoLocation').textContent = info.location || '--';
    $('#infoSalary').textContent = info.salary || '--';
    $('#infoRecruiter').textContent = info.recruiter || '--';
    $('#infoEmail').textContent = info.email || '--';
    $('#infoPhone').textContent = info.phone || '--';
    $('#infoWebsite').textContent = info.website || '--';
    $('#infoSkills').textContent = info.skills || '--';
  }

  function renderReasoning(reasoning) {
    $('#reasoningScore').textContent = reasoning.risk_score != null ? `${reasoning.risk_score} / 100` : '--';
    $('#reasoningVerdict').textContent = reasoning.verdict || '--';

    const redList = $('#redFlagsList');
    const greenList = $('#greenFlagsList');

    redList.innerHTML = (reasoning.red_flags || []).map(f => `<li>${escHtml(f)}</li>`).join('');
    greenList.innerHTML = (reasoning.green_flags || []).map(f => `<li>${escHtml(f)}</li>`).join('');

    $('#explanationText').textContent = reasoning.explanation || '--';
  }

  function renderContentAnalysis(analysis) {
    const body = $('#contentAnalysisBody');
    if (!analysis || Object.keys(analysis).length === 0) {
      body.innerHTML = '<p style="color:var(--text-muted);font-size:13px;">No content analysis available.</p>';
      return;
    }

    const riskScore = analysis.content_risk_score;
    const riskLabel = riskScore != null ? (riskScore >= 70 ? 'High' : riskScore >= 40 ? 'Medium' : 'Low') : 'N/A';
    const riskCls = riskScore != null ? (riskScore >= 70 ? 'fail' : riskScore >= 40 ? 'warn' : 'pass') : 'warn';

    const checks = [
      { label: 'Salary Realistic', val: analysis.salary_realistic, invert: true },
      { label: 'Email Legitimate', val: analysis.email_legitimate, invert: true },
      { label: 'Grammar Quality', val: analysis.grammar_quality, type: 'quality' },
      { label: 'Urgency Pressure', val: analysis.urgency_pressure, invert: true },
      { label: 'Payment Request', val: analysis.payment_request, invert: true },
      { label: 'Interview Too Easy', val: analysis.interview_too_easy, invert: true },
      { label: 'Contact Quality', val: analysis.contact_quality, type: 'quality' },
      { label: 'Known Company', val: analysis.company_known },
      { label: 'Timeline Realistic', val: analysis.timeline_realistic },
    ];

    let html = `<div class="risk-score-row" style="margin-bottom:12px;">
      <span style="font-size:13px;color:var(--text-muted);">Content Risk Score</span>
      <span class="tech-status ${riskCls}" style="font-size:15px;font-weight:700;">${riskScore != null ? riskScore + '/100' : '--'} (${riskLabel})</span>
    </div>`;

    for (const c of checks) {
      let display, cls;
      if (c.type === 'quality') {
        const v = String(c.val || '').toLowerCase();
        display = v === 'good' || v === 'professional' ? '\u2713 ' + (c.val || 'N/A')
                : v === 'poor' || v === 'suspicious' ? '\u2717 ' + (c.val || 'N/A')
                : '? ' + (c.val || 'N/A');
        cls = v === 'good' || v === 'professional' ? 'pass' : v === 'poor' || v === 'suspicious' ? 'fail' : 'warn';
      } else {
        const isTrue = c.val === true;
        if (c.invert) {
          display = isTrue ? '\u2717 ' + c.label : '\u2713 ' + c.label;
          cls = isTrue ? 'fail' : 'pass';
        } else {
          display = isTrue ? '\u2713 ' + c.label : '\u2717 ' + c.label;
          cls = isTrue ? 'pass' : 'fail';
        }
      }
      html += `<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid var(--border-subtle);">
        <span style="font-size:13px;color:var(--text-secondary);">${escHtml(c.label)}</span>
        <span class="tech-status ${cls}" style="font-size:13px;">${display}</span>
      </div>`;
    }

    const redFlags = analysis.red_flags || [];
    const greenFlags = analysis.green_flags || [];
    if (redFlags.length > 0) {
      html += `<div style="margin-top:10px;"><span style="font-size:12px;font-weight:600;color:var(--accent-red);">RED FLAGS (${redFlags.length})</span><ul style="margin:4px 0 0 16px;font-size:12px;color:var(--text-secondary);">`;
      for (const f of redFlags) html += `<li>${escHtml(f)}</li>`;
      html += '</ul></div>';
    }
    if (greenFlags.length > 0) {
      html += `<div style="margin-top:8px;"><span style="font-size:12px;font-weight:600;color:var(--accent-green);">GREEN FLAGS (${greenFlags.length})</span><ul style="margin:4px 0 0 16px;font-size:12px;color:var(--text-secondary);">`;
      for (const f of greenFlags) html += `<li>${escHtml(f)}</li>`;
      html += '</ul></div>';
    }

    body.innerHTML = html;
  }

  function renderTechnical(tech) {
    const checks = {
      domain_registered: 'checkDomainRegistered',
      website_reachable: 'checkWebsiteReachable',
      https_enabled: 'checkHttpsEnabled',
      ssl_valid: 'checkSslValid',
      mx_record: 'checkMxRecord',
      spf_record: 'checkSpfRecord',
      dmarc_record: 'checkDmarcRecord',
      email_domain_match: 'checkEmailDomainMatch',
      disposable_email: 'checkDisposableEmail',
      free_email: 'checkFreeEmail',
      live_verification: 'checkLiveVerification',
      phone_valid: 'checkPhoneValid',
    };

    for (const [key, id] of Object.entries(checks)) {
      const el = document.getElementById(id);
      if (!el) continue;
      const val = tech[key];
      const display = formatCheckStatus(key, val);
      el.textContent = display.text;
      el.className = `tech-status ${display.cls}`;
    }
  }

  function formatCheckStatus(key, val) {
    const inverted = ['disposable_email', 'free_email'];

    if (val == null) return { text: 'N/A', cls: 'warn' };

    // Three-state system: "PASS", "FAIL", "UNKNOWN"
    const str = String(val).toUpperCase();
    if (str === 'PASS') {
      return inverted.includes(key)
        ? { text: '\u2717 Detected', cls: 'fail' }
        : { text: '\u2713 Pass', cls: 'pass' };
    }
    if (str === 'FAIL') {
      return inverted.includes(key)
        ? { text: '\u2713 Clean', cls: 'pass' }
        : { text: '\u2717 Failed', cls: 'fail' };
    }
    if (str === 'UNKNOWN') {
      return { text: '? Unknown', cls: 'warn' };
    }

    // Legacy boolean fallback
    const isTrue = val === true || val === 'true' || val === 1;
    if (inverted.includes(key)) {
      return isTrue
        ? { text: '\u2717 Detected', cls: 'fail' }
        : { text: '\u2713 Clean', cls: 'pass' };
    }
    return isTrue
      ? { text: '\u2713 Pass', cls: 'pass' }
      : { text: '\u2717 Failed', cls: 'fail' };
  }

  function renderRiskIndicators(indicators) {
    const container = $('#riskChips');
    if (!indicators || Object.keys(indicators).length === 0) {
      container.innerHTML = '<p style="color:var(--text-muted);font-size:13px;">No risk indicators available.</p>';
      return;
    }

    container.innerHTML = Object.entries(indicators).map(([key, val]) => {
      const label = formatChipLabel(key);
      const valStr = String(val);
      const isYes = valStr.toLowerCase() === 'yes' || valStr.toLowerCase() === 'true';
      const isNo = valStr.toLowerCase() === 'no' || valStr.toLowerCase() === 'false';
      const cls = isYes ? 'chip-fail' : isNo ? 'chip-pass' : 'chip-neutral';
      return `<div class="risk-chip ${cls}"><span class="chip-label">${escHtml(label)}</span> ${escHtml(valStr)}</div>`;
    }).join('');
  }

  function formatChipLabel(key) {
    return key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }

  function renderEvidence(ev) {
    const whois = ev.whois || {};
    const dns = ev.dns || {};
    const tls = ev.tls || {};
    const emailVal = ev.email_validation || {};
    const phoneIntel = ev.phone_intelligence || {};

    function evidenceStatusClass(status) {
      if (status === 'PASS') return 'pass';
      if (status === 'FAIL') return 'fail';
      if (status === 'UNKNOWN') return 'warn';
      return 'warn';
    }

    function setEl(id, val) {
      const el = document.getElementById(id);
      if (el) el.textContent = val ?? '--';
    }

    function setStatus(id, status) {
      const el = document.getElementById(id);
      if (el) {
        el.textContent = status || 'UNKNOWN';
        el.className = 'tech-status ' + evidenceStatusClass(status);
      }
    }

    function boolText(val) {
      if (val === true || val === 'true' || val === 'TRUE') return 'Yes';
      if (val === false || val === 'false' || val === 'FALSE') return 'No';
      return '--';
    }

    setEl('whoisCreated', whois.created);
    setEl('whoisExpiry', whois.expires);
    setEl('whoisRegistrar', whois.registrar);
    setStatus('whoisStatus', whois.status);

    const aRecords = Array.isArray(dns.a) ? dns.a : [];
    const mxRecords = Array.isArray(dns.mx) ? dns.mx : [];
    const txtRecords = Array.isArray(dns.txt) ? dns.txt : [];
    setEl('dnsA', aRecords.length > 0 ? aRecords.join(', ') : null);
    setEl('dnsMx', mxRecords.length > 0 ? mxRecords.join(', ') : null);
    setEl('dnsTxt', txtRecords.length > 0 ? txtRecords.join(', ') : null);
    setStatus('dnsStatus', dns.status);

    setEl('tlsVersion', tls.version);
    setEl('tlsIssuer', tls.issuer);
    setStatus('tlsStatus', tls.status);

    setEl('httpStatus', ev.http_status);

    setEl('emailDeliverability', emailVal.deliverability);
    setEl('emailQualityScore', emailVal.quality_score);
    setEl('emailSmtpValid', boolText(emailVal.is_smtp_valid));
    setEl('emailMxFound', boolText(emailVal.is_mx_found));
    setEl('emailDisposable', boolText(emailVal.is_disposable));
    setEl('emailFree', boolText(emailVal.is_free_email));
    setEl('emailRole', boolText(emailVal.is_role_email));
    setEl('emailCatchall', boolText(emailVal.is_catchall));
    setEl('emailAutocorrect', emailVal.autocorrect || '--');
    setStatus('emailValidStatus', emailVal.status);

    setEl('phoneValid', boolText(phoneIntel.is_valid));
    setEl('phoneLineType', phoneIntel.line_type);
    setEl('phoneLineStatus', phoneIntel.line_status);
    setEl('phoneCarrier', phoneIntel.carrier);
    setEl('phoneCountry', phoneIntel.country);
    setEl('phoneRiskLevel', phoneIntel.risk_level);
    setEl('phoneBreaches', phoneIntel.total_breaches != null ? String(phoneIntel.total_breaches) : '--');
    setStatus('phoneIntelStatus', phoneIntel.status);
  }

  // ---------------------------------------------------------------------------
  // 6. TIMELINE — mark all complete when results render
  // ---------------------------------------------------------------------------
  function markTimelineComplete() {
    $$('.timeline-item').forEach(t => { t.classList.add('complete'); });
  }

  // ---------------------------------------------------------------------------
  // 7. ACCORDION
  // ---------------------------------------------------------------------------
  document.addEventListener('click', (e) => {
    const trigger = e.target.closest('.accordion-trigger');
    if (!trigger) return;
    const item = trigger.closest('.accordion-item');
    if (!item) return;
    item.classList.toggle('open');
  });

  // ---------------------------------------------------------------------------
  // UTILITIES
  // ---------------------------------------------------------------------------
  function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  function escHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // ---------------------------------------------------------------------------
  // 8. DEMO DATA (shown when API is unavailable)
  // ---------------------------------------------------------------------------
  function getDemoData() {
    return {
      verdict: 'SAFE',
      risk_score: 18,
      risk_breakdown: {
        technical_risk: 5,
        content_risk: 15,
        reasoning_risk: 28,
      },
      confidence: 'High',
      timestamp: new Date().toISOString(),
      job_info: {
        company: 'Google',
        title: 'Senior Software Engineer',
        location: 'Mountain View, CA (Hybrid)',
        salary: '$145,000 - $185,000/year',
        recruiter: 'Sarah Chen',
        email: 'sarah.chen@google.com',
        phone: '+1 (650) 253-0000',
        website: 'https://careers.google.com',
        skills: 'Python, Go, Distributed Systems, Cloud Infrastructure',
      },
      ai_reasoning: {
        risk_score: 18,
        verdict: 'SAFE',
        red_flags: [],
        green_flags: [
          'Company domain matches official Google domain',
          'Recruiter email uses verified corporate domain',
          'HTTPS enabled with valid SSL certificate',
          'Domain registered since 1997 (well-established)',
          'SPF, DMARC, and MX records all properly configured',
          'Salary range is consistent with market rates for this role',
        ],
        explanation: 'This job posting appears to be legitimate. The posting originates from Google\'s official careers domain, and the recruiter\'s email address is consistent with Google\'s corporate email infrastructure. The domain has been registered since 1997 with a reputable registrar. All email authentication records (SPF, DMARC, MX) are properly configured, and the website uses a valid SSL certificate. The salary range is competitive but within normal bounds for senior engineering roles at major tech companies. No red flags were detected during technical investigation.',
      },
      technical: {
        domain_registered: true,
        website_reachable: true,
        https_enabled: true,
        ssl_valid: true,
        mx_record: true,
        spf_record: true,
        dmarc_record: true,
        email_domain_match: true,
        disposable_email: false,
        free_email: false,
        live_verification: true,
        phone_valid: true,
      },
      risk_indicators: {
        domain_registered: 'Pass',
        https_enabled: 'Pass',
        ssl_valid: 'Pass',
        mx_record: 'Pass',
        spf_record: 'Pass',
        dmarc_record: 'Pass',
        email_domain_match: 'Pass',
        phone_valid: 'Pass',
        disposable_email: 'No',
        free_email: 'No',
        suspicious_salary: 'No',
        domain_age: '27+ years',
        domain_source: 'website',
        checks_pass: 12,
        checks_fail: 0,
        checks_unknown: 0,
      },
      technical_evidence: {
        whois: {
          created: '1997-09-15',
          expires: '2025-09-14',
          registrar: 'MarkMonitor Inc.',
        },
        dns: {
          a: ['142.250.80.46', '142.250.80.78'],
          mx: ['alt1.aspmx.l.google.com', 'aspmx.l.google.com'],
          txt: ['v=spf1 include:_spf.google.com ~all', 'google-site-verification=...'],
        },
        tls: {
          version: 'TLS 1.3',
          issuer: 'GTS CA 1C3 (Google Trust Services)',
        },
        http_status: 200,
      },
    };
  }

  // ---------------------------------------------------------------------------
  // 9. INIT
  // ---------------------------------------------------------------------------
  if (window.lucide) lucide.createIcons();

})();
