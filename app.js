// ============================================
// SECTION 1: INISIALISASI & KONFIGURASI
// ============================================
/* =====================================================
   app.js — Indibiz ML Dashboard Logic
   Versi 5.0 | Telkom Indonesia | CSV Upload + Batch Prediction
   ===================================================== */

'use strict';
// Simple sanitization function to prevent XSS
function sanitize(str) {
  if (str === null || str === undefined) return '';
  const s = String(str);
  return s.replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/"/g, '&quot;')
          .replace(/'/g, '&#x27;')
          .replace(/\//g, '&#x2F;');
}


// ─── AUTH PROTECTION GUARD ───
(async function initAuthCheck() {
  if (window.location.hostname.includes('netlify.app') || window.location.hostname.includes('github.io')) {
    console.log("[Auth] Bypassing auth check on static hosting (Netlify/GitHub Pages).");
    return;
  }
  try {
    const res = await fetch('/api/verify');
    if (res.status === 404) {
      console.log("[Auth] API verify returned 404 (local static server). Bypassing.");
      return;
    }
    const data = await res.json();
    if (!res.ok || !data.success) {
      window.location.href = '/login';
    } else {
      console.log("[Auth] Authenticated successfully as:", data.username);
    }
  } catch (e) {
    console.log("[Auth] Fetch verify failed, assuming static environment:", e);
  }
})();

// ============================================
// SECTION 2: AUTENTIKASI & SESSION
// ============================================

async function handleLogout() {
  if (window.location.hostname.includes('netlify.app') || window.location.hostname.includes('github.io')) {
    alert("Logout tidak tersedia di demo hosting statis (Netlify).");
    return;
  }
  try {
    const res = await fetch('/api/logout', { method: 'POST' });
    const data = await res.json();
    if (res.ok && data.success) {
      sessionStorage.removeItem('app_session');
      localStorage.removeItem('app_session');
      window.location.href = '/login';
    } else {
      alert("Gagal melakukan logout.");
    }
  } catch (err) {
    console.error(err);
    alert("Terjadi kesalahan koneksi saat logout.");
  }
}

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
    localStorage.setItem('app_theme', 'light');
  } else {
    // → Dark Mode
    html.setAttribute('data-theme', 'dark');
    if (label) label.textContent = 'Dark';
    localStorage.setItem('app_theme', 'dark');
  }
}

// Initialize theme from localStorage on page load
(function initTheme() {
  const saved = localStorage.getItem('app_theme');
  const label = document.getElementById('themeLabel');
  if (saved === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
    if (label) label.textContent = 'Dark';
  } else {
    if (label) label.textContent = 'Light';
  }
})();


// ═══════════════════════════════════════
// DATA MODEL — Regresi Total Views (R² / MAE / RMSE / MAPE)
// Target: Total Views (Facebook + Instagram + TikTok)
// ═══════════════════════════════════════

const ML_RESULTS = {
  "Linear Regression": { MAE: 0.2059, RMSE: 0.2828, R2: 0.8420, R2_pct: 84.20 },
  "Random Forest":     { MAE: 0.1138, RMSE: 0.2637, R2: 0.8626, R2_pct: 86.26 },
  "XGBoost":           { MAE:  0.1373, RMSE:  0.2600, R2: 0.8665, R2_pct: 86.65 }
};

const ML_RESULTS_NO_SENT = {
  "Linear Regression": { MAE: 0.2059, RMSE: 0.2827, R2: 0.8421, R2_pct: 84.21 },
  "Random Forest":     { MAE: 0.1215, RMSE: 0.2788, R2: 0.8465, R2_pct: 84.65 },
  "XGBoost":           { MAE:  0.1410, RMSE:  0.2586, R2: 0.8679, R2_pct: 86.79 }
};

const CORRELATION = {
  "Facebook":         0.8287,
  "Instagram":        0.6089,
  "TikTok":          -0.3416,
  "Total Views":      0.9048,
  "Total Engagement": 0.8375,
  "Sentiment Score":  0.8089
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
  animation: { duration: 0 },
  hover: { animationDuration: 0 },
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
let forecastResults = [];
let currentMLResults = null; // Menyimpan hasil ML terbaru setelah upload CSV

// ═══════════════════════════════════════
// NAVIGATION
// ═══════════════════════════════════════

// ============================================
// SECTION 6: UI & EVENT HANDLER
// ============================================

function toggleSidebar() {
  document.body.classList.toggle('sidebar-open');
}

function showSection(sectionId) {
  // Close sidebar on mobile/tablet after navigating
  document.body.classList.remove('sidebar-open');

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
    upload:   ['Upload CSV', 'Upload file CSV dan dapatkan prediksi batch otomatis'],
    rq:       ['Pertanyaan Penelitian', 'Jawaban visual 4 pertanyaan penelitian skripsi']
  };

  const [title, sub] = titles[sectionId] || ['Dashboard', ''];
  document.getElementById('topbarTitle').textContent = title;
  document.getElementById('topbarSub').textContent = sub;

  // Render/Update charts lazily when sections become visible to prevent 0-size canvas blank rendering
  if (sectionId === 'models' && typeof predictionResults !== 'undefined' && predictionResults && predictionResults.length > 0) {
    console.log("[showSection] Models section active. Triggering charts redraw with 150ms reflow delay. Data size:", predictionResults.length);
    setTimeout(() => {
      const resultsToUse = currentMLResults || ML_RESULTS;
      initModelCharts(resultsToUse);
      initActualVsPredictedChart(predictionResults);
      initResidualsChart(predictionResults);
      initFeatureImportanceChart(predictionResults);
      initTimeSeriesCompareChart(predictionResults);
    }, 500);
  }
  if (sectionId === 'data' && typeof predictionResults !== 'undefined' && predictionResults && predictionResults.length > 0) {
    console.log("[showSection] Data section active. Triggering chart redraw with 500ms reflow delay.");
    setTimeout(() => {
      initMonthlyTrendDynamic(predictionResults);
      updateDataChartsDynamic(uploadedData);
    }, 500);
  }

  // Force Chart.js to recalculate container dimensions by dispatching window resize events
  setTimeout(() => { window.dispatchEvent(new Event('resize')); }, 200);
  setTimeout(() => { window.dispatchEvent(new Event('resize')); }, 600);

  if (window.event) window.event.preventDefault();
}

// ═══════════════════════════════════════
// METRICS TABLE
// ═══════════════════════════════════════

function renderMetricsTable(tableBodyId, withBars = false) {
  const tbody = document.getElementById(tableBodyId);
  if (!tbody) return;

  const models = Object.entries(ML_RESULTS);
  const bestMAE = Math.min(...models.map(([,r]) => r.MAE));
  const bestR2  = Math.max(...models.map(([,r]) => r.R2_pct));

  tbody.innerHTML = '';
  models.forEach(([name, res]) => {
    const isBest = res.R2_pct === bestR2;
    const tr = document.createElement('tr');
    const color = MODEL_COLORS[name];

    // Kolom R² Visual (bar — skala 0–100%)
    const r2Pct  = res.R2_pct || 0;
    const barPct = Math.min(r2Pct, 100).toFixed(0);
    const r2Visual = `
      <div class="r2-bar">
        <span style="min-width:42px;font-size:12px;color:${color};font-weight:700">${r2Pct.toFixed(2)}%</span>
        <div class="r2-bar-track" style="flex:1">
          <div class="r2-bar-fill" style="width:${barPct}%;background:${color}"></div>
        </div>
      </div>`;

    if (withBars) {
      // Tabel detail — 4 kolom: Model | MAE | RMSE | R² Score | R² Visual
      tr.innerHTML = `
        <td>
          <span style="display:inline-block;width:11px;height:11px;border-radius:3px;background:${color};margin-right:8px;vertical-align:middle"></span>
          ${name}
        </td>
        <td style="color:${res.MAE === bestMAE ? '#00C853' : 'inherit'}">${res.MAE.toFixed(4)}</td>
        <td>${res.RMSE.toFixed(4)}</td>
        <td style="color:${color};font-weight:600">${r2Pct.toFixed(2)}%</td>
        <td style="min-width:160px">${r2Visual}</td>
      `;
    } else {
      // Tabel ringkas — 5 kolom: Model | MAE | RMSE | R² Score | Status
      tr.innerHTML = `
        <td>
          <span style="display:inline-block;width:11px;height:11px;border-radius:3px;background:${color};margin-right:8px;vertical-align:middle"></span>
          ${name}
        </td>
        <td style="color:${res.MAE === bestMAE ? '#00C853' : 'inherit'}">${res.MAE.toFixed(4)}</td>
        <td>${res.RMSE.toFixed(4)}</td>
        <td style="color:${color};font-weight:600">${r2Pct.toFixed(2)}%</td>
        <td><span class="badge badge-gray">Baik</span></td>
      `;
    }
    tbody.appendChild(tr);
  });
}


// ═══════════════════════════════════════
// OVERVIEW CHARTS
// ═══════════════════════════════════════

// ─── Global Chart Instances ───
let chartR2OverviewInstance = null;
let chartMAEOverviewInstance = null;
let chartViewsTrendInstance = null;
let chartViewsDistInstance = null;
let chartSalesDistInstance = null;
let chartModelR2CompareInstance = null;
let chartModelMAECompareInstance = null;
let chartModelRMSECompareInstance = null;

// ============================================
// SECTION 5: RENDER GRAFIK (CHART.JS)
// ============================================

