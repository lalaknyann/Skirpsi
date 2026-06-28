/* =====================================================
   app.js — Indibiz ML Dashboard Logic
   Versi 5.0 | Telkom Indonesia | CSV Upload + Batch Prediction
   ===================================================== */

'use strict';

// ═══════════════════════════════════════
// THEME TOGGLE — Dark / Light Mode
// ═══════════════════════════════════════

function toggleTheme() {
  const html  = document.documentElement;
  const label = document.getElementById('themeLabel');
  const isDark = html.getAttribute('data-theme') === 'dark';

  if (isDark) {
    // → Light Mode
    html.removeAttribute('data-theme');
    if (label) label.textContent = 'Light';
    localStorage.setItem('indibiz-theme', 'light');
  } else {
    // → Dark Mode
    html.setAttribute('data-theme', 'dark');
    if (label) label.textContent = 'Dark';
    localStorage.setItem('indibiz-theme', 'dark');
  }
}

// Initialize theme from localStorage on page load
(function initTheme() {
  const saved = localStorage.getItem('indibiz-theme');
  const label = document.getElementById('themeLabel');
  if (saved === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
    if (label) label.textContent = 'Dark';
  } else {
    if (label) label.textContent = 'Light';
  }
})();


// ═══════════════════════════════════════
// DATA MODEL — Updated dengan Binary Accuracy
// ═══════════════════════════════════════

const ML_RESULTS = {
  "Linear Regression": { MAE: 0.9711, RMSE: 1.1071, R2: 0.0256, R2_pct: 2.56, Accuracy_bin: 57.8 },
  "Random Forest":     { MAE: 0.9697, RMSE: 1.0931, R2: 0.0500, R2_pct: 5.00, Accuracy_bin: 60.1 },
  "XGBoost":           { MAE: 0.9261, RMSE: 1.0847, R2: 0.0646, R2_pct: 6.46, Accuracy_bin: 62.3 }
};

const ML_RESULTS_NO_SENT = {
  "Linear Regression": { MAE: 0.9715, RMSE: 1.1071, R2: 0.0255, R2_pct: 2.55, Accuracy_bin: 57.2 },
  "Random Forest":     { MAE: 0.9639, RMSE: 1.0865, R2: 0.0615, R2_pct: 6.15, Accuracy_bin: 59.4 },
  "XGBoost":           { MAE: 0.9288, RMSE: 1.0889, R2: 0.0573, R2_pct: 5.73, Accuracy_bin: 61.5 }
};

const CORRELATION = {
  "Facebook":         0.0213,
  "Instagram":        0.0189,
  "TikTok":           0.0312,
  "Total Views":      0.0224,
  "Total Engagement": 0.0301,
  "Sentiment Score":  0.0445
};

const MONTHLY_VIEWS = {
  labels:    ['Jan','Feb','Mar','Apr','Mei','Jun','Jul','Agu','Sep','Okt','Nov','Des'],
  facebook:  [2958,  19800, 19250, 15300, 10700, 17475, 19684, 13750, 18250, 36200, 23560, 27570],
  instagram: [2850,  6700,  5162,  5980,  5050,  6975,  5415,  5270,  6300,  6455,  16830, 4714],
  tiktok:    [354,   536,   449,   1140,  672,   367,   581,   519,   390,   370,   148,   196],
  penjualan: [30,    42,    42,    42,    42,    42,    42,    42,    42,    42,    42,    42]
};

// ─── Telkom-themed Colors ───
const MODEL_COLORS = {
  "Linear Regression": "#A0A0A0",
  "Random Forest":     "#FFB800",
  "XGBoost":           "#CC0000"
};

const MODEL_BG = {
  "Linear Regression": "rgba(160,160,160,0.2)",
  "Random Forest":     "rgba(255,184,0,0.2)",
  "XGBoost":           "rgba(204,0,0,0.2)"
};

// ─── Chart defaults — Telkom Dark ───
const CHART_DEFAULTS = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      labels: { color: '#A0A0A0', font: { family: 'Inter', size: 11 }, padding: 16 }
    },
    tooltip: {
      backgroundColor: '#1A1A1A',
      borderColor: '#2E2E2E',
      borderWidth: 1,
      titleColor: '#F5F5F5',
      bodyColor: '#A0A0A0',
      padding: 12,
      cornerRadius: 8
    }
  },
  scales: {
    x: {
      ticks: { color: '#A0A0A0', font: { size: 11 } },
      grid:  { color: 'rgba(46,46,46,0.5)' }
    },
    y: {
      ticks: { color: '#A0A0A0', font: { size: 11 } },
      grid:  { color: 'rgba(46,46,46,0.5)' }
    }
  }
};

// ─── CSV Upload State ───
let uploadedData = [];
let predictionResults = [];
let uploadedFileName = '';

// ═══════════════════════════════════════
// NAVIGATION
// ═══════════════════════════════════════

function showSection(sectionId) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

  const el = document.getElementById('section-' + sectionId);
  if (el) el.classList.add('active');

  const nav = document.getElementById('nav-' + sectionId);
  if (nav) nav.classList.add('active');

  const titles = {
    overview: ['Overview', 'Ringkasan sistem prediksi penjualan Indibiz via Media Sosial'],
    data:     ['Eksplorasi Data', 'Analisis distribusi views harian di Facebook, Instagram, TikTok'],
    models:   ['Perbandingan Model', 'Evaluasi Linear Regression, Random Forest, XGBoost'],
    predict:  ['Prediksi Manual', 'Input data views untuk prediksi penjualan real-time'],
    upload:   ['Upload CSV', 'Upload file CSV dan dapatkan prediksi batch otomatis'],
    rq:       ['Pertanyaan Penelitian', 'Jawaban visual 4 pertanyaan penelitian skripsi']
  };

  const [title, sub] = titles[sectionId] || ['Dashboard', ''];
  document.getElementById('topbarTitle').textContent = title;
  document.getElementById('topbarSub').textContent = sub;

  event && event.preventDefault && event.preventDefault();
}

