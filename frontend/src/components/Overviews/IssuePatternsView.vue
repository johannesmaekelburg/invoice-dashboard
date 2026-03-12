<template>
  <div class="ip-page">

    <!-- ── Page header ── -->
    <div class="page-header">
      <div>
        <span class="page-title">Issue Patterns</span>
        <span class="page-sub">Structural quality and compliance patterns across the invoice portfolio</span>
      </div>
      <div class="kpi-strip" v-if="summary">
        <div class="kpi-item">
          <span class="kpi-val kpi-error">{{ summary.totalViolations }}</span>
          <span class="kpi-label">Violations</span>
        </div>
        <div class="kpi-sep"></div>
        <div class="kpi-item">
          <span class="kpi-val">{{ summary.distinctCategories }}</span>
          <span class="kpi-label">Issue Types</span>
        </div>
        <div class="kpi-sep"></div>
        <div class="kpi-item">
          <span class="kpi-val kpi-warn">{{ summary.topCategoryCount }}</span>
          <span class="kpi-label">Top Issue</span>
        </div>
      </div>
    </div>

    <!-- ── KPI cards ── -->
    <div class="ip-kpi-row" v-if="summary && summary.totalViolations > 0">
      <div class="ip-kpi-card ip-kpi-total">
        <div class="ip-kpi-label">Total Violations</div>
        <div class="ip-kpi-value">{{ summary.totalViolations }}</div>
      </div>
      <div class="ip-kpi-card ip-kpi-cats">
        <div class="ip-kpi-label">Distinct Issue Types</div>
        <div class="ip-kpi-value">{{ summary.distinctCategories }}</div>
      </div>
      <div class="ip-kpi-card ip-kpi-top">
        <div class="ip-kpi-label">Most Common Issue</div>
        <div class="ip-kpi-value ip-kpi-value-sm">{{ summary.topCategory }}</div>
        <div class="ip-kpi-sub">{{ summary.topCategoryCount }} occurrences</div>
      </div>
      <div v-for="sv in severity" :key="sv.severity" class="ip-kpi-card">
        <div class="ip-kpi-label">{{ severityLabel(sv.severity) }}</div>
        <div class="ip-kpi-value" :class="severityClass(sv.severity)">{{ sv.count }}</div>
        <div class="ip-kpi-sub">violations</div>
      </div>
    </div>

    <div class="ip-main-grid">

      <!-- ── Left column ── -->
      <div class="ip-col">

        <!-- Top issue categories -->
        <div class="ip-panel">
          <div class="ip-panel-header">
            <span class="ip-panel-title">Top Issue Categories</span>
            <span class="ip-panel-sub">Ranked by occurrence count</span>
          </div>
          <div class="ip-table-wrap" v-if="topCats.length">
            <table class="ip-table">
              <thead>
                <tr>
                  <th class="ip-th-rank">#</th>
                  <th>Issue / Constraint</th>
                  <th class="ip-th-num">Violations</th>
                  <th class="ip-th-num">Invoices</th>
                  <th class="ip-th-bar"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, i) in topCats" :key="row.category">
                  <td class="ip-td-rank">{{ i + 1 }}</td>
                  <td class="ip-td-name">{{ row.category }}</td>
                  <td class="ip-td-num">{{ row.violationCount }}</td>
                  <td class="ip-td-num ip-muted">{{ row.invoiceCount }}</td>
                  <td class="ip-td-bar">
                    <div class="ip-bar-track">
                      <div class="ip-bar-fill" :style="{ width: barPct(row.violationCount, maxCatViolations) + '%' }"></div>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="ip-empty">Loading…</div>
        </div>

        <!-- Issues by section -->
        <div class="ip-panel">
          <div class="ip-panel-header">
            <span class="ip-panel-title">Violations by Invoice Section</span>
          </div>
          <div class="ip-sections" v-if="bySection.length">
            <div v-for="sec in bySection" :key="sec.section" class="ip-section-row">
              <div class="ip-section-label">{{ sec.section }}</div>
              <div class="ip-section-bar-track">
                <div class="ip-section-bar" :style="{ width: barPct(sec.violationCount, maxSectionViolations) + '%' }"></div>
              </div>
              <div class="ip-section-nums">
                <span class="ip-section-count">{{ sec.violationCount }}</span>
                <span class="ip-section-inv">{{ sec.invoiceCount }} invoices</span>
              </div>
            </div>
          </div>
          <div v-else class="ip-empty">Loading…</div>
        </div>

      </div>

      <!-- ── Right column ── -->
      <div class="ip-col">

        <!-- Severity breakdown -->
        <div class="ip-panel">
          <div class="ip-panel-header">
            <span class="ip-panel-title">Severity Breakdown</span>
          </div>
          <div class="ip-sev-grid" v-if="severity.length">
            <div v-for="sv in severity" :key="sv.severity" class="ip-sev-card" :class="severityCardClass(sv.severity)">
              <div class="ip-sev-label">{{ severityLabel(sv.severity) }}</div>
              <div class="ip-sev-count">{{ sv.count }}</div>
              <div class="ip-sev-bar-track">
                <div class="ip-sev-bar-fill" :style="{ width: barPct(sv.count, totalViolationsNum) + '%' }"></div>
              </div>
              <div class="ip-sev-pct">{{ pct(sv.count, totalViolationsNum) }}</div>
            </div>
          </div>
          <div v-else class="ip-empty">Loading…</div>
        </div>

        <!-- Per-supplier breakdown -->
        <div class="ip-panel ip-panel-grow">
          <div class="ip-panel-header">
            <span class="ip-panel-title">Issues by Supplier</span>
            <span class="ip-panel-sub">Top 15 by violation count</span>
          </div>
          <div class="ip-table-wrap" v-if="bySupplier.length">
            <table class="ip-table">
              <thead>
                <tr>
                  <th>Supplier</th>
                  <th class="ip-th-num">Violations</th>
                  <th>Top Issues</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in bySupplier" :key="row.supplier">
                  <td class="ip-td-name">{{ row.supplier }}</td>
                  <td class="ip-td-num ip-bold">{{ row.totalViolations }}</td>
                  <td class="ip-td-issues">
                    <span v-for="cat in row.topCategories.slice(0, 3)" :key="cat.category" class="ip-cat-tag">
                      {{ cat.category }} <em>({{ cat.count }})</em>
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="ip-empty">Loading…</div>
        </div>

      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import {
  getIssueSummary,
  getTopIssueCategories,
  getIssuesBySection,
  getIssuesBySupplier,
  getIssueSeverityBreakdown,
} from '@/services/api.js';