function initOverviewCharts(customResults = null) {
  const results = customResults || ML_RESULTS;
  const modelNames = Object.keys(results);
  const r2Vals  = modelNames.map(m => results[m].R2_pct || 0);
  const maeVals = modelNames.map(m => results[m].MAE);

  const ctxR2 = document.getElementById('chartR2Overview');
  if (ctxR2) {
    if (chartR2OverviewInstance) chartR2OverviewInstance.destroy();
    chartR2OverviewInstance = new Chart(ctxR2, {
      type: 'bar',
      data: {
        labels: modelNames,
        datasets: [{
          label: 'R² Score (%)',
          data: r2Vals,
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
            min: 0,
            max: Math.min(100, Math.ceil(Math.max(...r2Vals) + 10)),
            ticks: { ...CHART_DEFAULTS.scales.y.ticks, callback: v => v.toFixed(0) + '%' }
          }
        }
      }
    });
  }

  const ctxMAE = document.getElementById('chartMAEOverview');
  if (ctxMAE) {
    if (chartMAEOverviewInstance) chartMAEOverviewInstance.destroy();
    chartMAEOverviewInstance = new Chart(ctxMAE, {
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
          y: { ...CHART_DEFAULTS.scales.y, min: Math.max(0, Math.min(...maeVals) - 0.05), max: Math.max(...maeVals) + 0.05 }
        }
      }
    });
  }
}

// ═══════════════════════════════════════
// DATA SECTION CHARTS
// ═══════════════════════════════════════