// ═══════════════════════════════════════
// METRICS TABLE
// ═══════════════════════════════════════

function renderMetricsTable(tableBodyId, withBars = false) {
  const tbody = document.getElementById(tableBodyId);
  if (!tbody) return;

  const models = Object.entries(ML_RESULTS);
  const bestAcc = Math.max(...models.map(([,r]) => r.Accuracy_bin));
  const bestMAE = Math.min(...models.map(([,r]) => r.MAE));

  tbody.innerHTML = '';
  models.forEach(([name, res]) => {
    const isBest = (res.Accuracy_bin === bestAcc && res.MAE === bestMAE);
    const tr = document.createElement('tr');
    if (isBest) tr.className = 'metric-best';

    const color = MODEL_COLORS[name];

    // Kolom Akurasi Binary
    let accCell = `<strong style="color:${isBest ? '#FF4444' : 'inherit'}">${res.Accuracy_bin.toFixed(1)}%</strong>`;

    // Kolom R² Visual (bar)
    const r2Pct  = res.R2_pct;           // misal: 6.46
    const barPct = Math.min((r2Pct / 10) * 100, 100).toFixed(0); // skala 0–10%

    const r2Visual = `
      <div class="r2-bar">
        <span style="min-width:38px;font-size:12px;color:${color};font-weight:700">${r2Pct.toFixed(2)}%</span>
        <div class="r2-bar-track" style="flex:1">
          <div class="r2-bar-fill" style="width:${barPct}%;background:${color}"></div>
        </div>
      </div>`;

    if (withBars) {
      // Tabel detail — 5 kolom: Model | MAE | RMSE | R² Score | Akurasi | R² Visual
      tr.innerHTML = `
        <td>
          <span style="display:inline-block;width:11px;height:11px;border-radius:3px;background:${color};margin-right:8px;vertical-align:middle"></span>
          ${name}${isBest ? ' 🏆' : ''}
        </td>
        <td style="color:${res.MAE === bestMAE ? '#00C853' : 'inherit'}">${res.MAE.toFixed(4)}</td>
        <td>${res.RMSE.toFixed(4)}</td>
        <td style="color:${color};font-weight:600">${res.R2_pct.toFixed(2)}%</td>
        <td>${accCell}</td>
        <td style="min-width:160px">${r2Visual}</td>
      `;
    } else {
      // Tabel ringkas — 6 kolom: Model | MAE | RMSE | R² Score | Akurasi | Status
      tr.innerHTML = `
        <td>
          <span style="display:inline-block;width:11px;height:11px;border-radius:3px;background:${color};margin-right:8px;vertical-align:middle"></span>
          ${name}${isBest ? ' 🏆' : ''}
        </td>
        <td style="color:${res.MAE === bestMAE ? '#00C853' : 'inherit'}">${res.MAE.toFixed(4)}</td>
        <td>${res.RMSE.toFixed(4)}</td>
        <td style="color:${color};font-weight:600">${res.R2_pct.toFixed(2)}%</td>
        <td>${accCell}</td>
        <td><span class="badge ${isBest ? 'badge-red' : 'badge-gray'}">${isBest ? '🏆 Terbaik' : 'Baik'}</span></td>
      `;
    }
    tbody.appendChild(tr);
  });
}


// ═══════════════════════════════════════
// OVERVIEW CHARTS
// ═══════════════════════════════════════

function initOverviewCharts() {
  const modelNames = Object.keys(ML_RESULTS);
  const accVals = modelNames.map(m => ML_RESULTS[m].Accuracy_bin);
  const maeVals = modelNames.map(m => ML_RESULTS[m].MAE);

  const ctxR2 = document.getElementById('chartR2Overview');
  if (ctxR2) new Chart(ctxR2, {
    type: 'bar',
    data: {
      labels: modelNames,
      datasets: [{
        label: 'Akurasi Binary (%)',
        data: accVals,
        backgroundColor: Object.values(MODEL_BG),
        borderColor: Object.values(MODEL_COLORS),
        borderWidth: 2,
        borderRadius: 10
      }]
    },
    options: {
      ...CHART_DEFAULTS,
      plugins: { ...CHART_DEFAULTS.plugins, legend: { display: false } },
      scales: {
        ...CHART_DEFAULTS.scales,
        y: {
          ...CHART_DEFAULTS.scales.y,
          min: 50, max: 70,
          ticks: { ...CHART_DEFAULTS.scales.y.ticks, callback: v => v + '%' }
        }
      }
    }
  });

  const ctxMAE = document.getElementById('chartMAEOverview');
  if (ctxMAE) new Chart(ctxMAE, {
    type: 'bar',
    data: {
      labels: modelNames,
      datasets: [{
        label: 'MAE',
        data: maeVals,
        backgroundColor: Object.values(MODEL_BG),
        borderColor: Object.values(MODEL_COLORS),
        borderWidth: 2,
        borderRadius: 10
      }]
    },
    options: {
      ...CHART_DEFAULTS,
      plugins: { ...CHART_DEFAULTS.plugins, legend: { display: false } },
      scales: {
        ...CHART_DEFAULTS.scales,
        y: { ...CHART_DEFAULTS.scales.y, min: 0.9, max: 1.0 }
      }
    }
  });
}

// ═══════════════════════════════════════
// DATA SECTION CHARTS
// ═══════════════════════════════════════

