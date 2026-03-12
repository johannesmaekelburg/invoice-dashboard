<template>
  <div class="fr-page">

    <!-- ── Page header ── -->
    <div class="page-header">
      <div>
        <span class="page-title">Financial Risk</span>
        <span class="page-sub">Concentration of blocked and at-risk invoice value</span>
      </div>
      <div class="kpi-strip" v-if="summary">
        <div class="kpi-item">
          <span class="kpi-val kpi-error">{{ summary.blockedCount }}</span>
          <span class="kpi-label">Blocked</span>
        </div>
        <div class="kpi-sep"></div>
        <div class="kpi-item">
          <span class="kpi-val kpi-warn">{{ summary.atRiskCount }}</span>
          <span class="kpi-label">At Risk</span>
        </div>
        <div class="kpi-sep"></div>
        <div class="kpi-item">
          <span class="kpi-val kpi-green">{{ summary.compliantCount }}</span>
          <span class="kpi-label">Compliant</span>
        </div>
        <div class="kpi-sep"></div>
        <div class="kpi-item">
          <span class="kpi-val">{{ fmt(summary.totalValue) }}</span>
          <span class="kpi-label">Portfolio</span>
        </div>
      </div>
    </div>

    <!-- ── KPI cards ── -->
    <div class="fr-kpi-row" v-if="summary">
      <div class="fr-kpi-card fr-kpi-blocked">
        <div class="fr-kpi-label">Blocked Value</div>
        <div class="fr-kpi-value">{{ fmt(summary.blockedValue) }}</div>
        <div class="fr-kpi-sub">{{ summary.blockedCount }} invoices</div>
      </div>
      <div class="fr-kpi-card fr-kpi-atrisk">
        <div class="fr-kpi-label">At-Risk Value</div>
        <div class="fr-kpi-value">{{ fmt(summary.atRiskValue) }}</div>
        <div class="fr-kpi-sub">{{ summary.atRiskCount }} invoices</div>
      </div>
      <div class="fr-kpi-card fr-kpi-total">
        <div class="fr-kpi-label">Total Portfolio Value</div>
        <div class="fr-kpi-value">{{ fmt(summary.totalValue) }}</div>
        <div class="fr-kpi-sub">{{ summary.totalCount }} invoices</div>
      </div>
      <div class="fr-kpi-card fr-kpi-safe">
        <div class="fr-kpi-label">Compliant</div>
        <div class="fr-kpi-value">{{ pct(summary.compliantCount, summary.totalCount) }}</div>
        <div class="fr-kpi-sub">{{ summary.compliantCount }} invoices</div>
      </div>
      <div class="fr-kpi-card fr-kpi-exposure">
        <div class="fr-kpi-label">Exposure Rate</div>
        <div class="fr-kpi-value">{{ pct(summary.blockedValue + summary.atRiskValue, summary.totalValue, true) }}</div>
        <div class="fr-kpi-sub">of total portfolio</div>
      </div>
    </div>

    <div class="fr-main-grid">

      <!-- ── Left column ── -->
      <div class="fr-col">

        <!-- Exposure by Supplier -->
        <div class="fr-panel">
          <div class="fr-panel-header">
            <span class="fr-panel-title">Exposure by Supplier</span>
            <span class="fr-panel-sub">Ranked by total at-risk + blocked value</span>
          </div>
          <div class="fr-table-wrap" v-if="bySupplier.length">
            <table class="fr-table">
              <thead>
                <tr>
                  <th class="fr-th-rank">#</th>
                  <th>Supplier</th>
                  <th class="fr-th-num">Blocked</th>
                  <th class="fr-th-num">At Risk</th>
                  <th class="fr-th-num">Invoices</th>
                  <th class="fr-th-bar"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, i) in bySupplier.slice(0, 12)" :key="row.supplier">
                  <td class="fr-td-rank">{{ i + 1 }}</td>
                  <td class="fr-td-name">{{ row.supplier }}</td>
                  <td class="fr-td-num fr-color-blocked">{{ fmt(row.blockedValue) }}</td>
                  <td class="fr-td-num fr-color-atrisk">{{ fmt(row.atRiskValue) }}</td>
                  <td class="fr-td-num">{{ row.blockedCount + row.atRiskCount }}</td>
                  <td class="fr-td-bar">
                    <div class="fr-bar-track">
                      <div class="fr-bar-blocked" :style="{ width: barPct(row.blockedValue, maxSupplierRisk) + '%' }"></div>
                      <div class="fr-bar-atrisk"  :style="{ width: barPct(row.atRiskValue,  maxSupplierRisk) + '%', marginLeft: barPct(row.blockedValue, maxSupplierRisk) + '%' }"></div>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="fr-empty">Loading…</div>
        </div>

        <!-- Exposure by Document Type -->
        <div class="fr-panel">
          <div class="fr-panel-header">
            <span class="fr-panel-title">Exposure by Document Type</span>
          </div>
          <div class="fr-table-wrap" v-if="byDocType.length">
            <table class="fr-table">
              <thead>
                <tr>
                  <th>Document Type</th>
                  <th class="fr-th-num">Blocked</th>
                  <th class="fr-th-num">At Risk</th>
                  <th class="fr-th-num">Count</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in byDocType" :key="row.docType">
                  <td class="fr-td-name">{{ row.docType }}</td>
                  <td class="fr-td-num fr-color-blocked">{{ fmt(row.blockedValue) }}</td>
                  <td class="fr-td-num fr-color-atrisk">{{ fmt(row.atRiskValue) }}</td>
                  <td class="fr-td-num">{{ row.blockedCount + row.atRiskCount }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="fr-empty">No data</div>
        </div>

      </div>

      <!-- ── Right column ── -->
      <div class="fr-col">

        <!-- Violation severity buckets -->
        <div class="fr-panel">
          <div class="fr-panel-header">
            <span class="fr-panel-title">Risk Severity Buckets</span>
            <span class="fr-panel-sub">Grouped by violation count per invoice</span>
          </div>
          <div class="fr-buckets" v-if="aging.length">
            <div v-for="b in aging" :key="b.bucket" class="fr-bucket-row">
              <div class="fr-bucket-label">{{ b.bucket }}</div>
              <div class="fr-bucket-bar-track">
                <div class="fr-bucket-bar" :style="{ width: barPct(b.count, maxBucketCount) + '%' }"></div>
              </div>
              <div class="fr-bucket-nums">
                <span class="fr-bucket-count">{{ b.count }}</span>
                <span class="fr-bucket-value">{{ fmt(b.value) }}</span>
              </div>
            </div>
          </div>
          <div v-else class="fr-empty">Loading…</div>
        </div>

        <!-- High-value risk invoice queue -->
        <div class="fr-panel fr-panel-grow">
          <div class="fr-panel-header">
            <span class="fr-panel-title">High-Value Risk Invoices</span>
            <span class="fr-panel-sub">Top 20 by invoice amount</span>
          </div>
          <div class="fr-table-wrap" v-if="highValue.length">
            <table class="fr-table">
              <thead>
                <tr>
                  <th>Invoice</th>
                  <th>Supplier</th>
                  <th class="fr-th-num">Amount</th>
                  <th class="fr-th-center">Violations</th>
                  <th class="fr-th-center">Status</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="row in highValue"
                  :key="row.uri"
                  class="fr-hv-row"
                  @click="openInvoice(row.uri)"
                >
                  <td class="fr-td-mono">{{ row.documentNumber || row.id }}</td>
                  <td class="fr-td-name">{{ row.supplier }}</td>
                  <td class="fr-td-num">{{ fmt(row.amount) }}</td>
                  <td class="fr-td-center">
                    <span class="fr-viol-badge">{{ row.violationCount }}</span>
                  </td>
                  <td class="fr-td-center">
                    <span :class="['fr-status-pill', row.status === 'Blocked' ? 'fr-status-blocked' : 'fr-status-atrisk']">
                      {{ row.status }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-else class="fr-empty">Loading…</div>
        </div>

      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import {
  getFinancialRiskSummary,
  getExposureBySupplier,
  getExposureByDocType,
  getHighValueRiskInvoices,
  getAgingBuckets,
} from '@/services/api.js';

const router   = useRouter();
const summary  = ref(null);
const bySupplier = ref([]);
const byDocType  = ref([]);
const highValue  = ref([]);
const aging      = ref([]);

function fmt(value) {
  if (value == null || value === '') return '—';
  const n = parseFloat(value);
  if (isNaN(n)) return '—';
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(n);
}

function pct(numerator, denominator, isValue = false) {
  const n = parseFloat(numerator);
  const d = parseFloat(denominator);
  if (!d || isNaN(n) || isNaN(d)) return '—';
  return (n / d * 100).toFixed(1) + '%';
}

function barPct(value, max) {
  if (!max) return 0;
  return Math.min(100, (value / max) * 100).toFixed(1);
}

const maxSupplierRisk = computed(() =>
  Math.max(...bySupplier.value.map(r => r.blockedValue + r.atRiskValue), 1)
);
const maxBucketCount = computed(() =>
  Math.max(...aging.value.map(r => r.count), 1)
);

function openInvoice(uri) {
  router.push({ name: 'InvoiceView', query: { invoice_uri: uri } });
}

onMounted(async () => {
  const [s, sup, dt, hv, ag] = await Promise.all([
    getFinancialRiskSummary(),
    getExposureBySupplier(),
    getExposureByDocType(),
    getHighValueRiskInvoices(),
    getAgingBuckets(),
  ]);
  summary.value   = s;
  bySupplier.value = sup;
  byDocType.value  = dt;
  highValue.value  = hv;
  aging.value      = ag;
});
</script>

<style scoped>
/* ── Shell ── */
.fr-page {
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
.kpi-green { color: #86efac; }
.kpi-warn  { color: #fde68a; }
.kpi-label { font-size: 10px; color: #64748b; text-transform: uppercase; letter-spacing: .5px; margin-top: 1px; }

/* ── Body ── */
.fr-main-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  padding: 20px 24px;
}
@media (max-width: 1000px) { .fr-main-grid { grid-template-columns: 1fr; } }

.fr-col { display: flex; flex-direction: column; gap: 16px; }

/* KPI row */
.fr-kpi-row {
  display: flex;
  gap: 1px;
  flex-wrap: nowrap;
  background: #cbd5e1;
  border: 1px solid #cbd5e1;
  margin: 0 24px;
}
.fr-kpi-card {
  flex: 1 1 0;
  padding: 14px 18px;
  background: #fff;
}
.fr-kpi-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .6px; color: #64748b; margin-bottom: 5px; }
.fr-kpi-value { font-size: 22px; font-weight: 800; line-height: 1.1; font-variant-numeric: tabular-nums; color: #0f172a; }
.fr-kpi-sub   { font-size: 11px; color: #94a3b8; margin-top: 3px; }
.fr-kpi-blocked .fr-kpi-value { color: #dc2626; }
.fr-kpi-atrisk  .fr-kpi-value { color: #d97706; }
.fr-kpi-safe    .fr-kpi-value { color: #16a34a; }
.fr-kpi-exposure .fr-kpi-value { color: #2563eb; }

/* Panel */
.fr-panel {
  background: #fff;
  border: 1px solid #cbd5e1;
  border-radius: 2px;
  overflow: hidden;
}
.fr-panel-grow { flex: 1; }
.fr-panel-header {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 10px 14px 8px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
}
.fr-panel-title { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .7px; color: #64748b; }
.fr-panel-sub   { font-size: 11px; color: #94a3b8; }

/* Table */
.fr-table-wrap { overflow-x: auto; }
.fr-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.fr-table th {
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
.fr-table td { padding: 8px 12px; border-bottom: 1px solid #f1f5f9; vertical-align: middle; color: #334155; }
.fr-table tbody tr:last-child td { border-bottom: none; }
.fr-table tbody tr:hover td { background: #f8fafc; }

.fr-th-num    { text-align: right; }
.fr-th-center { text-align: center; }
.fr-th-rank   { width: 32px; text-align: center; }
.fr-th-bar    { width: 120px; }

.fr-td-rank   { text-align: center; color: #94a3b8; font-size: 11px; }
.fr-td-name   { max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fr-td-num    { text-align: right; font-variant-numeric: tabular-nums; }
.fr-td-center { text-align: center; }
.fr-td-mono   { font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 12px; color: #475569; }
.fr-td-bar    { padding: 0 12px; }

.fr-color-blocked { color: #dc2626; font-weight: 700; }
.fr-color-atrisk  { color: #d97706; font-weight: 700; }

/* Stacked bar */
.fr-bar-track {
  position: relative;
  height: 8px;
  background: #f1f5f9;
  border-radius: 2px;
  overflow: hidden;
}
.fr-bar-blocked, .fr-bar-atrisk {
  position: absolute;
  top: 0;
  height: 100%;
}
.fr-bar-blocked { background: #dc2626; left: 0; }
.fr-bar-atrisk  { background: #d97706; }

/* Bucket rows */
.fr-buckets { padding: 14px; display: flex; flex-direction: column; gap: 10px; }
.fr-bucket-row { display: grid; grid-template-columns: 160px 1fr auto; align-items: center; gap: 10px; }
.fr-bucket-label { font-size: 12px; font-weight: 600; color: #334155; white-space: nowrap; }
.fr-bucket-bar-track { height: 12px; background: #f1f5f9; border-radius: 2px; overflow: hidden; }
.fr-bucket-bar { height: 100%; background: #3b82f6; transition: width .4s ease; }
.fr-bucket-nums { display: flex; flex-direction: column; align-items: flex-end; gap: 1px; min-width: 90px; }
.fr-bucket-count { font-size: 12px; font-weight: 700; color: #0f172a; }
.fr-bucket-value { font-size: 11px; color: #64748b; }

/* High-value risk invoice table */
.fr-hv-row { cursor: pointer; border-left: 3px solid #dc2626; }
.fr-hv-row:hover td { background: #fff5f5 !important; }
.fr-viol-badge {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 22px; height: 20px; border-radius: 10px;
  background: #fee2e2; color: #dc2626;
  font-size: 10px; font-weight: 700; padding: 0 5px;
}
.fr-status-pill {
  display: inline-block; border-radius: 10px;
  padding: 2px 8px; font-size: 10px; font-weight: 700; white-space: nowrap;
}
.fr-status-blocked { background: #fee2e2; color: #dc2626; }
.fr-status-atrisk  { background: #fef3c7; color: #92400e; }

.fr-empty { padding: 24px; color: #94a3b8; font-size: 12px; text-align: center; }
</style>