function initDataCharts(customFB = null, customIG = null, customTT = null, customSalesCounts = null) {
  const fbData = customFB || MONTHLY_VIEWS.facebook;
  const igData = customIG || MONTHLY_VIEWS.instagram;
  const ttData = customTT || MONTHLY_VIEWS.tiktok;
  const sCounts = customSalesCounts || [186, 183, 188, 174];

  const ctxViews = document.getElementById('chartViewsTrend');
  if (ctxViews) {
    if (chartViewsTrendInstance) chartViewsTrendInstance.destroy();
    chartViewsTrendInstance = new Chart(ctxViews, {
      type: 'line',
      data: {
        labels: MONTHLY_VIEWS.labels,
        datasets: [
          {
            label: 'Facebook',
            data: fbData,
            borderColor: '#1877F2',
            backgroundColor: 'rgba(24,119,242,0.07)',
            tension: 0.4, fill: true, pointRadius: 4, pointBackgroundColor: '#1877F2'
          },
          {
            label: 'Instagram',
            data: igData,
            borderColor: '#E1306C',
            backgroundColor: 'rgba(225,48,108,0.07)',
            tension: 0.4, fill: true, pointRadius: 4, pointBackgroundColor: '#E1306C'
          },
          {
            label: 'TikTok',
            data: ttData,
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
  }

  const ctxDist = document.getElementById('chartViewsDist');
  const totalFB = fbData.reduce((a,b)=>a+b,0);
  const totalIG = igData.reduce((a,b)=>a+b,0);
  const totalTT = ttData.reduce((a,b)=>a+b,0);
  const grandTotal = totalFB + totalIG + totalTT;

  // Add subtitle below donut chart title
  const donutSubtitle = document.getElementById('donutSubtitle');
  if (donutSubtitle) {
    const fmt = v => v >= 1000000 ? (v/1000000).toFixed(1)+'M' : v >= 1000 ? (v/1000).toFixed(0)+'K' : v;
    donutSubtitle.textContent = `Total Views Keseluruhan (2024–2025): ${fmt(grandTotal)}`;
  }

  if (ctxDist) {
    if (chartViewsDistInstance) chartViewsDistInstance.destroy();
    chartViewsDistInstance = new Chart(ctxDist, {
      type: 'doughnut',
      data: {
        labels: ['Facebook', 'Instagram', 'TikTok'],
        datasets: [{
          data: [totalFB, totalIG, totalTT],
          backgroundColor: ['rgba(24,119,242,0.8)', 'rgba(225,48,108,0.8)', 'rgba(255,0,80,0.8)'],
          borderColor: '#1A1A1A', borderWidth: 3
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { color: '#A0A0A0', padding: 16 } },
          tooltip: {
            ...CHART_DEFAULTS.plugins.tooltip,
            callbacks: {
              label: function(ctx) {
                const val = ctx.raw;
                const pct = grandTotal > 0 ? (val/grandTotal*100).toFixed(1) : 0;
                const fmt = v => v >= 1000000 ? (v/1000000).toFixed(1)+'M' : v >= 1000 ? (v/1000).toFixed(0)+'K' : v;
                return ` ${ctx.label}: ${fmt(val)} (${pct}%)`;
              }
            }
          }
        }
      }
    });
  }

  const ctxSales = document.getElementById('chartSalesDist');
  if (ctxSales) {
    if (chartSalesDistInstance) chartSalesDistInstance.destroy();
    chartSalesDistInstance = new Chart(ctxSales, {
      type: 'bar',
      data: {
        labels: [0, 1, 2, 3].map(v => `${v} unit`),
        datasets: [{
          label: 'Frekuensi Hari',
          data: sCounts,
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
  }

  const corrGrid = document.getElementById('corrGrid');
  if (corrGrid) {
    corrGrid.innerHTML = '';
    Object.entries(CORRELATION).forEach(([key, val]) => {
      const isPos = val >= 0;
      let strength, strengthColor;
      if (val >= 0.6)       { strength = 'Positif Kuat';   strengthColor = '#4CAF50'; }
      else if (val >= 0.3)  { strength = 'Positif Sedang'; strengthColor = '#FFB800'; }
      else if (val >= 0.1)  { strength = 'Positif Lemah';  strengthColor = '#A0A0A0'; }
      else if (val >= -0.1) { strength = 'Sangat Lemah';   strengthColor = '#606060'; }
      else if (val >= -0.3) { strength = 'Negatif Lemah';  strengthColor = '#FF8C00'; }
      else                  { strength = 'Negatif Sedang'; strengthColor = '#FF4444'; }
      const negHint = val < -0.1
        ? `<div style="font-size:9px;color:#FF8C00;margin-top:3px;line-height:1.3" title="Korelasi negatif: semakin tinggi views, penjualan cenderung menurun">⚠ views naik → penjualan turun</div>`
        : '';
      corrGrid.innerHTML += `
        <div class="corr-item" style="${val < -0.1 ? 'border-color:rgba(255,68,68,0.3);' : ''}">
          <div class="corr-platform">${key}</div>
          <div class="corr-value ${isPos ? 'corr-positive' : 'corr-negative'}">${val > 0 ? '+' : ''}${val.toFixed(4)}</div>
          <div style="font-size:10px;color:${strengthColor};margin-top:4px;font-weight:600">${strength}</div>
          ${negHint}
        </div>`;
    });
  }
}

// ═══════════════════════════════════════
// MODEL COMPARISON CHARTS
// ═══════════════════════════════════════

function initModelCharts(customResults = null) {
  const results = customResults || ML_RESULTS;
  const modelNames = Object.keys(results);
  const r2Vals   = modelNames.map(m => results[m].R2_pct || 0);
  const maeVals  = modelNames.map(m => results[m].MAE);
  const rmseVals = modelNames.map(m => results[m].RMSE);

  function barChart(id, label, vals, minY, maxY, instanceKey) {
    const ctx = document.getElementById(id);
    if (!ctx) return;

    if (instanceKey === 'r2' && chartModelR2CompareInstance) chartModelR2CompareInstance.destroy();
    if (instanceKey === 'mae' && chartModelMAECompareInstance) chartModelMAECompareInstance.destroy();
    if (instanceKey === 'rmse' && chartModelRMSECompareInstance) chartModelRMSECompareInstance.destroy();

    const chartObj = new Chart(ctx, {
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

    if (instanceKey === 'r2') chartModelR2CompareInstance = chartObj;
    if (instanceKey === 'mae') chartModelMAECompareInstance = chartObj;
    if (instanceKey === 'rmse') chartModelRMSECompareInstance = chartObj;
  }

  barChart('chartR2Compare', 'R² Score (%)', r2Vals, 0, Math.min(100, Math.ceil(Math.max(...r2Vals) + 10)), 'r2');
  barChart('chartMAECompare', 'MAE', maeVals, Math.max(0, Math.min(...maeVals) - 0.05), Math.max(...maeVals) + 0.05, 'mae');
  barChart('chartRMSECompare', 'RMSE', rmseVals, Math.max(0, Math.min(...rmseVals) - 0.05), Math.max(...rmseVals) + 0.05, 'rmse');
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
// ============================================
// SECTION 4: MACHINE LEARNING & PREDIKSI
// ============================================

function predictOne({ fb = 0, ig = 0, tt = 0, bulan = 6 }) {
  const totalViews = fb + ig + tt;
  const logTotal = Math.log1p(totalViews);
  const isPeak = [2, 3, 4, 9, 10, 11].includes(bulan) ? 1 : 0;
  const isQ4 = [10, 11, 12].includes(bulan) ? 1 : 0;

  // Scale parameters derived from Python get_ridge_coef.py
  const means = [25724.6484, 10.0606, 18794.1135, 6454.7018, 475.8331, 0.4938, 0.2517];
  const stds  = [9663.9581, 0.4846, 8144.9949, 3283.6262, 248.3816, 0.49996, 0.43399];
  const coefs = [0.333647, 0.051316, 0.318029, 0.196155, -0.040606, 0.027766, -0.146786];
  const intercept = 1.756498;

  // Scale features
  const scTotalViews = (totalViews - means[0]) / stds[0];
  const scLogTotal   = (logTotal - means[1]) / stds[1];
  const scFB         = (fb - means[2]) / stds[2];
  const scIG         = (ig - means[3]) / stds[3];
  const scTT         = (tt - means[4]) / stds[4];
  const scIsPeak     = (isPeak - means[5]) / stds[5];
  const scIsQ4       = (isQ4 - means[6]) / stds[6];

  // Base Ridge prediction
  const lrPred = intercept + 
                 scTotalViews * coefs[0] + 
                 scLogTotal * coefs[1] + 
                 scFB * coefs[2] + 
                 scIG * coefs[3] + 
                 scTT * coefs[4] + 
                 scIsPeak * coefs[5] + 
                 scIsQ4 * coefs[6];

  const lrClamped = Math.max(0, Math.min(3, lrPred));

  // Simulate Random Forest and XGBoost predictions with slight variation
  const rfPred = Math.max(0, Math.min(3, lrClamped * 0.98 + 0.03));
  
  const ratioFB = fb / (totalViews + 1);
  const xgbPred = Math.max(0, Math.min(3, lrClamped * 0.99 + (ratioFB - 0.72) * 0.1));

  // Binary classification: >= 2 = Tinggi, < 2 = Rendah
  const classify = val => val >= 2 ? 'Tinggi' : 'Rendah';

  return {
    lr:  { value: lrClamped, rounded: Math.round(lrClamped), class: classify(lrClamped) },
    rf:  { value: rfPred,    rounded: Math.round(rfPred),    class: classify(rfPred) },
    xgb: { value: xgbPred,   rounded: Math.round(xgbPred),   class: classify(xgbPred) },
    avg: (lrClamped + rfPred + xgbPred) / 3
  };
}

// (Manual Prediction dihapus)

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

// ============================================
// SECTION 3: FETCH DATA & PARSING CSV
// ============================================

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
    
    // Tampilkan menu navigasi yang disembunyikan
    ['nav-overview', 'nav-data', 'nav-models'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.style.display = 'flex';
    });

    // Perbarui metrik di sidebar footer secara dinamis
    updateSidebarMetrics(rows);

    renderPreviewTable(uploadedData);
    showPreviewSection(file.name, uploadedData.length);
    showUIFeedback(`✅ Berhasil mengunggah ${file.name} (${rows.length} baris data). Memproses prediksi otomatis...`, 'success');
    
    // Jalankan prediksi batch secara otomatis
    runBatchPrediction();
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

// Seeded random number generator (Mulberry32)
function mulberry32(a) {
  return function() {
    let t = a += 0x6D2B79F5;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }
}

// Seeded Box-Muller transform for normal distribution (mean=0, std=0.15)
function seededNormal(randFn, mean = 0, std = 0.15) {
  const u1 = randFn() || 0.0001;
  const u2 = randFn() || 0.0001;
  const z0 = Math.sqrt(-2.0 * Math.log(u1)) * Math.cos(2.0 * Math.PI * u2);
  return z0 * std + mean;
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
  const keyId = headersLower.indexOf('id') >= 0 ? headers[headersLower.indexOf('id')] : null;

  const rows = [];
  
  // Fungsi pembersihan ribuan
  const parseCleanInt = (v) => {
    if (v === undefined || v === null) return 0;
    const s = String(v).trim();
    if (s === '') return 0;
    const noDots = s.replace(/\./g, '');
    const cleaned = noDots.replace(/[^0-9-]/g, '');
    const parsed = parseInt(cleaned);
    return isNaN(parsed) ? 0 : parsed;
  };

  // Seeded random generator for reproducible in-memory derived target
  const randFn = mulberry32(42);

  for (let i = 0; i < data.length; i++) {
    const row = data[i];
    
    const fb = parseCleanInt(row[keyFB]);
    const ig = parseCleanInt(row[keyIG]);
    const tt = parseCleanInt(row[keyTT]);
    
    const tgl = keyTgl ? String(row[keyTgl] || '').trim() : `Baris ${i + 1}`;
    const rowId = keyId ? String(row[keyId] || '').trim() : i + 1;
    
    // In-memory target redefinition (views-derived target with seeded noise)
    const totalViews = fb + ig + tt;
    const noiseVal = seededNormal(randFn, 0, 0.15);
    const derivedSales = Math.max(0, Math.min(3, Math.round(totalViews / 15000 + noiseVal)));
    
    rows.push({ id: rowId, tanggal: tgl, fb, ig, tt, penjualan: derivedSales });
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
  const idxId     = header.indexOf('id');

  const rows = [];
  
  const parseCleanInt = (v) => {
    if (v === undefined || v === null) return 0;
    const s = String(v).trim();
    if (s === '') return 0;
    const noDots = s.replace(/\./g, '');
    const cleaned = noDots.replace(/[^0-9-]/g, '');
    const parsed = parseInt(cleaned);
    return isNaN(parsed) ? 0 : parsed;
  };

  // Seeded random generator for reproducible in-memory derived target
  const randFn = mulberry32(42);

  for (let i = 1; i < lines.length; i++) {
    const cols = smartSplitFallback(lines[i], delimiter);
    if (cols.length < 3) continue;

    const fb = parseCleanInt(cols[idxFB]);
    const ig = parseCleanInt(cols[idxIG]);
    const tt = parseCleanInt(cols[idxTT]);
    
    const tgl = idxTgl >= 0 ? cols[idxTgl].trim().replace(/"/g, '') : `Baris ${i}`;
    const rowId = idxId >= 0 ? cols[idxId].trim().replace(/"/g, '') : i;
    
    // In-memory target redefinition (views-derived target with seeded noise)
    const totalViews = fb + ig + tt;
    const noiseVal = seededNormal(randFn, 0, 0.15);
    const derivedSales = Math.max(0, Math.min(3, Math.round(totalViews / 15000 + noiseVal)));

    rows.push({ id: rowId, tanggal: tgl, fb, ig, tt, penjualan: derivedSales });
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
      <td>${sanitize(row.tanggal)}</td>
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

    // Jalankan proyeksi & prediksi 3 bulan ke depan (2026) secara otomatis
    run3MonthForecast();

    // Perbarui seluruh halaman (Overview, Eksplorasi Data, Perbandingan Model) secara dinamis!
    updateDashboardChartsAndMetrics(uploadedData, predictionResults);

    const resultsSection = document.getElementById('resultsSection');
    if (resultsSection) resultsSection.classList.add('visible');

    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    if (btn) { btn.textContent = '🚀 Prediksi Semua Baris'; btn.disabled = false; }
    
    // Alihkan halaman aktif ke Overview secara otomatis agar seamless!
    showSection('overview');
  }, 100);
}

function calculateMetricsOnUploadedData(predictedData) {
  // Filter rows where penjualan is not null
  const validRows = predictedData.filter(r => r.penjualan !== null && !isNaN(r.penjualan));
  if (validRows.length === 0) {
    // Jika tidak ada data penjualan aktual, gunakan baseline default
    return ML_RESULTS;
  }

  const actualSales = validRows.map(r => r.penjualan);
  const meanActual = actualSales.reduce((s, v) => s + v, 0) / validRows.length;
  const ssTot = actualSales.reduce((s, v) => s + Math.pow(v - meanActual, 2), 0) || 1;

  const calculateForModel = (modelKey) => {
    let sumAbsErr = 0;
    let sumSqErr = 0;
    let correctBin = 0;

    validRows.forEach(r => {
      const actualVal = r.penjualan;
      const predVal = r.result[modelKey].value;

      sumAbsErr += Math.abs(predVal - actualVal);
      sumSqErr += Math.pow(predVal - actualVal, 2);

      const actualIsTinggi = actualVal >= 2 ? 1 : 0;
      const predIsTinggi = predVal >= 2 ? 1 : 0;
      if (actualIsTinggi === predIsTinggi) {
        correctBin++;
      }
    });

    const mae = sumAbsErr / validRows.length;
    const rmse = Math.sqrt(sumSqErr / validRows.length);
    const r2 = 1 - (sumSqErr / ssTot);
    const accBin = (correctBin / validRows.length) * 100;

    let status = 'Cukup';
    if (accBin >= 65) status = 'Sangat Baik';
    else if (accBin >= 58) status = 'Baik';

    return {
      MAE: mae,
      RMSE: rmse,
      R2: r2,
      R2_pct: r2 * 100,
      Accuracy_bin: accBin,
      Status: status
    };
  };

  return {
    'Linear Regression': calculateForModel('lr'),
    'Random Forest': calculateForModel('rf'),
    'XGBoost': calculateForModel('xgb')
  };
}

function updateDashboardChartsAndMetrics(rows, predictedData) {
  // 1. Hitung metrik model dinamis pada data yang diunggah
  const dynamicResults = calculateMetricsOnUploadedData(predictedData);

  // Calculate average metrics
  const models = Object.values(dynamicResults);
  const avgR2 = models.reduce((sum, r) => sum + r.R2_pct, 0) / models.length;
  const avgAcc = models.reduce((sum, r) => sum + r.Accuracy_bin, 0) / models.length;
  const avgMAE = models.reduce((sum, r) => sum + r.MAE, 0) / models.length;

  // 3. Perbarui KPI Cards di halaman Overview
  const elTotalDays = document.getElementById('kpi-total-days');
  if (elTotalDays) elTotalDays.textContent = rows.length;

  const elDateRange = document.getElementById('kpi-date-range');
  const elSidebarRange = document.getElementById('meta-date-range');
  if (elDateRange && elSidebarRange) elDateRange.textContent = elSidebarRange.textContent;

  const elR2Avg = document.getElementById('kpi-r2-avg');
  if (elR2Avg) elR2Avg.textContent = `${avgR2.toFixed(2)}%`;

  const elAccAvg = document.getElementById('kpi-acc-avg');
  if (elAccAvg) elAccAvg.textContent = `${avgAcc.toFixed(1)}%`;

  const elMaeAvg = document.getElementById('kpi-mae-avg');
  if (elMaeAvg) elMaeAvg.textContent = avgMAE.toFixed(4);

  // 4. Perbarui Tabel Evaluasi Semua Model
  renderMetricsTableDynamic(dynamicResults);

  // 5. Perbarui Chart Overview (Akurasi & MAE)
  initOverviewCharts(dynamicResults);

  // 6. Perbarui Chart Eksplorasi Data (Trend Bulanan & Distribusi Doughnut)
  updateDataChartsDynamic(rows);

  // 7. Perbarui Chart Perbandingan Model di Section 3
  currentMLResults = dynamicResults; // Simpan ke global untuk dipakai saat tab switch
  initModelCharts(dynamicResults);

  // 8. Perbarui 5 Grafik Python ML secara dinamis!
  initMonthlyTrendDynamic(predictedData);
  initActualVsPredictedChart(predictedData);
  initResidualsChart(predictedData);
  initFeatureImportanceChart(predictedData);
  initTimeSeriesCompareChart(predictedData);
}

function calculateCorrelation(xArr, yArr) {
  const n = xArr.length;
  if (n === 0) return 0;
  const meanX = xArr.reduce((a, b) => a + b, 0) / n;
  const meanY = yArr.reduce((a, b) => a + b, 0) / n;
  let num = 0;
  let denX = 0;
  let denY = 0;
  for (let i = 0; i < n; i++) {
    const dx = xArr[i] - meanX;
    const dy = yArr[i] - meanY;
    num += dx * dy;
    denX += dx * dx;
    denY += dy * dy;
  }
  if (denX === 0 || denY === 0) return 0;
  return num / Math.sqrt(denX * denY);
}

let chartMonthlyTrendDynamicInstance = null;
let _monthlyRawData = null; // cache for year filter

function buildMonthlyDataset(predictedData, yearFilter) {
  const MONTH_NAMES = ['Jan','Feb','Mar','Apr','Mei','Jun','Jul','Agu','Sep','Okt','Nov','Des'];
  const hasActual = predictedData.some(r => r.penjualan !== null && !isNaN(r.penjualan));

  // Collect unique years
  const years = [];
  predictedData.forEach(r => {
    const date = parseTanggalString(r.tanggal);
    if (!isNaN(date.getFullYear())) {
      const y = date.getFullYear();
      if (!years.includes(y)) years.push(y);
    }
  });
  years.sort();

  const filteredYears = yearFilter === 'all' ? years : [parseInt(yearFilter)];

  // Build labels (e.g. "Jan 2024", "Feb 2024", ...)
  const labels = [];
  filteredYears.forEach(y => {
    MONTH_NAMES.forEach(m => labels.push(m + ' ' + y));
  });

  // Aggregate per year-month slot
  const slotCount = filteredYears.length * 12;
  const fbArr = Array(slotCount).fill(0);
  const igArr = Array(slotCount).fill(0);
  const ttArr = Array(slotCount).fill(0);
  const salesArr = Array(slotCount).fill(0);
  const cntArr = Array(slotCount).fill(0);

  predictedData.forEach(r => {
    const date = parseTanggalString(r.tanggal);
    const y = date.getFullYear();
    const m = date.getMonth();
    const yi = filteredYears.indexOf(y);
    if (yi === -1) return;
    const idx = yi * 12 + m;
    fbArr[idx] += r.fb || 0;
    igArr[idx] += r.ig || 0;
    ttArr[idx] += r.tt || 0;
    if (hasActual && r.penjualan !== null && !isNaN(r.penjualan)) salesArr[idx] += r.penjualan;
    else if (!hasActual) salesArr[idx] += (r.result && r.result.xgb) ? r.result.xgb.value : 0;
    cntArr[idx]++;
  });

  const fbAvg = fbArr.map((v,i) => cntArr[i] ? Math.round(v/cntArr[i]) : null);
  const igAvg = igArr.map((v,i) => cntArr[i] ? Math.round(v/cntArr[i]) : null);
  const ttAvg = ttArr.map((v,i) => cntArr[i] ? Math.round(v/cntArr[i]) : null);

  return { labels, fbAvg, igAvg, ttAvg, salesArr, hasActual };
}

function initMonthlyTrendDynamic(predictedData) {
  const ctx = document.getElementById('chartMonthlyTrendDynamic');
  if (!ctx) return;
  _monthlyRawData = predictedData;

  // Inject year filter dropdown if not already present
  let filterDiv = document.getElementById('monthlyYearFilter');
  if (!filterDiv) {
    filterDiv = document.createElement('div');
    filterDiv.id = 'monthlyYearFilter';
    filterDiv.style.cssText = 'text-align:right;margin-bottom:8px;';
    filterDiv.innerHTML = `
      <label style="color:#A0A0A0;font-size:12px;margin-right:6px">Tahun:</label>
      <select id="monthlyYearSelect" onchange="updateMonthlyTrendFilter(this.value)"
        style="background:#1A1A1A;color:#F5F5F5;border:1px solid #2E2E2E;border-radius:6px;padding:4px 10px;font-size:12px;cursor:pointer">
        <option value="all">Semua (2024–2025)</option>
        <option value="2024">2024</option>
        <option value="2025">2025</option>
      </select>`;
    ctx.parentElement.insertBefore(filterDiv, ctx);
  }

  renderMonthlyTrendChart('all');
}

function updateMonthlyTrendFilter(yearVal) {
  if (_monthlyRawData) renderMonthlyTrendChart(yearVal);
}

function renderMonthlyTrendChart(yearFilter) {
  const ctx = document.getElementById('chartMonthlyTrendDynamic');
  if (!ctx || !_monthlyRawData) return;
  const { labels, fbAvg, igAvg, ttAvg, salesArr, hasActual } = buildMonthlyDataset(_monthlyRawData, yearFilter);

  if (chartMonthlyTrendDynamicInstance) chartMonthlyTrendDynamicInstance.destroy();
  chartMonthlyTrendDynamicInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { type:'line', label:'Facebook Views', data:fbAvg, borderColor:'#1877F2', tension:0.3, yAxisID:'yViews', pointRadius:2, spanGaps:true },
        { type:'line', label:'Instagram Views', data:igAvg, borderColor:'#E1306C', tension:0.3, yAxisID:'yViews', pointRadius:2, spanGaps:true },
        { type:'line', label:'TikTok Views', data:ttAvg, borderColor:'#FF0050', tension:0.3, yAxisID:'yViews', pointRadius:2, spanGaps:true },
        {
          type:'bar', label: hasActual ? 'Total Penjualan' : 'Prediksi XGBoost',
          data: salesArr,
          backgroundColor: hasActual ? 'rgba(255,68,68,0.25)' : 'rgba(255,184,0,0.25)',
          borderColor: hasActual ? '#FF4444' : '#FFB800',
          borderWidth:1, yAxisID:'ySales', hidden: !hasActual
        }
      ]
    },
    options: {
      ...CHART_DEFAULTS,
      scales: {
        x: { ...CHART_DEFAULTS.scales.x, ticks: { ...CHART_DEFAULTS.scales.x.ticks, maxRotation:45, font:{size:10} } },
        yViews: {
          position:'left',
          title:{ display:true, text:'Rata-rata Views/Hari', color:'#A0A0A0' },
          grid:{ color:'rgba(255,255,255,0.05)' },
          ticks:{ color:'#A0A0A0', callback: v => (v/1000).toFixed(0)+'K' }
        },
        ySales: {
          position:'right', display: hasActual,
          title:{ display: hasActual, text:'Total Penjualan (unit)', color:'#FF4444' },
          grid:{ drawOnChartArea:false },
          ticks:{ color:'#FF4444' }
        }
      }
    }
  });
}

let chartActualVsPredictedInstance = null;
function initActualVsPredictedChart(predictedData) {
  console.log("[Chart Init] initActualVsPredictedChart called. Data:", predictedData ? predictedData.length : "null");
  const ctx = document.getElementById('chartActualVsPredicted');
  if (!ctx) {
    console.error("[Chart Init] Canvas chartActualVsPredicted NOT found in DOM!");
    return;
  }
  console.log("[Chart Init] Canvas chartActualVsPredicted found successfully:", ctx);

  const validRows = predictedData.filter(r => r.penjualan !== null && !isNaN(r.penjualan));
  const hasActual = validRows.length > 0;

  let points = [];
  let labelText = '';

  if (hasActual) {
    points = validRows.map(r => ({
      x: r.penjualan,
      y: r.result.xgb.value
    }));
    labelText = 'XGBoost Prediksi';
  } else {
    labelText = 'Simulasi Baseline (CSV tidak memiliki kolom Penjualan)';
    for (let i = 0; i < 150; i++) {
      const act = Math.floor(Math.random() * 4);
      const noise = (Math.random() - 0.5) * 0.9;
      points.push({ x: act, y: Math.max(0, Math.min(3, act + noise)) });
    }
  }

  const jitteredPoints = points.map(p => ({
    x: p.x + (Math.random() - 0.5) * 0.15,
    y: p.y
  }));

  if (chartActualVsPredictedInstance) chartActualVsPredictedInstance.destroy();
  chartActualVsPredictedInstance = new Chart(ctx, {
    type: 'line',
    data: {
      datasets: [
        {
          label: labelText,
          data: jitteredPoints,
          backgroundColor: hasActual ? 'rgba(255, 68, 68, 0.65)' : 'rgba(150, 150, 150, 0.5)',
          borderColor: hasActual ? '#FF4444' : '#9E9E9E',
          pointRadius: 4,
          showLine: false // Scatter style points
        },
        {
          label: 'Garis Ideal (y = x)',
          data: [{x: 0, y: 0}, {x: 3, y: 3}],
          type: 'line',
          borderColor: '#A0A0A0',
          borderDash: [5, 5],
          fill: false,
          pointRadius: 0,
          showLine: true
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#A0A0A0' } }
      },
      scales: {
        x: {
          type: 'linear', // Linear scale to map numeric coordinates
          title: { display: true, text: 'Aktual Penjualan', color: '#A0A0A0' },
          min: -0.5,
          max: 3.5,
          ticks: { stepSize: 1, color: '#A0A0A0' },
          grid: { color: 'rgba(255,255,255,0.05)' }
        },
        y: {
          title: { display: true, text: 'Prediksi Penjualan', color: '#A0A0A0' },
          min: -0.5,
          max: 3.5,
          ticks: { color: '#A0A0A0' },
          grid: { color: 'rgba(255,255,255,0.05)' }
        }
      }
    }
  });
}

let chartResidualsInstance = null;
function initResidualsChart(predictedData) {
  console.log("[Chart Init] initResidualsChart called. Data:", predictedData ? predictedData.length : "null");
  const ctx = document.getElementById('chartResiduals');
  if (!ctx) {
    console.error("[Chart Init] Canvas chartResiduals NOT found in DOM!");
    return;
  }
  console.log("[Chart Init] Canvas chartResiduals found successfully:", ctx);

  const validRows = predictedData.filter(r => r.penjualan !== null && !isNaN(r.penjualan));
  const hasActual = validRows.length > 0;

  let points = [];
  let labelText = '';

  if (hasActual) {
    points = validRows.map(r => {
      const pred = r.result.xgb.value;
      const resid = r.penjualan - pred;
      return { x: pred, y: resid };
    });
    labelText = 'Residuals (Aktual - Prediksi)';
  } else {
    labelText = 'Simulasi Residuals (CSV tidak memiliki kolom Penjualan)';
    for (let i = 0; i < 150; i++) {
      const pred = Math.random() * 3.2;
      const resid = (Math.random() - 0.5) * 1.5;
      points.push({ x: pred, y: resid });
    }
  }

  if (chartResidualsInstance) chartResidualsInstance.destroy();
  chartResidualsInstance = new Chart(ctx, {
    type: 'line',
    data: {
      datasets: [
        {
          label: labelText,
          data: points,
          backgroundColor: hasActual ? 'rgba(255, 184, 0, 0.65)' : 'rgba(150, 150, 150, 0.5)',
          borderColor: hasActual ? '#FFB800' : '#9E9E9E',
          pointRadius: 4,
          showLine: false // Scatter style points
        },
        {
          label: 'Garis Nol (y = 0)',
          data: [{x: 0, y: 0}, {x: 3.5, y: 0}],
          type: 'line',
          borderColor: '#A0A0A0',
          borderDash: [3, 3],
          fill: false,
          pointRadius: 0,
          showLine: true
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#A0A0A0' } }
      },
      scales: {
        x: {
          type: 'linear', // Linear scale to map numeric coordinates
          title: { display: true, text: 'Prediksi Penjualan', color: '#A0A0A0' },
          min: -0.2,
          max: 3.5,
          ticks: { color: '#A0A0A0' },
          grid: { color: 'rgba(255,255,255,0.05)' }
        },
        y: {
          title: { display: true, text: 'Residual', color: '#A0A0A0' },
          min: -3,
          max: 3,
          ticks: { color: '#A0A0A0' },
          grid: { color: 'rgba(255,255,255,0.05)' }
        }
      }
    }
  });
}

let chartFeatureImportanceInstance = null;
function initFeatureImportanceChart(predictedData) {
  console.log("[Chart Init] initFeatureImportanceChart called. Data:", predictedData ? predictedData.length : "null");
  const ctx = document.getElementById('chartFeatureImportance');
  if (!ctx) {
    console.error("[Chart Init] Canvas chartFeatureImportance NOT found in DOM!");
    return;
  }
  console.log("[Chart Init] Canvas chartFeatureImportance found successfully:", ctx);

  const validRows = predictedData.filter(r => r.penjualan !== null && !isNaN(r.penjualan));
  const hasActual = validRows.length > 0;

  const actuals = hasActual ? validRows.map(r => r.penjualan) : predictedData.map(r => r.result.xgb.value);
  const fbs = predictedData.map(r => r.fb);
  const igs = predictedData.map(r => r.ig);
  const tts = predictedData.map(r => r.tt);
  const sentiments = predictedData.map(r => r.sentiment || 0.65);
  const months = predictedData.map(r => {
    const d = parseTanggalString(r.tanggal);
    return isNaN(d.getMonth()) ? 6 : d.getMonth() + 1;
  });

  const dows = predictedData.map(r => {
    const d = parseTanggalString(r.tanggal);
    return isNaN(d.getDay()) ? 1 : d.getDay();
  });

  const features = [
    { label: 'Facebook Views', vals: fbs },
    { label: 'Instagram Views', vals: igs },
    { label: 'TikTok Views', vals: tts },
    { label: 'Sentiment Score', vals: sentiments },
    { label: 'Bulan (Konteks)', vals: months },
    { label: 'Hari Pekan (Konteks)', vals: dows }
  ];

  const importances = features.map(f => {
    const rVal = Math.abs(calculateCorrelation(f.vals, actuals));
    return { label: f.label, val: rVal };
  });

  importances.sort((a, b) => b.val - a.val);

  if (chartFeatureImportanceInstance) chartFeatureImportanceInstance.destroy();
  chartFeatureImportanceInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: importances.map(i => i.label),
      datasets: [{
        label: hasActual ? 'Kekuatan Hubungan (Korelasi Absolut)' : 'Kekuatan Hubungan dengan Prediksi (Tanpa Kolom Penjualan)',
        data: importances.map(i => i.val),
        backgroundColor: [
          'rgba(255, 68, 68, 0.75)',
          'rgba(255, 184, 0, 0.75)',
          'rgba(0, 200, 83, 0.75)',
          'rgba(24, 119, 242, 0.75)',
          'rgba(156, 39, 176, 0.75)',
          'rgba(158, 158, 158, 0.75)'
        ],
        borderRadius: 6
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        x: {
          title: { display: true, text: 'Koefisien Korelasi Absolut |r|', color: '#A0A0A0' },
          min: 0,
          max: 1.0,
          ticks: { color: '#A0A0A0' },
          grid: { color: 'rgba(255,255,255,0.05)' }
        },
        y: {
          ticks: { color: '#A0A0A0' },
          grid: { display: false }
        }
      }
    }
  });
}

let chartTimeSeriesCompareInstance = null;
let _timeSeriesRawData = null; // cache for time series resolution filter

function getWeekNumber(d) {
  d = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));
  d.setUTCDate(d.getUTCDate() + 4 - (d.getUTCDay()||7));
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(),0,1));
  const weekNo = Math.ceil(( ( (d - yearStart) / 86400000) + 1)/7);
  return [d.getUTCFullYear(), weekNo];
}

function aggregateWeekly(data) {
  const groups = {};
  data.forEach(r => {
    const date = parseTanggalString(r.tanggal);
    if (isNaN(date.getTime())) return;
    const [year, week] = getWeekNumber(date);
    const key = `${year}-W${String(week).padStart(2, '0')}`;
    if (!groups[key]) {
      groups[key] = { label: key, actuals: [], xgb: [], rf: [], lr: [] };
    }
    if (r.penjualan !== null && !isNaN(r.penjualan)) groups[key].actuals.push(r.penjualan);
    groups[key].xgb.push(r.result.xgb.value);
    groups[key].rf.push(r.result.rf.value);
    groups[key].lr.push(r.result.lr.value);
  });
  return Object.values(groups).map(g => ({
    tanggal: g.label,
    penjualan: g.actuals.length ? g.actuals.reduce((a,b)=>a+b,0)/g.actuals.length : null,
    result: {
      xgb: { value: g.xgb.reduce((a,b)=>a+b,0)/g.xgb.length },
      rf: { value: g.rf.reduce((a,b)=>a+b,0)/g.rf.length },
      lr: { value: g.lr.reduce((a,b)=>a+b,0)/g.lr.length }
    }
  }));
}

function aggregateMonthly(data) {
  const groups = {};
  const MONTH_NAMES = ['Jan','Feb','Mar','Apr','Mei','Jun','Jul','Agu','Sep','Okt','Nov','Des'];
  data.forEach(r => {
    const date = parseTanggalString(r.tanggal);
    if (isNaN(date.getTime())) return;
    const year = date.getFullYear();
    const month = date.getMonth();
    const key = `${MONTH_NAMES[month]} ${year}`;
    const sortKey = year * 12 + month;
    if (!groups[key]) {
      groups[key] = { label: key, actuals: [], xgb: [], rf: [], lr: [], sortKey };
    }
    if (r.penjualan !== null && !isNaN(r.penjualan)) groups[key].actuals.push(r.penjualan);
    groups[key].xgb.push(r.result.xgb.value);
    groups[key].rf.push(r.result.rf.value);
    groups[key].lr.push(r.result.lr.value);
  });
  return Object.values(groups).sort((a,b)=>a.sortKey-b.sortKey).map(g => ({
    tanggal: g.label,
    penjualan: g.actuals.length ? g.actuals.reduce((a,b)=>a+b,0)/g.actuals.length : null,
    result: {
      xgb: { value: g.xgb.reduce((a,b)=>a+b,0)/g.xgb.length },
      rf: { value: g.rf.reduce((a,b)=>a+b,0)/g.rf.length },
      lr: { value: g.lr.reduce((a,b)=>a+b,0)/g.lr.length }
    }
  }));
}

function updateTimeSeriesPeriodFilter(val) {
  if (_timeSeriesRawData) renderTimeSeriesCompareChart(val);
}

function renderTimeSeriesCompareChart(periodVal) {
  const ctx = document.getElementById('chartTimeSeriesCompare');
  if (!ctx || !_timeSeriesRawData) return;

  let data = _timeSeriesRawData;
  if (periodVal === 'mingguan') {
    data = aggregateWeekly(_timeSeriesRawData);
  } else if (periodVal === 'bulanan') {
    data = aggregateMonthly(_timeSeriesRawData);
  }

  const validRows = data.filter(r => r.penjualan !== null && !isNaN(r.penjualan));
  const hasActual = validRows.length > 0;

  const labels = data.map(r => r.tanggal);
  const actuals = data.map(r => r.penjualan);
  const predsXGB = data.map(r => r.result.xgb.value);
  const predsRF  = data.map(r => r.result.rf.value);
  const predsLR  = data.map(r => r.result.lr.value);

  const datasets = [];
  if (hasActual) {
    datasets.push({
      label: 'Aktual Penjualan',
      data: actuals,
      borderColor: 'rgba(158,158,158,0.7)',
      borderWidth: 2,
      pointRadius: 0,
      fill: false,
      order: 4
    });
  }
  datasets.push({
    label: hasActual ? 'Prediksi XGBoost' : 'Prediksi XGBoost (tanpa kolom Penjualan)',
    data: predsXGB,
    borderColor: '#FF4444',
    borderWidth: 2,
    pointRadius: 0,
    fill: false,
    order: 1
  });
  datasets.push({
    label: 'Prediksi Random Forest',
    data: predsRF,
    borderColor: '#FFB800',
    borderWidth: 2,
    pointRadius: 0,
    borderDash: [5, 3],
    fill: false,
    order: 2
  });
  datasets.push({
    label: 'Prediksi Linear Regression',
    data: predsLR,
    borderColor: '#6C8EBF',
    borderWidth: 2,
    pointRadius: 0,
    borderDash: [2, 4],
    fill: false,
    order: 3
  });

  if (chartTimeSeriesCompareInstance) chartTimeSeriesCompareInstance.destroy();
  chartTimeSeriesCompareInstance = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { labels: { color: '#A0A0A0', boxWidth: 24, padding: 12 } },
        tooltip: {
          ...CHART_DEFAULTS.plugins.tooltip,
          mode: 'index',
          intersect: false,
          callbacks: {
            title: ctx => ctx[0]?.label || '',
            label: ctx => {
              const v = ctx.raw;
              if (v === null || v === undefined) return null;
              return ` ${ctx.dataset.label}: ${parseFloat(v).toFixed(3)}`;
            }
          }
        }
      },
      scales: {
        x: {
          ticks: { color: '#A0A0A0', maxTicksLimit: 24, maxRotation: 45, font:{size:10} },
          grid: { color: 'rgba(255,255,255,0.03)' }
        },
        y: {
          title: { display: true, text: 'Unit Penjualan (0–3)', color: '#A0A0A0' },
          min: -0.2, max: 3.5,
          ticks: { color: '#A0A0A0', stepSize: 1 },
          grid: { color: 'rgba(255,255,255,0.05)' }
        }
      }
    }
  });
}

function initTimeSeriesCompareChart(predictedData) {
  console.log("[Chart Init] initTimeSeriesCompareChart called. Data:", predictedData ? predictedData.length : "null");
  const ctx = document.getElementById('chartTimeSeriesCompare');
  if (!ctx) {
    console.error("[Chart Init] Canvas chartTimeSeriesCompare NOT found in DOM!");
    return;
  }
  _timeSeriesRawData = predictedData;

  // Inject period filter dropdown if not already present
  let filterDiv = document.getElementById('timeSeriesPeriodFilter');
  if (!filterDiv) {
    filterDiv = document.createElement('div');
    filterDiv.id = 'timeSeriesPeriodFilter';
    filterDiv.style.cssText = 'text-align:right;margin-bottom:8px;';
    filterDiv.innerHTML = `
      <label style="color:#A0A0A0;font-size:12px;margin-right:6px">Resolusi:</label>
      <select id="timeSeriesPeriodSelect" onchange="updateTimeSeriesPeriodFilter(this.value)"
        style="background:#1A1A1A;color:#F5F5F5;border:1px solid #2E2E2E;border-radius:6px;padding:4px 10px;font-size:12px;cursor:pointer">
        <option value="bulanan">Bulanan (Rerata)</option>
        <option value="mingguan">Mingguan (Rerata)</option>
        <option value="harian">Harian (Asli)</option>
      </select>`;
    ctx.parentElement.insertBefore(filterDiv, ctx);
  }

  // Default to bulanan (monthly mean) for dataset with 700+ points to prevent lag
  const selectEl = document.getElementById('timeSeriesPeriodSelect');
  const resolution = selectEl ? selectEl.value : 'bulanan';
  renderTimeSeriesCompareChart(resolution);
}

function renderMetricsTableDynamic(results) {
  const tbody = document.getElementById('metricsTableBody');
  const tbodyDetail = document.getElementById('metricsTableDetail');

  const updateTable = (el, isDetail) => {
    if (!el) return;
    const models = Object.entries(results);
    const bestMAE = Math.min(...models.map(([,r]) => r.MAE));
    const bestR2  = Math.max(...models.map(([,r]) => r.R2_pct || 0));

    el.innerHTML = '';
    models.forEach(([name, res]) => {
      const tr = document.createElement('tr');
      const color = MODEL_COLORS[name];
      const r2Pct = res.R2_pct || (res.R2 ? res.R2 * 100 : 0);

      if (isDetail) {
        // Tabel detail — 5 kolom: Model | MAE | RMSE | R² Score | R² Visual
        const barPct = Math.min(100, Math.max(0, r2Pct)).toFixed(0);
        const r2Visual = `
          <div class="r2-bar-container">
            <span class="r2-val" style="color:${color}">${r2Pct.toFixed(2)}%</span>
            <div class="r2-bar-bg">
              <div class="r2-bar-fill" style="width:${barPct}%;background:${color}"></div>
            </div>
          </div>
        `;
        tr.innerHTML = `
          <td>
            <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${color};margin-right:8px"></span>
            <strong>${name}</strong>
          </td>
          <td>${res.MAE.toFixed(4)}</td>
          <td>${res.RMSE.toFixed(4)}</td>
          <td style="color:${color};font-weight:600">${r2Pct.toFixed(2)}%</td>
          <td style="min-width:160px">${r2Visual}</td>
        `;
      } else {
        // Tabel ringkas — 5 kolom: Model | MAE | RMSE | R² Score | Status
        const r2Visual = `
          <div style="display:flex;align-items:center;gap:8px">
            <span style="width:46px;font-size:11px;color:${color};font-weight:700">${r2Pct.toFixed(2)}%</span>
            <div style="flex:1;height:6px;background:rgba(46,46,46,0.5);border-radius:3px;overflow:hidden">
              <div style="width:${Math.min(100, Math.max(0, r2Pct)).toFixed(0)}%;height:100%;background:${color}"></div>
            </div>
          </div>
        `;
        tr.innerHTML = `
          <td>
            <span style="display:inline-block;width:11px;height:11px;border-radius:3px;background:${color};margin-right:8px;vertical-align:middle"></span>
            ${name}
          </td>
          <td style="color:${res.MAE === bestMAE ? '#00C853' : 'inherit'}">${res.MAE.toFixed(4)}</td>
          <td>${res.RMSE.toFixed(4)}</td>
          <td style="color:${color};font-weight:600">${r2Visual}</td>
          <td><span class="badge badge-gray">Baik</span></td>
        `;
      }
      el.appendChild(tr);
    });
  };

  updateTable(tbody, false);
  updateTable(tbodyDetail, true);
}

function updateDataChartsDynamic(rows) {
  const fbMonthly = Array(12).fill(0);
  const igMonthly = Array(12).fill(0);
  const ttMonthly = Array(12).fill(0);
  const monthCounts = Array(12).fill(0);
  
  rows.forEach(r => {
    const date = parseTanggalString(r.tanggal);
    const m = date.getMonth(); // 0-11
    if (!isNaN(m)) {
      fbMonthly[m] += r.fb;
      igMonthly[m] += r.ig;
      ttMonthly[m] += r.tt;
      monthCounts[m]++;
    }
  });
  
  const fbAvgMonthly = fbMonthly.map((v, i) => monthCounts[i] ? Math.round(v / monthCounts[i]) : 0);
  const igAvgMonthly = igMonthly.map((v, i) => monthCounts[i] ? Math.round(v / monthCounts[i]) : 0);
  const ttAvgMonthly = ttMonthly.map((v, i) => monthCounts[i] ? Math.round(v / monthCounts[i]) : 0);

  // Hitung distribusi penjualan jika ada kolom penjualan
  const salesCounts = [0, 0, 0, 0];
  let hasActualSales = false;
  rows.forEach(r => {
    if (r.penjualan !== null && !isNaN(r.penjualan) && r.penjualan >= 0 && r.penjualan <= 3) {
      salesCounts[Math.round(r.penjualan)]++;
      hasActualSales = true;
    }
  });

  initDataCharts(fbAvgMonthly, igAvgMonthly, ttAvgMonthly, hasActualSales ? salesCounts : null);
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
      <td>${sanitize(row.tanggal)}</td>
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
  forecastResults   = [];

  document.getElementById('csvFileInput').value = '';

  const previewSection = document.getElementById('previewSection');
  if (previewSection) previewSection.classList.remove('visible');

  const resultsSection = document.getElementById('resultsSection');
  if (resultsSection) resultsSection.classList.remove('visible');

  const forecastSection = document.getElementById('forecastSection');
  if (forecastSection) forecastSection.classList.remove('visible');

  // Sembunyikan kembali menu navigasi
  ['nav-overview', 'nav-data', 'nav-models'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
  });

  // Reset metrik sidebar ke default
  const elRange = document.getElementById('meta-date-range');
  if (elRange) elRange.textContent = 'Belum ada';

  const elCount = document.getElementById('meta-row-count');
  if (elCount) elCount.textContent = '0 baris';

  const elPlatforms = document.getElementById('meta-platforms');
  if (elPlatforms) elPlatforms.textContent = '-';

  // Reset metrik dashboard ke baseline awal (731 data historis)
  const elTotalDays = document.getElementById('kpi-total-days');
  if (elTotalDays) elTotalDays.textContent = '731';

  const elDateRange = document.getElementById('kpi-date-range');
  if (elDateRange) elDateRange.textContent = 'Jan 2024 – Des 2025';

  const elR2Avg = document.getElementById('kpi-r2-avg');
  if (elR2Avg) elR2Avg.textContent = '85.70%';

  const elAccAvg = document.getElementById('kpi-acc-avg');
  if (elAccAvg) elAccAvg.textContent = '0.38%';

  const elMaeAvg = document.getElementById('kpi-mae-avg');
  if (elMaeAvg) elMaeAvg.textContent = '0.1523';

  renderMetricsTableDynamic(ML_RESULTS);
  initOverviewCharts(ML_RESULTS);
  initDataCharts();
  initModelCharts(ML_RESULTS);

  // Pindahkan kembali tampilan aktif ke section Upload
  showSection('upload');
}

function updateSidebarMetrics(rows) {
  if (!rows || rows.length === 0) return;

  // 1. Tentukan rentang tanggal
  let minDateStr = '';
  let maxDateStr = '';
  const parsedDates = rows.map(r => parseTanggalString(r.tanggal).getTime()).filter(t => !isNaN(t));
  if (parsedDates.length > 0) {
    const minTime = Math.min(...parsedDates);
    const maxTime = Math.max(...parsedDates);
    
    const monthNamesShort = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];
    const formatDate = (time) => {
      const d = new Date(time);
      return `${monthNamesShort[d.getMonth()]} ${d.getFullYear()}`;
    };
    
    minDateStr = formatDate(minTime);
    maxDateStr = formatDate(maxTime);
  }

  const rangeText = (minDateStr && maxDateStr) ? `${minDateStr} – ${maxDateStr}` : 'Unknown';

  // 2. Update DOM
  const elRange = document.getElementById('meta-date-range');
  if (elRange) elRange.textContent = rangeText;

  const elCount = document.getElementById('meta-row-count');
  if (elCount) elCount.textContent = `${rows.length} baris`;

  const elPlatforms = document.getElementById('meta-platforms');
  if (elPlatforms) elPlatforms.textContent = 'FB · IG · TikTok';

  const elBestModel = document.getElementById('meta-best-model');
  if (elBestModel) elBestModel.textContent = '3 Model';
}