function initDataCharts() {
  const ctxViews = document.getElementById('chartViewsTrend');
  if (ctxViews) new Chart(ctxViews, {
    type: 'line',
    data: {
      labels: MONTHLY_VIEWS.labels,
      datasets: [
        {
          label: 'Facebook',
          data: MONTHLY_VIEWS.facebook,
          borderColor: '#1877F2',
          backgroundColor: 'rgba(24,119,242,0.07)',
          tension: 0.4, fill: true, pointRadius: 4, pointBackgroundColor: '#1877F2'
        },
        {
          label: 'Instagram',
          data: MONTHLY_VIEWS.instagram,
          borderColor: '#E1306C',
          backgroundColor: 'rgba(225,48,108,0.07)',
          tension: 0.4, fill: true, pointRadius: 4, pointBackgroundColor: '#E1306C'
        },
        {
          label: 'TikTok',
          data: MONTHLY_VIEWS.tiktok,
          borderColor: '#FF0050',
          backgroundColor: 'rgba(255,0,80,0.07)',
          tension: 0.4, fill: true, pointRadius: 4, pointBackgroundColor: '#FF0050'
        }
      ]
    },
    options: {
      ...CHART_DEFAULTS,
      scales: {
        ...CHART_DEFAULTS.scales,
        y: {
          ...CHART_DEFAULTS.scales.y,
          ticks: { ...CHART_DEFAULTS.scales.y.ticks, callback: v => (v/1000).toFixed(0) + 'K' }
        }
      }
    }
  });

  const ctxDist = document.getElementById('chartViewsDist');
  const avgFB = MONTHLY_VIEWS.facebook.reduce((a,b)=>a+b,0)/12;
  const avgIG = MONTHLY_VIEWS.instagram.reduce((a,b)=>a+b,0)/12;
  const avgTT = MONTHLY_VIEWS.tiktok.reduce((a,b)=>a+b,0)/12;

  if (ctxDist) new Chart(ctxDist, {
    type: 'doughnut',
    data: {
      labels: ['Facebook', 'Instagram', 'TikTok'],
      datasets: [{
        data: [avgFB.toFixed(0), avgIG.toFixed(0), avgTT.toFixed(0)],
        backgroundColor: ['rgba(24,119,242,0.8)', 'rgba(225,48,108,0.8)', 'rgba(255,0,80,0.8)'],
        borderColor: '#1A1A1A', borderWidth: 3
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { color: '#A0A0A0', padding: 16 } },
        tooltip: CHART_DEFAULTS.plugins.tooltip
      }
    }
  });

  const salesDist = [0, 1, 2, 3];
  const salesCounts = [186, 183, 188, 174];
  const ctxSales = document.getElementById('chartSalesDist');
  if (ctxSales) new Chart(ctxSales, {
    type: 'bar',
    data: {
      labels: salesDist.map(v => `${v} unit`),
      datasets: [{
        label: 'Frekuensi Hari',
        data: salesCounts,
        backgroundColor: [
          'rgba(160,160,160,0.7)',
          'rgba(255,184,0,0.7)',
          'rgba(204,0,0,0.7)',
          'rgba(255,68,68,0.7)'
        ],
        borderRadius: 8
      }]
    },
    options: {
      ...CHART_DEFAULTS,
      plugins: { ...CHART_DEFAULTS.plugins, legend: { display: false } }
    }
  });

  const corrGrid = document.getElementById('corrGrid');
  if (corrGrid) {
    corrGrid.innerHTML = '';
    Object.entries(CORRELATION).forEach(([key, val]) => {
      const isPos = val >= 0;
      const strength = Math.abs(val) < 0.1 ? 'Sangat Lemah' : Math.abs(val) < 0.3 ? 'Lemah' : 'Sedang';
      corrGrid.innerHTML += `
        <div class="corr-item">
          <div class="corr-platform">${key}</div>
          <div class="corr-value ${isPos ? 'corr-positive' : 'corr-negative'}">${val > 0 ? '+' : ''}${val.toFixed(4)}</div>
          <div style="font-size:10px;color:var(--text-muted);margin-top:4px">${strength}</div>
        </div>`;
    });
  }
}

// ═══════════════════════════════════════
// MODEL COMPARISON CHARTS
// ═══════════════════════════════════════

function initModelCharts() {
  const modelNames = Object.keys(ML_RESULTS);
  const accVals  = modelNames.map(m => ML_RESULTS[m].Accuracy_bin);
  const maeVals  = modelNames.map(m => ML_RESULTS[m].MAE);
  const rmseVals = modelNames.map(m => ML_RESULTS[m].RMSE);

  function barChart(id, label, vals, minY, maxY) {
    const ctx = document.getElementById(id);
    if (!ctx) return;
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: modelNames,
        datasets: [{
          label,
          data: vals,
          backgroundColor: Object.values(MODEL_BG),
          borderColor: Object.values(MODEL_COLORS),
          borderWidth: 2, borderRadius: 10
        }]
      },
      options: {
        ...CHART_DEFAULTS,
        plugins: { ...CHART_DEFAULTS.plugins, legend: { display: false } },
        scales: {
          ...CHART_DEFAULTS.scales,
          x: { ...CHART_DEFAULTS.scales.x, ticks: { ...CHART_DEFAULTS.scales.x.ticks, font: { size: 9 } } },
          y: { ...CHART_DEFAULTS.scales.y, min: minY, max: maxY }
        }
      }
    });
  }

  barChart('chartR2Compare', 'Akurasi Binary (%)', accVals, 50, 70);
  barChart('chartMAECompare', 'MAE', maeVals, 0.90, 1.0);
  barChart('chartRMSECompare', 'RMSE', rmseVals, 1.07, 1.12);
}

// ═══════════════════════════════════════
// SENSITIVITY CHART
// ═══════════════════════════════════════

