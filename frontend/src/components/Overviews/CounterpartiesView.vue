<template>
  <div class="cp-root">

    <!-- ── Dark-navy header ── -->
    <div class="cp-header">
      <div class="cp-header-top">
        <div>
          <span class="cp-title">Counterparties</span>
          <span class="cp-subtitle">Non-conformance &amp; financial exposure across all suppliers and buyers</span>
        </div>
        <div class="cp-tab-row">
          <button class="cp-tab" :class="{ 'cpt-active': tab === 'supplier' }" @click="switchTab('supplier')">
            <v-icon size="13" class="mr-1">mdi-truck-outline</v-icon>Suppliers
          </button>
          <button class="cp-tab" :class="{ 'cpt-active': tab === 'buyer' }" @click="switchTab('buyer')">
            <v-icon size="13" class="mr-1">mdi-store-outline</v-icon>Buyers
          </button>
        </div>
      </div>

      <!-- KPI strip in header -->
      <div class="cp-kpi-strip" v-if="!loading">
        <div class="cp-ks-item">
          <span class="cp-ks-val cp-kv-red">{{ fmtEur(riskSummary.blockedValue) }}</span>
          <span class="cp-ks-label">Blocked Value</span>
        </div>
        <div class="cp-ks-item">
          <span class="cp-ks-val cp-kv-amber">{{ fmtEur(riskSummary.atRiskValue) }}</span>
          <span class="cp-ks-label">At-Risk Value</span>
        </div>
        <div class="cp-ks-item">
          <span class="cp-ks-val">{{ riskSummary.exposurePct != null ? riskSummary.exposurePct + '%' : '—' }}</span>
          <span class="cp-ks-label">Portfolio Exposure</span>
        </div>
        <div class="cp-ks-item">
          <span class="cp-ks-val">{{ rows.length }}</span>
          <span class="cp-ks-label">{{ tab === 'supplier' ? 'Suppliers' : 'Buyers' }} Tracked</span>
        </div>
        <div class="cp-ks-item">
          <span class="cp-ks-val cp-kv-red">{{ rows.filter(r => r.failRate > 50).length }}</span>
          <span class="cp-ks-label">High-Risk (&gt;50%)</span>
        </div>
        <div class="cp-ks-item">
          <span class="cp-ks-val cp-kv-green">{{ rows.filter(r => r.failRate === 0).length }}</span>
          <span class="cp-ks-label">Fully Compliant</span>
        </div>
      </div>
    </div>

    <!-- ── Body ── -->
    <div class="cp-body">

      <div v-if="loading" class="cp-loading">
        <v-progress-circular indeterminate size="32" color="#3b82f6" />
        <span class="ml-3">Loading counterparty data…</span>
      </div>

      <!-- ── Ranked table ── -->
      <div v-if="!loading && rows.length" class="cp-panel">
        <div class="cp-panel-hdr">
          <span class="cp-panel-title">Ranked {{ tab === 'supplier' ? 'Suppliers' : 'Buyers' }}</span>
          <span class="cp-panel-meta">{{ sortedRows.length }} counterpart{{ sortedRows.length !== 1 ? 'ies' : 'y' }} · click a row to drill down</span>
        </div>
        <table class="cp-table">
          <thead>
            <tr>
              <th class="cp-th-rank">#</th>
              <th @click="setSort('name')" class="cp-th-sort">
                {{ tab === 'supplier' ? 'Supplier' : 'Buyer' }}
                <v-icon size="11">{{ sortCol === 'name' ? (sortDir === 'asc' ? 'mdi-arrow-up' : 'mdi-arrow-down') : 'mdi-unfold-more-horizontal' }}</v-icon>
              </th>
              <th class="text-right cp-th-sort" @click="setSort('total')">
                Invoices <v-icon size="11">{{ sortCol === 'total' ? (sortDir === 'asc' ? 'mdi-arrow-up' : 'mdi-arrow-down') : 'mdi-unfold-more-horizontal' }}</v-icon>
              </th>
              <th class="text-right cp-th-sort" @click="setSort('failing')">
                Non-conf. <v-icon size="11">{{ sortCol === 'failing' ? (sortDir === 'asc' ? 'mdi-arrow-up' : 'mdi-arrow-down') : 'mdi-unfold-more-horizontal' }}</v-icon>
              </th>
              <th>Fail Rate</th>
              <th class="text-right cp-th-sort" @click="setSort('avgViol')">
                Avg Viol. <v-icon size="11">{{ sortCol === 'avgViol' ? (sortDir === 'asc' ? 'mdi-arrow-up' : 'mdi-arrow-down') : 'mdi-unfold-more-horizontal' }}</v-icon>
              </th>
              <th class="text-right cp-th-sort" @click="setSort('atRisk')">
                Amount at Risk <v-icon size="11">{{ sortCol === 'atRisk' ? (sortDir === 'asc' ? 'mdi-arrow-up' : 'mdi-arrow-down') : 'mdi-unfold-more-horizontal' }}</v-icon>
              </th>
              <th class="text-center">Quality</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, idx) in sortedRows" :key="row.name"
              class="cp-row"
              :class="{ 'cp-row-sel': selectedRow === row.name }"
              @click="selectRow(row.name)">
              <td class="cp-td-rank">
                <span class="cp-rank" :class="idx < 3 ? 'cpr-top3' : ''">{{ idx + 1 }}</span>
              </td>
              <td class="cp-td-name">{{ row.name }}</td>
              <td class="text-right cp-td-num">{{ row.total }}</td>
              <td class="text-right cp-td-num">
                <span :class="row.failing > 0 ? 'cp-fail-num' : 'cp-ok-num'">{{ row.failing }}</span>
              </td>
              <td class="cp-td-bar">
                <div class="cp-bar-row">
                  <div class="cp-bar-wrap">
                    <div class="cp-bar" :style="{ width: row.failRate + '%' }"
                      :class="row.failRate > 50 ? 'cpb-red' : row.failRate > 25 ? 'cpb-amber' : row.failRate > 0 ? 'cpb-yellow' : 'cpb-green'">
                    </div>
                  </div>
                  <span class="cp-rate-label"
                    :class="row.failRate > 50 ? 'cpr-red' : row.failRate > 25 ? 'cpr-amber' : row.failRate > 0 ? 'cpr-yellow' : 'cpr-green'">
                    {{ row.failRate }}%
                  </span>
                </div>
              </td>
              <td class="text-right cp-td-num">{{ row.avgViol }}</td>
              <td class="text-right cp-td-num">{{ fmtEur(row.atRisk) }}</td>
              <td class="text-center">
                <span class="cp-badge"
                  :class="row.failRate === 0 ? 'cpq-green' : row.failRate <= 10 ? 'cpq-yellow' : row.failRate <= 40 ? 'cpq-amber' : 'cpq-red'">
                  {{ row.failRate === 0 ? 'Excellent' : row.failRate <= 10 ? 'Good' : row.failRate <= 40 ? 'Fair' : 'Poor' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="!loading && !rows.length" class="cp-empty">
        No counterparty data available. Ensure invoices include supplier/buyer names.
      </div>

      <!-- ── Drill-down: selected counterparty invoices ── -->
      <div v-if="selectedRow" class="cp-drilldown">
        <div class="cp-dd-hdr">
          <v-icon size="14" color="#3b82f6" class="mr-1">mdi-filter-outline</v-icon>
          <span class="cp-dd-title">Invoices for <strong>{{ selectedRow }}</strong></span>
          <span class="cp-dd-count">{{ drillInvoices.length }} document{{ drillInvoices.length !== 1 ? 's' : '' }}</span>
          <button class="cp-dd-close" @click="selectedRow = null">
            <v-icon size="14">mdi-close</v-icon> Clear
          </button>
        </div>
        <table class="cp-dd-table">
          <thead>
            <tr>
              <th>Document No.</th>
              <th>Type</th>
              <th>Date</th>
              <th class="text-right">Amount</th>
              <th class="text-right">Violations</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="inv in drillInvoices" :key="inv.uri"
              class="cp-dd-row" @click="openInvoice(inv)">
              <td class="cp-dd-doc">{{ inv.documentNumber || inv.id || '-' }}</td>
              <td>{{ inv.documentType || '-' }}</td>
              <td>{{ inv.documentDate || '-' }}</td>
              <td class="text-right">{{ inv.invoiceAmount ? fmtEur(inv.invoiceAmount) : '-' }}</td>
              <td class="text-right">
                <span class="cp-viol-pill"
                  :class="inv.violationCount > 10 ? 'cpvp-red' : inv.violationCount > 5 ? 'cpvp-amber' : inv.violationCount > 0 ? 'cpvp-yellow' : 'cpvp-green'">
                  {{ inv.violationCount }}
                </span>
              </td>
              <td>
                <span class="cp-status-badge"
                  :class="inv.violationCount > 10 ? 'cps-red' : inv.violationCount > 5 ? 'cps-amber' : inv.violationCount > 0 ? 'cps-yellow' : 'cps-green'">
                  {{ inv.violationCount > 10 ? 'Cannot Process' : inv.violationCount > 5 ? 'High Risk' : inv.violationCount > 0 ? 'Needs Review' : 'Compliant' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

    </div><!-- /cp-body -->
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { getInvoiceList, getFinancialRiskSummary } from '@/services/api.js';

const router = useRouter();

// ── State ──
const invoices    = ref([]);
const riskSummary = ref({});
const loading     = ref(true);
const tab         = ref('supplier');
const sortCol     = ref('failing');
const sortDir     = ref('desc');
const selectedRow = ref(null);

// ── Load ──
onMounted(async () => {
  try {
    [invoices.value, riskSummary.value] = await Promise.all([
      getInvoiceList(),
      getFinancialRiskSummary(),
    ]);
  } catch {
    invoices.value    = [];
    riskSummary.value = {};
  } finally {
    loading.value = false;
  }
});

// ── Build rows (client-side aggregation) ──
function buildRows(keyFn) {
  const map = {};
  for (const inv of invoices.value) {
    const key = keyFn(inv);
    if (!key) continue;
    if (!map[key]) map[key] = { name: key, total: 0, failing: 0, totalViol: 0, atRisk: 0 };
    map[key].total++;
    if (inv.violationCount > 0) {
      map[key].failing++;
      map[key].totalViol += inv.violationCount;
      map[key].atRisk += parseFloat(inv.invoiceAmount || 0);
    }
  }
  return Object.values(map).map(r => ({
    ...r,
    failRate: Math.round((r.failing / r.total) * 100),
    avgViol:  r.failing > 0 ? (r.totalViol / r.failing).toFixed(1) : '0',
  }));
}

const rows = computed(() =>
  tab.value === 'supplier'
    ? buildRows(i => i.supplierName || null)
    : buildRows(i => i.buyerName    || null)
);

// ── Sort ──
function setSort(col) {
  if (sortCol.value === col) {
    sortDir.value = sortDir.value === 'desc' ? 'asc' : 'desc';
  } else {
    sortCol.value = col;
    sortDir.value = 'desc';
  }
}

const sortedRows = computed(() => {
  return [...rows.value].sort((a, b) => {
    const av = typeof a[sortCol.value] === 'string' ? a[sortCol.value] : parseFloat(a[sortCol.value]);
    const bv = typeof b[sortCol.value] === 'string' ? b[sortCol.value] : parseFloat(b[sortCol.value]);
    if (typeof av === 'string') return sortDir.value === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
    return sortDir.value === 'asc' ? av - bv : bv - av;
  });
});

// ── Tab switch ──
function switchTab(t) {
  tab.value = t;
  selectedRow.value = null;
}

// ── Drill-down ──
const drillInvoices = computed(() => {
  if (!selectedRow.value) return [];
  const field = tab.value === 'supplier' ? 'supplierName' : 'buyerName';
  return [...invoices.value.filter(i => i[field] === selectedRow.value)]
    .sort((a, b) => b.violationCount - a.violationCount);
});

function selectRow(name) {
  selectedRow.value = selectedRow.value === name ? null : name;
}

function openInvoice(inv) {
  router.push({ name: 'InvoiceView', query: { uri: inv.uri } });
}

// ── Formatters ──
const fmtEur = (v) => {
  const n = parseFloat(v);
  if (!v || isNaN(n)) return '—';
  if (n >= 1_000_000) return '€' + (n / 1_000_000).toFixed(1) + 'M';
  if (n >= 1_000)     return '€' + (n / 1_000).toFixed(1) + 'K';
  return '€' + n.toFixed(0);
};
</script>

<style scoped>
/* ── Root ── */
.cp-root {
  background: #eef0f3;
  min-height: 100vh;
  font-family: 'Inter', 'Segoe UI', sans-serif;
}

/* ── Header ── */
.cp-header {
  background: #1e293b;
  padding: 14px 24px 12px;
  border-bottom: 1px solid #334155;
}
.cp-header-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.cp-title {
  font-size: 15px;
  font-weight: 700;
  color: #f1f5f9;
  margin-right: 10px;
}
.cp-subtitle {
  font-size: 12px;
  color: #64748b;
}

/* ── Tab row (inside header) ── */
.cp-tab-row {
  display: flex;
  gap: 0;
  border: 1px solid #334155;
  border-radius: 4px;
  overflow: hidden;
}
.cp-tab {
  font-size: 11px;
  font-weight: 600;
  color: #94a3b8;
  background: transparent;
  border: none;
  padding: 5px 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  transition: background .1s, color .1s;
}
.cp-tab:hover { background: rgba(255,255,255,.07); color: #e2e8f0; }
.cpt-active   { background: rgba(255,255,255,.15) !important; color: #f1f5f9 !important; }

/* ── KPI strip ── */
.cp-kpi-strip {
  display: flex;
  gap: 1px;
  background: #334155;
  border: 1px solid #334155;
  border-radius: 4px;
  overflow: hidden;
}
.cp-ks-item {
  flex: 1;
  background: rgba(255,255,255,.05);
  padding: 8px 14px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.cp-ks-val {
  font-size: 18px;
  font-weight: 800;
  color: #f1f5f9;
  font-variant-numeric: tabular-nums;
  line-height: 1;
}
.cp-kv-red   { color: #f87171; }
.cp-kv-amber { color: #fbbf24; }
.cp-kv-green { color: #4ade80; }
.cp-ks-label {
  font-size: 9px;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: .5px;
}

/* ── Body ── */
.cp-body { padding: 20px 24px; }

/* ── Loading / empty ── */
.cp-loading { display: flex; align-items: center; justify-content: center; padding: 48px; color: #94a3b8; font-size: 13px; }
.cp-empty   { text-align: center; color: #94a3b8; font-size: 13px; padding: 48px 0; }

/* ── Panel ── */
.cp-panel {
  background: #fff;
  border: 1px solid #cbd5e1;
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 16px;
}
.cp-panel-hdr {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 14px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
}
.cp-panel-title {
  font-size: 11px;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: .7px;
}
.cp-panel-meta {
  font-size: 11px;
  color: #94a3b8;
}

/* ── Table ── */
.cp-table { width: 100%; border-collapse: collapse; }
.cp-table thead tr { background: #1e293b; }
.cp-table th {
  font-size: 10px;
  font-weight: 700;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: .5px;
  padding: 9px 12px;
  border-bottom: 1px solid #2d3f55;
  white-space: nowrap;
}
.cp-th-rank { width: 44px; text-align: center; }
.cp-th-sort { cursor: pointer; user-select: none; }
.cp-th-sort:hover { color: #e2e8f0; }
.cp-table td { font-size: 12px; padding: 9px 12px; border-bottom: 1px solid #f1f5f9; color: #334155; }
.cp-row { cursor: pointer; transition: background .1s; }
.cp-row:hover td { background: #f8fafc; }
.cp-row-sel td { background: #eff6ff !important; }
.cp-td-rank { text-align: center; }
.cp-rank { display: inline-flex; align-items: center; justify-content: center; width: 22px; height: 22px; border-radius: 50%; font-size: 11px; font-weight: 700; background: #f1f5f9; color: #64748b; }
.cpr-top3 { background: #1e293b; color: #fff; }
.cp-td-name { font-weight: 600; color: #0f172a; max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cp-td-num { font-variant-numeric: tabular-nums; }
.cp-fail-num { color: #dc2626; font-weight: 700; }
.cp-ok-num   { color: #16a34a; }

/* ── Fail rate bar ── */
.cp-td-bar  { min-width: 160px; }
.cp-bar-row { display: flex; align-items: center; gap: 8px; }
.cp-bar-wrap { flex: 1; height: 7px; background: #f1f5f9; border-radius: 2px; overflow: hidden; }
.cp-bar { height: 100%; border-radius: 2px; transition: width .4s; }
.cpb-red    { background: #dc2626; }
.cpb-amber  { background: #d97706; }
.cpb-yellow { background: #eab308; }
.cpb-green  { background: #16a34a; }
.cp-rate-label { font-size: 11px; font-weight: 700; width: 36px; text-align: right; flex-shrink: 0; }
.cpr-red    { color: #dc2626; }
.cpr-amber  { color: #d97706; }
.cpr-yellow { color: #ca8a04; }
.cpr-green  { color: #16a34a; }

/* ── Quality badge ── */
.cp-badge { font-size: 10px; font-weight: 700; border-radius: 3px; padding: 2px 7px; text-transform: uppercase; letter-spacing: .3px; }
.cpq-green  { background: #dcfce7; color: #15803d; }
.cpq-yellow { background: #fef9c3; color: #a16207; }
.cpq-amber  { background: #fef3c7; color: #92400e; }
.cpq-red    { background: #fee2e2; color: #b91c1c; }

/* ── Drill-down ── */
.cp-drilldown { background: #fff; border: 1px solid #bfdbfe; border-radius: 2px; overflow: hidden; }
.cp-dd-hdr { display: flex; align-items: center; gap: 8px; padding: 10px 14px; background: #eff6ff; border-bottom: 1px solid #bfdbfe; }
.cp-dd-title { font-size: 12px; font-weight: 600; color: #1d4ed8; }
.cp-dd-count { font-size: 11px; color: #60a5fa; }
.cp-dd-close { margin-left: auto; font-size: 11px; color: #64748b; background: transparent; border: 1px solid #cbd5e1; border-radius: 3px; padding: 2px 8px; cursor: pointer; display: flex; align-items: center; gap: 3px; }
.cp-dd-close:hover { background: #fee2e2; border-color: #fca5a5; color: #dc2626; }
.cp-dd-table { width: 100%; border-collapse: collapse; }
.cp-dd-table th { font-size: 10px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: .4px; padding: 7px 12px; border-bottom: 1px solid #e2e8f0; background: #f8fafc; }
.cp-dd-table td { font-size: 12px; padding: 8px 12px; border-bottom: 1px solid #f1f5f9; color: #334155; }
.cp-dd-row { cursor: pointer; transition: background .1s; }
.cp-dd-row:hover td { background: #f0f9ff; }
.cp-dd-doc { font-weight: 600; color: #0f172a; }
.cp-viol-pill { font-size: 10px; font-weight: 700; border-radius: 10px; padding: 1px 7px; }
.cpvp-red    { background: #fee2e2; color: #b91c1c; }
.cpvp-amber  { background: #fef3c7; color: #92400e; }
.cpvp-yellow { background: #fef9c3; color: #a16207; }
.cpvp-green  { background: #dcfce7; color: #15803d; }
.cp-status-badge { font-size: 10px; font-weight: 700; border-radius: 3px; padding: 2px 7px; }
.cps-red    { background: #fee2e2; color: #b91c1c; }
.cps-amber  { background: #fef3c7; color: #92400e; }
.cps-yellow { background: #fef9c3; color: #a16207; }
.cps-green  { background: #dcfce7; color: #15803d; }
</style>