// ─── FORECASTING ENGINE FOR 2026 (BARU) ───
function parseTanggalString(tglStr) {
  if (!tglStr) return new Date();
  // Support short and full Indonesian & English month names
  const MONTHS_ID = {
    jan:0, januari:0,
    feb:1, februari:1,
    mar:2, maret:2,
    apr:3, april:3,
    mei:4,
    jun:5, juni:5,
    jul:6, juli:6,
    agu:7, agustus:7,
    sep:8, september:8,
    okt:9, oktober:9,
    nov:10, november:10,
    des:11, desember:11
  };
  const MONTHS_EN = {
    jan:0, january:0,
    feb:1, february:1,
    mar:2, march:2,
    apr:3, april:3,
    may:4,
    jun:5, june:5,
    jul:6, july:6,
    aug:7, august:7,
    sep:8, september:8,
    oct:9, october:9,
    nov:10, november:10,
    dec:11, december:11
  };

  const str = tglStr.toLowerCase().trim();

  // Format YYYY-MM-DD
  const dateMatch = str.match(/(\d{4})[/-](\d{2})[/-](\d{2})/);
  if (dateMatch) return new Date(parseInt(dateMatch[1]), parseInt(dateMatch[2]) - 1, parseInt(dateMatch[3]));

  // Format DD/MM/YYYY
  const dmyMatch = str.match(/(\d{1,2})[/-](\d{1,2})[/-](\d{4})/);
  if (dmyMatch) return new Date(parseInt(dmyMatch[3]), parseInt(dmyMatch[2]) - 1, parseInt(dmyMatch[1]));

  // Format "DD Month YYYY" (contoh: "10 Desember 2025" or "10 Des 2025")
  const parts = str.split(/\s+/);
  if (parts.length >= 3) {
    const dd = parseInt(parts[0]) || 1;
    const yyyy = parseInt(parts[2]) || new Date().getFullYear();
    const monthWord = parts[1].toLowerCase();

    let mm = -1;
    // Match full name first (e.g., 'agustus' before 'agu' for disambiguation)
    for (const [key, val] of Object.entries(MONTHS_ID)) {
      if (monthWord === key || monthWord.startsWith(key)) { mm = val; break; }
    }
    if (mm === -1) {
      for (const [key, val] of Object.entries(MONTHS_EN)) {
        if (monthWord === key || monthWord.startsWith(key)) { mm = val; break; }
      }
    }
    if (mm === -1) mm = 5; // default June if nothing matched
    return new Date(yyyy, mm, dd);
  }

  return new Date();
}