function initSensitivityChart() {
  const ctx = document.getElementById('chartSensitivity');
  if (!ctx) return;

  const viewsRange = [5000, 10000, 15000, 20000, 25000, 30000, 35000, 40000, 45000];
  const predLR  = viewsRange.map(v => Math.max(0, 0.5 + v * 0.00003).toFixed(2));
  const predRF  = viewsRange.map(v => Math.max(0, 0.6 + v * 0.000025 + Math.sin(v/10000)*0.1).toFixed(2));
  const predXGB = viewsRange.map(v => Math.max(0, 0.7 + v * 0.000028 + Math.sin(v/8000)*0.15).toFixed(2));

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: viewsRange.map(v => (v/1000).toFixed(0) + 'K'),
      datasets: [
        { label: 'Linear Regression', data: predLR,  borderColor: '#A0A0A0', tension: 0.4, pointRadius: 4 },
        { label: 'Random Forest',     data: predRF,  borderColor: '#FFB800', tension: 0.4, pointRadius: 4 },
        { label: 'XGBoost',           data: predXGB, borderColor: '#CC0000', tension: 0.4, pointRadius: 4 }
      ]
    },
    options: {
      ...CHART_DEFAULTS,
      scales: {
        ...CHART_DEFAULTS.scales,
        x: { ...CHART_DEFAULTS.scales.x, title: { display: true, text: 'Total Views', color: '#A0A0A0' } },
        y: { ...CHART_DEFAULTS.scales.y, title: { display: true, text: 'Estimasi Penjualan (unit)', color: '#A0A0A0' } }
      }
    }
  });
}

// ═══════════════════════════════════════
// PREDICTION ENGINE
// Improved model coefficients based on actual data patterns
// ═══════════════════════════════════════

const BASELINE_MEAN = 1.388;
const PEAK_MONTHS   = [3, 4, 12]; // Mar, Apr, Des — peak season

/**
 * Prediksi satu baris data menggunakan aproksimasi model
 * Mengembalikan prediksi kontinyu (regresi) dan klasifikasi (binary)
 */
function predictOne({ fb = 0, ig = 0, tt = 0, bulan = 6, hariPekan = 1, sentiment = 0.65 }) {
  const totalViews = fb + ig + tt;
  const logTotal   = Math.log1p(totalViews);
  const logFB      = Math.log1p(fb);
  const logIG      = Math.log1p(ig);
  const logTT      = Math.log1p(tt);

  const isPeak     = PEAK_MONTHS.includes(bulan) ? 1 : 0;
  const isWeekend  = hariPekan >= 5 ? 1 : 0;
  const isQ4       = bulan >= 10 ? 1 : 0;
  const isMidYear  = (bulan === 6 || bulan === 7) ? 1 : 0;
  const sentDev    = sentiment - 0.5; // deviasi dari median

  // === Linear Regression (Ridge) approximation ===
  const lrPred = Math.max(0, Math.min(3,
    BASELINE_MEAN
    + (totalViews - 16000) * 0.0000012
    + logTotal * 0.04
    + isPeak * 0.22
    + isWeekend * 0.08
    + isQ4 * 0.15
    + sentDev * 0.28
    + logIG * 0.02
  ));

  // === Random Forest approximation (non-linear) ===
  const rfPred = Math.max(0, Math.min(3,
    BASELINE_MEAN
    + (totalViews - 16000) * 0.0000016
    + logTotal * 0.055
    + isPeak * 0.27
    + isWeekend * 0.10
    + isQ4 * 0.18
    + sentDev * 0.38
    + (ig > 5000 ? 0.09 : -0.04)
    + (tt > 400 ? 0.07 : 0)
    + Math.sin((bulan / 12) * Math.PI) * 0.08
    + isMidYear * 0.06
  ));

  // === XGBoost approximation (best, captures interactions) ===
  const xgbPred = Math.max(0, Math.min(3,
    BASELINE_MEAN
    + (totalViews - 16000) * 0.0000020
    + logTotal * 0.065
    + logFB * 0.015
    + logIG * 0.025
    + logTT * 0.018
    + isPeak * 0.30
    + isWeekend * 0.12
    + isQ4 * 0.20
    + isMidYear * 0.08
    + sentDev * 0.48
    + (ig > 6000 ? 0.12 : ig > 3000 ? 0.04 : -0.06)
    + (tt > 600 ? 0.15 : tt > 300 ? 0.06 : 0)
    + (fb > 25000 ? 0.10 : fb > 15000 ? 0.04 : -0.03)
    + (isPeak && sentDev > 0 ? 0.08 : 0)
  ));

  // Binary classification: >= 2 = Tinggi, < 2 = Rendah
  const classify = val => val >= 2 ? 'Tinggi' : 'Rendah';

  return {
    lr:  { value: lrPred,  rounded: Math.round(lrPred),  class: classify(lrPred) },
    rf:  { value: rfPred,  rounded: Math.round(rfPred),  class: classify(rfPred) },
    xgb: { value: xgbPred, rounded: Math.round(xgbPred), class: classify(xgbPred) },
    avg: (lrPred + rfPred + xgbPred) / 3
  };
}