const summary    = ref(null);
const topCats    = ref([]);
const bySection  = ref([]);
const bySupplier = ref([]);
const severity   = ref([]);

function barPct(value, max) {
  if (!max) return 0;
  return Math.min(100, (value / max) * 100).toFixed(1);
}

function pct(numerator, denominator) {
  const n = parseFloat(numerator);
  const d = parseFloat(denominator);
  if (!d || isNaN(n)) return '—';
  return (n / d * 100).toFixed(1) + '%';
}

function severityLabel(sev) {
  if (!sev) return 'Unknown';
  const s = sev.split('#').pop().replace('Severity', '').toLowerCase();
  return s.charAt(0).toUpperCase() + s.slice(1);
}
function severityClass(sev) {
  const s = (sev || '').toLowerCase();
  if (s.includes('violation')) return 'ip-sev-violation';
  if (s.includes('warning'))   return 'ip-sev-warning';
  if (s.includes('info'))      return 'ip-sev-info';
  return '';
}
function severityCardClass(sev) {
  const s = (sev || '').toLowerCase();
  if (s.includes('violation')) return 'ip-sev-card-violation';
  if (s.includes('warning'))   return 'ip-sev-card-warning';
  if (s.includes('info'))      return 'ip-sev-card-info';
  return '';
}