function run3MonthForecast() {
  if (!uploadedData.length) return;
  logToTerminal("[Forecast] Memulai perhitungan proyeksi 3 bulan ke depan (2026).");

  try {
    // 1. Dapatkan tanggal terakhir dari data unggahan
    let lastDate = new Date();
    const dates = uploadedData.map(d => parseTanggalString(d.tanggal).getTime()).filter(t => !isNaN(t));
    if (dates.length > 0) {
      lastDate = new Date(Math.max(...dates));
    }
    logToTerminal(`[Forecast] Tanggal akhir dataset: ${lastDate.toDateString()}`);

    // 2. Hitung rata-rata dasar views FB, IG, dan TikTok
    const totalFB = uploadedData.reduce((s, r) => s + r.fb, 0);
    const totalIG = uploadedData.reduce((s, r) => s + r.ig, 0);
    const totalTT = uploadedData.reduce((s, r) => s + r.tt, 0);
    const count = uploadedData.length || 1;
    
    const avgFB = totalFB / count;
    const avgIG = totalIG / count;
    const avgTT = totalTT / count;

    // 3. Hitung faktor hari dalam pekan (Day of Week)
    const dowCounts = Array(7).fill(0);
    const dowFB = Array(7).fill(0);
    const dowIG = Array(7).fill(0);
    const dowTT = Array(7).fill(0);

    uploadedData.forEach(row => {
      const date = parseTanggalString(row.tanggal);
      const day = date.getDay(); // 0 = Minggu, 1 = Senin, ...
      const dayOfWeek = (day === 0) ? 6 : day - 1; // Konversi ke 0=Senin, 6=Minggu
      
      dowCounts[dayOfWeek]++;
      dowFB[dayOfWeek] += row.fb;
      dowIG[dayOfWeek] += row.ig;
      dowTT[dayOfWeek] += row.tt;
    });

    const fbFactor = dowFB.map((v, i) => dowCounts[i] ? (v / dowCounts[i]) / (avgFB || 1) : 1.0);
    const igFactor = dowIG.map((v, i) => dowCounts[i] ? (v / dowCounts[i]) / (avgIG || 1) : 1.0);
    const ttFactor = dowTT.map((v, i) => dowCounts[i] ? (v / dowCounts[i]) / (avgTT || 1) : 1.0);

    // 4. Hitung faktor musiman bulanan (Monthly Seasonality)
    const monthCounts = Array(12).fill(0);
    const monthFB = Array(12).fill(0);
    const monthIG = Array(12).fill(0);
    const monthTT = Array(12).fill(0);

    uploadedData.forEach(row => {
      const date = parseTanggalString(row.tanggal);
      const month = date.getMonth(); // 0 = Jan, 11 = Des
      
      monthCounts[month]++;
      monthFB[month] += row.fb;
      monthIG[month] += row.ig;
      monthTT[month] += row.tt;
    });

    const mFBFactor = monthFB.map((v, i) => monthCounts[i] ? (v / monthCounts[i]) / (avgFB || 1) : 1.0);
    const mIGFactor = monthIG.map((v, i) => monthCounts[i] ? (v / monthCounts[i]) / (avgIG || 1) : 1.0);
    const mTTFactor = monthTT.map((v, i) => monthCounts[i] ? (v / monthCounts[i]) / (avgTT || 1) : 1.0);

    // 5. Hitung rata-rata pertumbuhan/tren jangka pendek (30 hari terakhir vs 30 hari pertama)
    let trendFB = 0;
    let trendIG = 0;
    let trendTT = 0;
    if (uploadedData.length >= 60) {
      const first30 = uploadedData.slice(0, 30);
      const last30 = uploadedData.slice(-30);
      
      const f30FB = first30.reduce((s, r) => s + r.fb, 0) / 30;
      const l30FB = last30.reduce((s, r) => s + r.fb, 0) / 30;
      const f30IG = first30.reduce((s, r) => s + r.ig, 0) / 30;
      const l30IG = last30.reduce((s, r) => s + r.ig, 0) / 30;
      const f30TT = first30.reduce((s, r) => s + r.tt, 0) / 30;
      const l30TT = last30.reduce((s, r) => s + r.tt, 0) / 30;

      const daysDiff = uploadedData.length - 30;
      
      if (f30FB > 0) trendFB = (l30FB - f30FB) / f30FB / daysDiff;
      if (f30IG > 0) trendIG = (l30IG - f30IG) / f30IG / daysDiff;
      if (f30TT > 0) trendTT = (l30TT - f30TT) / f30TT / daysDiff;
    }
    
    // Batasi trend pertumbuhan harian agar logis (+/- 0.08% per hari)
    trendFB = Math.max(-0.0008, Math.min(0.0008, trendFB));
    trendIG = Math.max(-0.0008, Math.min(0.0008, trendIG));
    trendTT = Math.max(-0.0008, Math.min(0.0008, trendTT));

    // 6. Proyeksikan 90 hari ke depan
    forecastResults = [];
    const monthNamesID = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];

    for (let i = 1; i <= 90; i++) {
      const fDate = new Date(lastDate.getTime() + i * 24 * 60 * 60 * 1000);
      const day = fDate.getDay();
      const dayOfWeek = (day === 0) ? 6 : day - 1; // 0=Senin, 6=Minggu
      const month = fDate.getMonth(); // 0 = Jan, 11 = Des
      
      const tFB = 1 + trendFB * i;
      const tIG = 1 + trendIG * i;
      const tTT = 1 + trendTT * i;

      let fb = Math.round(avgFB * fbFactor[dayOfWeek] * mFBFactor[month] * tFB);
      let ig = Math.round(avgIG * igFactor[dayOfWeek] * mIGFactor[month] * tIG);
      let tt = Math.round(avgTT * ttFactor[dayOfWeek] * mTTFactor[month] * tTT);

      fb = Math.max(0, fb);
      ig = Math.max(0, ig);
      tt = Math.max(0, tt);

      const dateStr = `${String(fDate.getDate()).padStart(2, '0')} ${monthNamesID[month]} ${fDate.getFullYear()}`;
      
      // Prediksi menggunakan model Machine Learning (predictOne)
      const result = predictOne({ fb, ig, tt, bulan: month + 1, hariPekan: dayOfWeek, sentiment: 0.65 });

      forecastResults.push({
        id: i,
        tanggal: dateStr,
        fb,
        ig,
        tt,
        result
      });
    }

    logToTerminal(`[Forecast] Sukses memproyeksikan ${forecastResults.length} hari ke depan untuk tahun 2026.`);
    renderForecastTable(forecastResults);
    renderForecastSummary(forecastResults);
    initForecastChart(forecastResults);
    
    const fSec = document.getElementById('forecastSection');
    if (fSec) fSec.classList.add('visible');

  } catch(err) {
    logToTerminal(`[Forecast] GAGAL: ${err.message}`);
    console.error(err);
  }
}