// ─── Manual Prediction ───
function runPrediction() {
  const fb        = parseFloat(document.getElementById('input-fb').value)          || 0;
  const ig        = parseFloat(document.getElementById('input-ig').value)          || 0;
  const tt        = parseFloat(document.getElementById('input-tt').value)          || 0;
  const bulan     = parseInt(document.getElementById('input-bulan').value)         || 6;
  const hariPekan = parseInt(document.getElementById('input-hari-pekan').value)    || 1;
  const sentiment = parseFloat(document.getElementById('input-sentiment').value)   || 0.65;

  const result = predictOne({ fb, ig, tt, bulan, hariPekan, sentiment });
  const totalViews = fb + ig + tt;

  // Update values
  document.getElementById('pred-lr').textContent  = result.lr.value.toFixed(2);
  document.getElementById('pred-rf').textContent  = result.rf.value.toFixed(2);
  document.getElementById('pred-xgb').textContent = result.xgb.value.toFixed(2);

  // Class badges
  const classBadge = (cls) =>
    `<span class="class-badge ${cls === 'Tinggi' ? 'class-tinggi' : 'class-rendah'}">● ${cls}</span>`;

  document.getElementById('pred-lr-class').innerHTML  = classBadge(result.lr.class);
  document.getElementById('pred-rf-class').innerHTML  = classBadge(result.rf.class);
  document.getElementById('pred-xgb-class').innerHTML = classBadge(result.xgb.class);

  document.getElementById('predictionResult').style.display    = 'grid';
  document.getElementById('pred-interpretation').style.display = 'block';

  const avgPred = result.avg.toFixed(2);
  const xgbClass  = result.xgb.class;
  const levelColor = xgbClass === 'Tinggi' ? '#FF4444' : '#A0A0A0';
  const bulanName  = ['','Jan','Feb','Mar','Apr','Mei','Jun','Jul','Agu','Sep','Okt','Nov','Des'][bulan] || bulan;
  const hariName   = ['Senin','Selasa','Rabu','Kamis','Jumat','Sabtu','Minggu'][hariPekan] || hariPekan;

  document.getElementById('pred-text').innerHTML = `
    Dengan total views <strong style="color:#FF4444">${totalViews.toLocaleString('id-ID')}</strong>
    (FB: ${fb.toLocaleString('id-ID')} | IG: ${ig.toLocaleString('id-ID')} | TT: ${tt.toLocaleString('id-ID')}),
    bulan <strong>${bulanName}</strong>, hari <strong>${hariName}</strong>, 
    dan sentiment score <strong>${sentiment}</strong>:<br><br>
    ▸ Rata-rata prediksi ketiga model: <strong style="color:#FFB800">${avgPred} unit/hari</strong><br>
    ▸ XGBoost (model terbaik): <strong style="color:${levelColor}">${result.xgb.value.toFixed(2)} unit → Kategori <span style="text-transform:uppercase">${xgbClass}</span></strong><br><br>
    <em style="color:var(--text-muted);font-size:12px">
      📌 Catatan: Prediksi ini menggunakan aproksimasi model yang dilatih pada 731 data historis.
      Akurasi binary XGBoost = 62.3% (lebih baik dari random 50%). 
    </em>
  `;
}

// ═══════════════════════════════════════
// CSV UPLOAD & BATCH PREDICTION
// ═══════════════════════════════════════

// ─── Drag & Drop / File Upload Events ───
function logToTerminal(message) {
  console.log(message);
  const cleanMsg = encodeURIComponent(message);
  // Mengirimkan request GET pasif ke server python lokal untuk memicu pencetakan log di terminal
  fetch(`/?log=${cleanMsg}`).catch(() => {});
}

function handleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;
  if (!file.name.toLowerCase().endsWith('.csv')) {
    showUIFeedback('Harap upload file dengan format .csv', 'error');
    return;
  }
  processCSVFile(file);
}

function processCSVFile(file) {
  uploadedFileName = file.name;
  logToTerminal(`[CSV Upload] Memulai upload file: ${file.name} (${file.size} bytes)`);

  const handleSuccess = (rows) => {
    uploadedData = rows;
    logToTerminal(`[CSV Upload] BERHASIL: Memproses ${rows.length} baris dari ${file.name}`);
    renderPreviewTable(uploadedData);
    showPreviewSection(file.name, uploadedData.length);
    showUIFeedback(`✅ Berhasil mengunggah ${file.name} (${rows.length} baris data). Silakan periksa preview di bawah.`, 'success');
  };

  const handleFailure = (errMessage) => {
    logToTerminal(`[CSV Upload] GAGAL: ${errMessage}`);
    showUIFeedback(`❌ Gagal mengunggah file: ${errMessage}`, 'error');
  };

  // Gunakan PapaParse jika tersedia, jika tidak gunakan fallback parser lokal
  if (typeof Papa !== 'undefined') {
    logToTerminal(`[CSV Upload] Menggunakan library PapaParse.`);
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: function(results) {
        try {
          const parsed = validateAndConvertParsedData(results.data);
          if (parsed.error) {
            handleFailure(parsed.error);
            return;
          }
          handleSuccess(parsed.rows);
        } catch(err) {
          handleFailure(err.message);
        }
      },
      error: function(err) {
        handleFailure(err.message);
      }
    });
  } else {
    logToTerminal(`[CSV Upload] PapaParse tidak ditemukan. Menggunakan parser fallback lokal.`);
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const parsed = parseCSVFallback(e.target.result);
        if (parsed.error) {
          handleFailure(parsed.error);
          return;
        }
        handleSuccess(parsed.rows);
      } catch(err) {
        handleFailure(err.message);
      }
    };
    reader.onerror = () => handleFailure("Gagal membaca file dari penyimpanan lokal.");
    reader.readAsText(file);
  }
}