const maxCatViolations = computed(() =>
  Math.max(...topCats.value.map(r => r.violationCount), 1)
);
const maxSectionViolations = computed(() =>
  Math.max(...bySection.value.map(r => r.violationCount), 1)
);
const totalViolationsNum = computed(() =>
  severity.value.reduce((acc, r) => acc + r.count, 0) || 1
);

onMounted(async () => {
  const [s, tc, bs, bsup, sev] = await Promise.all([
    getIssueSummary(),
    getTopIssueCategories(),
    getIssuesBySection(),
    getIssuesBySupplier(),
    getIssueSeverityBreakdown(),
  ]);
  summary.value    = s;
  topCats.value    = tc;
  bySection.value  = bs;
  bySupplier.value = bsup;
  severity.value   = sev;
});
</script>

<style scoped>
/* ── Shell ── */
.ip-page {
  min-height: 100vh;
  background: #eef0f3;
  font-family: 'Inter', 'Segoe UI', 'Roboto', sans-serif;
}

/* ── Page header (dark navy, same as HomeView) ── */
.page-header {
  background: #1e293b;
  padding: 14px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  border-bottom: 1px solid #334155;
}
.page-title { font-size: 15px; font-weight: 700; color: #f1f5f9; letter-spacing: .3px; }
.page-sub   { font-size: 11px; color: #64748b; margin-left: 10px; }
.kpi-strip {
  display: flex;
  align-items: center;
  background: rgba(255,255,255,.05);
  border: 1px solid #334155;
  border-radius: 4px;
  overflow: hidden;
}
.kpi-item  { display: flex; flex-direction: column; align-items: center; padding: 6px 18px; }
.kpi-sep   { width: 1px; background: #334155; align-self: stretch; }
.kpi-val   { font-size: 18px; font-weight: 700; color: #f1f5f9; line-height: 1.2; font-variant-numeric: tabular-nums; }
.kpi-error { color: #fca5a5; }
.kpi-warn  { color: #fde68a; }
.kpi-label { font-size: 10px; color: #64748b; text-transform: uppercase; letter-spacing: .5px; margin-top: 1px; }

/* ── KPI card strip ── */
.ip-kpi-row {
  display: flex;
  gap: 1px;
  background: #cbd5e1;
  border: 1px solid #cbd5e1;
  margin: 0 24px;
}
.ip-kpi-card {
  flex: 1 1 0;
  padding: 14px 18px;
  background: #fff;
}
.ip-kpi-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .6px; color: #64748b; margin-bottom: 5px; }
.ip-kpi-value { font-size: 22px; font-weight: 800; line-height: 1.1; font-variant-numeric: tabular-nums; color: #0f172a; }
.ip-kpi-value-sm { font-size: 13px; font-weight: 700; line-height: 1.3; max-width: 260px; white-space: normal; color: #0f172a; }
.ip-kpi-sub  { font-size: 11px; color: #94a3b8; margin-top: 3px; }
.ip-kpi-total .ip-kpi-value { color: #dc2626; }
.ip-kpi-cats  .ip-kpi-value { color: #2563eb; }

.ip-sev-violation { color: #dc2626; }
.ip-sev-warning   { color: #d97706; }
.ip-sev-info      { color: #2563eb; }

/* ── Main layout ── */
.ip-main-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  padding: 20px 24px;
}
@media (max-width: 1000px) { .ip-main-grid { grid-template-columns: 1fr; } }

.ip-col { display: flex; flex-direction: column; gap: 16px; }

/* Panel */
.ip-panel {
  background: #fff;
  border: 1px solid #cbd5e1;
  border-radius: 2px;
  overflow: hidden;
}
.ip-panel-grow { flex: 1; }
.ip-panel-header {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 10px 14px 8px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
}
.ip-panel-title { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .7px; color: #64748b; }
.ip-panel-sub   { font-size: 11px; color: #94a3b8; }

/* Table */
.ip-table-wrap { overflow-x: auto; }
.ip-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.ip-table th {
  text-align: left;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .6px;
  color: #64748b;
  padding: 7px 12px;
  border-bottom: 1px solid #e2e8f0;
  white-space: nowrap;
  background: #f1f5f9;
}
.ip-table td { padding: 8px 12px; border-bottom: 1px solid #f1f5f9; vertical-align: middle; color: #334155; }
.ip-table tbody tr:last-child td { border-bottom: none; }
.ip-table tbody tr:hover td { background: #f8fafc; }

.ip-th-num  { text-align: right; }
.ip-th-rank { width: 32px; text-align: center; }
.ip-th-bar  { width: 100px; }

.ip-td-rank   { text-align: center; color: #94a3b8; font-size: 11px; }
.ip-td-name   { max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ip-td-num    { text-align: right; font-variant-numeric: tabular-nums; }
.ip-td-issues { max-width: 240px; }
.ip-muted     { color: #94a3b8; }
.ip-bold      { font-weight: 700; }
.ip-td-bar    { padding: 0 12px; }

/* Bar */
.ip-bar-track { height: 8px; background: #f1f5f9; border-radius: 2px; overflow: hidden; }
.ip-bar-fill  { height: 100%; background: #dc2626; transition: width .4s ease; }

/* Sections */
.ip-sections { padding: 14px; display: flex; flex-direction: column; gap: 10px; }
.ip-section-row { display: grid; grid-template-columns: 130px 1fr auto; align-items: center; gap: 10px; }
.ip-section-label { font-size: 12px; font-weight: 600; color: #334155; white-space: nowrap; }
.ip-section-bar-track { height: 12px; background: #f1f5f9; border-radius: 2px; overflow: hidden; }
.ip-section-bar { height: 100%; background: #2563eb; transition: width .4s ease; }
.ip-section-nums { display: flex; flex-direction: column; align-items: flex-end; gap: 1px; min-width: 80px; }
.ip-section-count { font-size: 12px; font-weight: 700; color: #0f172a; }
.ip-section-inv   { font-size: 11px; color: #94a3b8; }

/* Severity cards */
.ip-sev-grid { display: flex; gap: 1px; background: #e2e8f0; margin: 14px; flex-wrap: wrap; }
.ip-sev-card {
  flex: 1 1 80px;
  padding: 14px;
  background: #fff;
}
.ip-sev-card-violation { border-top: 3px solid #dc2626; }
.ip-sev-card-warning   { border-top: 3px solid #d97706; }
.ip-sev-card-info      { border-top: 3px solid #2563eb; }
.ip-sev-label  { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; color: #64748b; margin-bottom: 4px; }
.ip-sev-count  { font-size: 28px; font-weight: 800; line-height: 1; margin-bottom: 8px; font-variant-numeric: tabular-nums; }
.ip-sev-card-violation .ip-sev-count { color: #dc2626; }
.ip-sev-card-warning   .ip-sev-count { color: #d97706; }
.ip-sev-card-info      .ip-sev-count { color: #2563eb; }
.ip-sev-bar-track { height: 4px; background: #f1f5f9; border-radius: 1px; overflow: hidden; margin-bottom: 4px; }
.ip-sev-bar-fill  { height: 100%; transition: width .4s ease; }
.ip-sev-card-violation .ip-sev-bar-fill { background: #dc2626; }
.ip-sev-card-warning   .ip-sev-bar-fill { background: #d97706; }
.ip-sev-card-info      .ip-sev-bar-fill { background: #2563eb; }
.ip-sev-pct { font-size: 11px; color: #94a3b8; }

/* Supplier tag list */
.ip-cat-tag {
  display: inline-block;
  background: #f1f5f9;
  border-radius: 2px;
  padding: 2px 6px;
  font-size: 11px;
  color: #475569;
  margin: 2px 2px 0 0;
  white-space: nowrap;
  border: 1px solid #e2e8f0;
}
.ip-cat-tag em { font-style: normal; color: #94a3b8; }

.ip-empty { padding: 24px; color: #94a3b8; font-size: 12px; text-align: center; }
</style>