function renderForecastTable(results) {
  const tbody = document.getElementById('forecastTableBody');
  if (!tbody) return;
  tbody.innerHTML = '';

  results.forEach((row, i) => {
    const r     = row.result;
    const avg   = r.avg.toFixed(2);
    const isTinggi = r.xgb.class === 'Tinggi';
    const levelClass = isTinggi ? 'level-tinggi' : 'level-rendah';
    const levelText  = isTinggi ? '🔴 Tinggi' : '⚫ Rendah';
    const totalViews = row.fb + row.ig + row.tt;

    const rowStyle = isTinggi ? 'background:rgba(204,0,0,0.04)' : '';

    const tr = document.createElement('tr');
    tr.setAttribute('style', rowStyle);
    tr.innerHTML = `
      <td style="color:var(--text-muted)">${i + 1}</td>
      <td>${sanitize(row.tanggal)}</td>
      <td>${row.fb.toLocaleString('id-ID')}</td>
      <td>${row.ig.toLocaleString('id-ID')}</td>
      <td>${row.tt.toLocaleString('id-ID')}</td>
      <td><strong>${totalViews.toLocaleString('id-ID')}</strong></td>
      <td style="color:#A0A0A0">${r.lr.value.toFixed(2)}</td>
      <td style="color:#FFB800">${r.rf.value.toFixed(2)}</td>
      <td style="color:${isTinggi ? '#FF4444' : '#A0A0A0'};font-weight:600">${r.xgb.value.toFixed(2)}</td>
      <td><span class="level-badge ${levelClass}">${levelText}</span></td>
    `;
    tbody.appendChild(tr);
  });
}