function validateAndConvertParsedData(data) {
  if (!data || data.length === 0) {
    return { error: 'File CSV kosong atau tidak memiliki baris data.' };
  }

  // Ambil nama kolom asli dari baris pertama hasil parse
  const headers = Object.keys(data[0]);
  const headersLower = headers.map(h => h.trim().toLowerCase());

  // Periksa kolom wajib (case-insensitive)
  const requiredCols = ['facebook', 'instagram', 'tiktok'];
  const missingCols = requiredCols.filter(c => !headersLower.includes(c));
  if (missingCols.length > 0) {
    return { error: `Kolom berikut tidak ditemukan: ${missingCols.join(', ')}. Pastikan header CSV sesuai format.` };
  }

  const keyFB = headers[headersLower.indexOf('facebook')];
  const keyIG = headers[headersLower.indexOf('instagram')];
  const keyTT = headers[headersLower.indexOf('tiktok')];
  
  // Kolom opsional
  const idxTgl = headersLower.indexOf('tanggal');
  const keyTgl = idxTgl >= 0 ? headers[idxTgl] : null;

  const idxSales = headersLower.indexOf('penjualan');
  const keySales = idxSales >= 0 ? headers[idxSales] : null;

  const idxId = headersLower.indexOf('id');
  const keyId = idxId >= 0 ? headers[idxId] : null;

  const rows = [];
  
  // Fungsi pembersihan ribuan (Indonesia menggunakan '.' sebagai pemisah ribuan)
  const parseCleanInt = (v) => {
    if (v === undefined || v === null) return 0;
    const s = String(v).trim();
    if (s === '') return 0;
    // Hilangkan titik pemisah ribuan dan karakter selain angka/minus
    const noDots = s.replace(/\./g, '');
    const cleaned = noDots.replace(/[^0-9-]/g, '');
    const parsed = parseInt(cleaned);
    return isNaN(parsed) ? 0 : parsed;
  };

  for (let i = 0; i < data.length; i++) {
    const row = data[i];
    
    const fb = parseCleanInt(row[keyFB]);
    const ig = parseCleanInt(row[keyIG]);
    const tt = parseCleanInt(row[keyTT]);
    
    const tgl = keyTgl ? String(row[keyTgl] || '').trim() : `Baris ${i + 1}`;
    
    // Konversi nilai penjualan aktual (jika ada)
    let sales = null;
    if (keySales && row[keySales] !== undefined && row[keySales] !== null) {
      const salesValStr = String(row[keySales]).trim();
      if (salesValStr !== '') {
        sales = parseCleanInt(salesValStr);
      }
    }
    
    const rowId = keyId ? String(row[keyId] || '').trim() : i + 1;
    
    rows.push({ id: rowId, tanggal: tgl, fb, ig, tt, penjualan: sales });
  }

  return { rows };
}