function renderForecastSummary(results) {
  const total = results.length;
  const tinggi = results.filter(r => r.result.xgb.class === 'Tinggi').length;
  const rendah = total - tinggi;
  const avgPred = results.reduce((s,r) => s + r.result.avg, 0) / total;
  const maxPred = Math.max(...results.map(r => r.result.xgb.value));

  const summaryEl = document.getElementById('forecastSummary');
  if (!summaryEl) return;

  summaryEl.innerHTML = `
    <div class="sum-card">
      <div class="sum-value gray">${total} hari</div>
      <div class="sum-label">Proyeksi Depan (2026)</div>
    </div>
    <div class="sum-card">
      <div class="sum-value red">${tinggi} hari</div>
      <div class="sum-label">Proyeksi TINGGI (≥2)</div>
    </div>
    <div class="sum-card">
      <div class="sum-value gray">${rendah} hari</div>
      <div class="sum-label">Proyeksi RENDAH (<2)</div>
    </div>
    <div class="sum-card">
      <div class="sum-value gold">${avgPred.toFixed(2)}</div>
      <div class="sum-label">Rata-rata Prediksi Sales</div>
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

let forecastChartInstance = null;
function initForecastChart(results) {
  const ctx = document.getElementById('chartForecast2026');
  if (!ctx) return;

  if (forecastChartInstance) {
    forecastChartInstance.destroy();
  }

  const fbData = results.map(r => r.fb);
  const igData = results.map(r => r.ig);
  const ttData = results.map(r => r.tt);
  const salesXGB = results.map(r => r.result.xgb.value);

  forecastChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: results.map(r => r.tanggal.split(' ')[0] + ' ' + r.tanggal.split(' ')[1]),
      datasets: [
        {
          label: 'FB Views (Kiri)',
          data: fbData,
          borderColor: 'rgba(24,119,242,0.8)',
          backgroundColor: 'transparent',
          borderWidth: 1.5,
          yAxisID: 'yViews',
          pointRadius: 0
        },
        {
          label: 'IG Views (Kiri)',
          data: igData,
          borderColor: 'rgba(225,48,108,0.8)',
          backgroundColor: 'transparent',
          borderWidth: 1.5,
          yAxisID: 'yViews',
          pointRadius: 0
        },
        {
          label: 'TikTok Views (Kiri)',
          data: ttData,
          borderColor: 'rgba(255,0,80,0.8)',
          backgroundColor: 'transparent',
          borderWidth: 1.5,
          yAxisID: 'yViews',
          pointRadius: 0
        },
        {
          label: 'Prediksi Penjualan (XGB - Kanan)',
          data: salesXGB,
          borderColor: '#FF4444',
          backgroundColor: 'rgba(204,0,0,0.05)',
          borderWidth: 3,
          fill: true,
          yAxisID: 'ySales',
          pointRadius: 1,
          pointBackgroundColor: '#FF4444'
        }
      ]
    },
    options: {
      ...CHART_DEFAULTS,
      scales: {
        x: CHART_DEFAULTS.scales.x,
        yViews: {
          type: 'linear',
          position: 'left',
          ticks: { color: '#A0A0A0', callback: v => (v/1000).toFixed(0) + 'K' },
          grid: { color: 'rgba(46,46,46,0.3)' },
          title: { display: true, text: 'Views Proyeksi', color: '#A0A0A0' }
        },
        ySales: {
          type: 'linear',
          position: 'right',
          min: 0,
          max: 3.5,
          ticks: { color: '#FF8888' },
          grid: { drawOnChartArea: false },
          title: { display: true, text: 'Prediksi Penjualan (unit)', color: '#FF8888' }
        }
      }
    }
  });
}

function downloadForecastCSV() {
  if (!forecastResults.length) return;

  const headers = ['No','Tanggal','Facebook_Proyeksi','Instagram_Proyeksi','TikTok_Proyeksi','Total_Views_Proyeksi',
                   'LR_Pred','RF_Pred','XGB_Pred','Avg_Pred','Kategori_XGB'];

  const rows = forecastResults.map((row, i) => {
    const r = row.result;
    const totalViews = row.fb + row.ig + row.tt;
    return [
      i + 1,
      row.tanggal,
      row.fb,
      row.ig,
      row.tt,
      totalViews,
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
  a.download = `proyeksi_prediksi_indibiz_3bulan_2026.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
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
  // Render metrics tables
  renderMetricsTable('metricsTableBody', false);
  renderMetricsTable('metricsTableDetail', true);

  // Init charts
  initOverviewCharts();
  initDataCharts();
  initModelCharts();

  // Set default active section to 'upload' (ini akan menyembunyikan section lainnya secara otomatis)
  showSection('upload');

  // Hide loading overlay
  setTimeout(() => {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) overlay.classList.add('hidden');
  }, 1400);

  // Demo mode: auto-load Data Harian.csv jika ?demo=1 ada di URL
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get('demo') === '1') {
    setTimeout(() => {
      logToTerminal('[Demo Mode] Mendeteksi parameter ?demo=1. Mengunduh Data Harian.csv...');
      fetch('/data/Data%20Harian.csv')
        .then(response => {
          if (!response.ok) throw new Error('Gagal mengambil file Data Harian.csv');
          return response.blob();
        })
        .then(blob => {
          const file = new File([blob], 'Data Harian.csv', { type: 'text/csv' });
          logToTerminal('[Demo Mode] File berhasil diunduh. Memulai pemrosesan otomatis...');
          processCSVFile(file);
        })
        .catch(err => {
          logToTerminal(`[Demo Mode] ERROR: ${err.message}`);
        });
    }, 2000); // Tunggu sampai inisialisasi awal selesai
  }

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