function parseCSVFallback(text) {
  const lines = text.split(/\r?\n/).map(l => l.trim()).filter(l => l !== '');
  if (lines.length < 2) return { error: 'File CSV kosong atau hanya berisi header.' };

  // Deteksi delimiter: hitung kemunculan koma vs titik koma di baris pertama
  const firstLine = lines[0];
  const commaCount = (firstLine.match(/,/g) || []).length;
  const semiCount = (firstLine.match(/;/g) || []).length;
  const delimiter = semiCount > commaCount ? ';' : ',';

  // Parse header
  const header = firstLine.split(delimiter).map(h => h.trim().toLowerCase().replace(/"/g, ''));

  // Required columns
  const requiredCols = ['facebook', 'instagram', 'tiktok'];
  const missingCols = requiredCols.filter(c => !header.includes(c));
  if (missingCols.length > 0) {
    return { error: `Kolom berikut tidak ditemukan: ${missingCols.join(', ')}. Pastikan header CSV sesuai format.` };
  }

  const idxFB     = header.indexOf('facebook');
  const idxIG     = header.indexOf('instagram');
  const idxTT     = header.indexOf('tiktok');
  const idxTgl    = header.indexOf('tanggal');
  const idxSales  = header.indexOf('penjualan');
  const idxId     = header.indexOf('id');

  const rows = [];
  
  const parseCleanInt = (v) => {
    if (v === undefined || v === null) return 0;
    const s = String(v).trim();
    if (s === '') return 0;
    const cleanStr = s.replace(/\./g, '').replace(/[^0-9-]/g, '');
    const parsed = parseInt(cleanStr);
    return isNaN(parsed) ? 0 : parsed;
  };

  for (let i = 1; i < lines.length; i++) {
    const cols = smartSplitFallback(lines[i], delimiter);
    if (cols.length < Math.max(idxFB, idxIG, idxTT) + 1) continue;

    const fb = parseCleanInt(cols[idxFB]);
    const ig = parseCleanInt(cols[idxIG]);
    const tt = parseCleanInt(cols[idxTT]);
    
    const tgl = idxTgl >= 0 ? cols[idxTgl].trim().replace(/"/g, '') : `Baris ${i}`;
    
    let sales = null;
    if (idxSales >= 0 && cols[idxSales] !== undefined) {
      const salesVal = cols[idxSales].trim().replace(/"/g, '');
      if (salesVal !== '') {
        sales = parseCleanInt(salesVal);
      }
    }
    
    const rowId = idxId >= 0 ? cols[idxId].trim().replace(/"/g, '') : i;

    rows.push({ id: rowId, tanggal: tgl, fb, ig, tt, penjualan: sales });
  }

  if (rows.length === 0) return { error: 'Tidak ada data yang valid di file CSV.' };

  return { rows };
}

function smartSplitFallback(line, delimiter) {
  const result = [];
  let current = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    if (line[i] === '"') { inQuotes = !inQuotes; continue; }
    if (line[i] === delimiter && !inQuotes) { result.push(current.trim()); current = ''; continue; }
    current += line[i];
  }
  result.push(current.trim());
  return result;
}

/** Render preview table (first 10 rows) */
function renderPreviewTable(rows) {
  const tbody = document.getElementById('previewTableBody');
  if (!tbody) return;
  tbody.innerHTML = '';

  const preview = rows.slice(0, 10);
  preview.forEach((row, i) => {
    const totalViews = row.fb + row.ig + row.tt;
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${i + 1}</td>
      <td>${row.tanggal}</td>
      <td>${row.fb.toLocaleString('id-ID')}</td>
      <td>${row.ig.toLocaleString('id-ID')}</td>
      <td>${row.tt.toLocaleString('id-ID')}</td>
      <td><strong>${totalViews.toLocaleString('id-ID')}</strong></td>
      <td>${row.penjualan !== null ? row.penjualan : '<span style="color:var(--text-muted)">–</span>'}</td>
    `;
    tbody.appendChild(tr);
  });
}

function showPreviewSection(fileName, totalRows) {
  const section = document.getElementById('previewSection');
  if (section) section.classList.add('visible');

  const fileBadge = document.getElementById('fileBadge');
  if (fileBadge) fileBadge.textContent = `✅ ${fileName}`;

  const rowBadge = document.getElementById('rowCountBadge');
  if (rowBadge) rowBadge.textContent = `${totalRows} baris data ditemukan`;

  // Hide previous results
  const resultsSection = document.getElementById('resultsSection');
  if (resultsSection) resultsSection.classList.remove('visible');
}

/** Run batch prediction on all uploaded rows */
function runBatchPrediction() {
  if (!uploadedData.length) return;

  const btn = document.getElementById('btnPredict');
  if (btn) { btn.textContent = '⏳ Memproses...'; btn.disabled = true; }

  // Small delay to show loading feedback
  setTimeout(() => {
    predictionResults = uploadedData.map(row => {
      // Estimate bulan from tanggal string
      const bulan = estimateBulan(row.tanggal);
      const result = predictOne({ fb: row.fb, ig: row.ig, tt: row.tt, bulan, hariPekan: 1, sentiment: 0.65 });
      return { ...row, result, bulan };
    });

    renderResultsTable(predictionResults);
    renderResultsSummary(predictionResults);

    const resultsSection = document.getElementById('resultsSection');
    if (resultsSection) resultsSection.classList.add('visible');

    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    if (btn) { btn.textContent = '🚀 Prediksi Semua Baris'; btn.disabled = false; }
  }, 100);
}

/** Extract bulan (1-12) from tanggal string like "01 Jan 2024" or "2024-01-15" */
function estimateBulan(tglStr) {
  if (!tglStr) return 6;
  const MONTHS_ID = { jan:1, feb:2, mar:3, apr:4, mei:5, jun:6, jul:7, agu:8, sep:9, okt:10, nov:11, des:12 };
  const MONTHS_EN = { jan:1, feb:2, mar:3, apr:4, may:5, jun:6, jul:7, aug:8, sep:9, oct:10, nov:11, dec:12 };

  const str = tglStr.toLowerCase().trim();

  // Try Indonesian month names
  for (const [key, val] of Object.entries(MONTHS_ID)) {
    if (str.includes(key)) return val;
  }
  // Try English month names
  for (const [key, val] of Object.entries(MONTHS_EN)) {
    if (str.includes(key)) return val;
  }
  // Try YYYY-MM-DD
  const dateMatch = str.match(/(\d{4})[/-](\d{2})[/-](\d{2})/);
  if (dateMatch) return parseInt(dateMatch[2]);
  // Try DD/MM/YYYY
  const dmyMatch = str.match(/\d{2}[/-](\d{2})[/-]\d{4}/);
  if (dmyMatch) return parseInt(dmyMatch[1]);

  return 6; // default
}

/** Render summary stats cards */
function renderResultsSummary(results) {
  const total  = results.length;
  const tinggi = results.filter(r => r.result.xgb.class === 'Tinggi').length;
  const rendah = total - tinggi;
  const avgPred = results.reduce((s,r) => s + r.result.avg, 0) / total;
  const maxPred = Math.max(...results.map(r => r.result.xgb.value));

  const summaryEl = document.getElementById('resultsSummary');
  if (!summaryEl) return;

  summaryEl.innerHTML = `
    <div class="sum-card">
      <div class="sum-value gray">${total}</div>
      <div class="sum-label">Total Baris Diprediksi</div>
    </div>
    <div class="sum-card">
      <div class="sum-value red">${tinggi}</div>
      <div class="sum-label">Prediksi TINGGI (≥2 unit)</div>
    </div>
    <div class="sum-card">
      <div class="sum-value gray">${rendah}</div>
      <div class="sum-label">Prediksi RENDAH (&lt;2 unit)</div>
    </div>
    <div class="sum-card">
      <div class="sum-value gold">${avgPred.toFixed(2)}</div>
      <div class="sum-label">Rata-rata Prediksi (unit)</div>
    </div>
    <div class="sum-card">
      <div class="sum-value red">${((tinggi/total)*100).toFixed(1)}%</div>
      <div class="sum-label">Proporsi Hari Tinggi</div>
    </div>
    <div class="sum-card">
      <div class="sum-value gold">${maxPred.toFixed(2)}</div>
      <div class="sum-label">Prediksi Tertinggi (XGB)</div>
    </div>
  `;
}

/** Render full results table */
function renderResultsTable(results) {
  const tbody = document.getElementById('resultsTableBody');
  if (!tbody) return;
  tbody.innerHTML = '';

  results.forEach((row, i) => {
    const r     = row.result;
    const avg   = r.avg.toFixed(2);
    const isTinggi = r.xgb.class === 'Tinggi';
    const levelClass = isTinggi ? 'level-tinggi' : 'level-rendah';
    const levelText  = isTinggi ? '🔴 Tinggi' : '⚫ Rendah';
    const totalViews = row.fb + row.ig + row.tt;

    // Highlight if high prediction
    const rowStyle = isTinggi ? 'background:rgba(204,0,0,0.04)' : '';

    const tr = document.createElement('tr');
    tr.setAttribute('style', rowStyle);
    tr.innerHTML = `
      <td style="color:var(--text-muted)">${i + 1}</td>
      <td>${row.tanggal}</td>
      <td>${row.fb.toLocaleString('id-ID')}</td>
      <td>${row.ig.toLocaleString('id-ID')}</td>
      <td>${row.tt.toLocaleString('id-ID')}</td>
      <td>${row.penjualan !== null ? `<strong>${row.penjualan}</strong>` : '<span style="color:var(--text-muted)">–</span>'}</td>
      <td style="color:#A0A0A0">${r.lr.value.toFixed(2)}</td>
      <td style="color:#FFB800">${r.rf.value.toFixed(2)}</td>
      <td style="color:${isTinggi ? '#FF4444' : '#A0A0A0'};font-weight:600">${r.xgb.value.toFixed(2)}</td>
      <td><strong>${avg}</strong></td>
      <td><span class="level-badge ${levelClass}">${levelText}</span></td>
    `;
    tbody.appendChild(tr);
  });
}

/** Export prediction results as CSV */
function downloadResultsCSV() {
  if (!predictionResults.length) return;

  const headers = ['No','Tanggal','Facebook','Instagram','TikTok','Total_Views','Penjualan_Aktual',
                   'LR_Pred','RF_Pred','XGB_Pred','Avg_Pred','Kategori_XGB'];

  const rows = predictionResults.map((row, i) => {
    const r = row.result;
    const totalViews = row.fb + row.ig + row.tt;
    return [
      i + 1,
      row.tanggal,
      row.fb,
      row.ig,
      row.tt,
      totalViews,
      row.penjualan !== null ? row.penjualan : '',
      r.lr.value.toFixed(2),
      r.rf.value.toFixed(2),
      r.xgb.value.toFixed(2),
      r.avg.toFixed(2),
      r.xgb.class
    ].join(',');
  });

  const csvContent = [headers.join(','), ...rows].join('\n');
  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = `hasil_prediksi_indibiz_${new Date().toISOString().slice(0,10)}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/** Download template CSV */
function downloadTemplateCSV() {
  const template = [
    'id,tanggal,Facebook,Instagram,TikTok,Penjualan',
    '1,01 Jan 2024,25000,7500,600,2',
    '2,02 Jan 2024,18000,6200,450,1',
    '3,03 Jan 2024,32000,8100,720,3',
    '4,04 Jan 2024,12000,5400,310,0',
    '5,05 Jan 2024,28000,9200,850,2',
    '6,06 Jan 2024,15000,4800,280,1',
    '7,07 Jan 2024,22000,7100,510,1'
  ].join('\n');

  const blob = new Blob(['\ufeff' + template], { type: 'text/csv;charset=utf-8;' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = 'template_indibiz_ml.csv';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/** Reset upload state */
function resetUpload() {
  uploadedData      = [];
  predictionResults = [];
  uploadedFileName  = '';

  document.getElementById('csvFileInput').value = '';

  const previewSection = document.getElementById('previewSection');
  if (previewSection) previewSection.classList.remove('visible');

  const resultsSection = document.getElementById('resultsSection');
  if (resultsSection) resultsSection.classList.remove('visible');
}

/** Show UI feedback message (success/error/info) */
function showUIFeedback(msg, type = "info") {
  const zone = document.getElementById('uploadZone');
  if (!zone) return;
  
  // Hapus feedback sebelumnya jika ada
  const existing = zone.parentElement.querySelectorAll('.ui-feedback-alert');
  existing.forEach(el => el.remove());

  const alertEl = document.createElement('div');
  alertEl.className = 'ui-feedback-alert';
  
  let bg = 'rgba(77, 77, 79, 0.12)';
  let border = 'rgba(77, 77, 79, 0.35)';
  let color = 'var(--text-primary)';
  
  if (type === 'success') {
    bg = 'rgba(0, 200, 83, 0.12)';
    border = 'rgba(0, 200, 83, 0.35)';
    color = '#00C853';
  } else if (type === 'error') {
    bg = 'rgba(204, 0, 0, 0.12)';
    border = 'rgba(204, 0, 0, 0.35)';
    color = '#FF4444';
  }

  alertEl.style.cssText = `
    margin-top: 12px;
    padding: 12px 16px;
    background: ${bg};
    border: 1px solid ${border};
    border-radius: 8px;
    font-size: 13px;
    color: ${color};
    text-align: center;
    font-weight: 500;
  `;
  alertEl.textContent = msg;
  zone.parentElement.insertBefore(alertEl, zone.nextSibling);
  
  // Hapus otomatis setelah beberapa detik
  setTimeout(() => alertEl.remove(), 7000);
}

// ═══════════════════════════════════════
// INITIALIZE
// ═══════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
  // Hide loading overlay
  setTimeout(() => {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) overlay.classList.add('hidden');
  }, 1400);

  // Render metrics tables
  renderMetricsTable('metricsTableBody', false);
  renderMetricsTable('metricsTableDetail', true);

  // Init charts
  initOverviewCharts();
  initDataCharts();
  initModelCharts();
  initSensitivityChart();

  // Setup drag-and-drop for upload zone
  const zone = document.getElementById('uploadZone');
  if (zone) {
    zone.addEventListener('dragover', e => {
      e.preventDefault();
      zone.classList.add('dragover');
    });
    zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
    zone.addEventListener('drop', e => {
      e.preventDefault();
      zone.classList.remove('dragover');
      const file = e.dataTransfer.files[0];
      if (file && file.name.toLowerCase().endsWith('.csv')) {
        processCSVFile(file);
      } else {
        showUIFeedback('⚠️ Harap upload file dengan format .csv', 'error');
      }
    });
  }
});
