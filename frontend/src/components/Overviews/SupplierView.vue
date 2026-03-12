<template>
  <div class="sv-root">
    <div class="sv-header">
      <div class="sv-title-row">
        <v-icon size="18" color="#334155" class="mr-2">mdi-office-building-outline</v-icon>
        <h1 class="sv-title">Supplier Performance</h1>
        <span class="sv-subtitle">Non-conformance rates across all counterparties</span>
      </div>
      <div class="sv-tab-row">
        <button class="sv-tab" :class="{ 'svt-active': tab === 'supplier' }" @click="tab = 'supplier'; selectedRow = null">
          <v-icon size="13" class="mr-1">mdi-truck-outline</v-icon>Suppliers
        </button>
        <button class="sv-tab" :class="{ 'svt-active': tab === 'buyer' }" @click="tab = 'buyer'; selectedRow = null">
          <v-icon size="13" class="mr-1">mdi-store-outline</v-icon>Buyers
        </button>
      </div>
    </div>

    <!-- ── Summary KPI bar ── -->
    <div class="sv-kpi-bar" v-if="!loading && rows.length">
      <div class="sv-kpi">
        <div class="sv-kpi-val">{{ rows.length }}</div>
        <div class="sv-kpi-label">{{ tab === 'supplier' ? 'Suppliers' : 'Buyers' }} tracked</div>
      </div>
      <div class="sv-kpi">
        <div class="sv-kpi-val sv-kv-red">{{ rows.filter(r => r.failRate > 50).length }}</div>
        <div class="sv-kpi-label">High-risk (&gt;50% fail rate)</div>
      </div>
      <div class="sv-kpi">
        <div class="sv-kpi-val sv-kv-amber">{{ rows.filter(r => r.failRate > 0 && r.failRate <= 50).length }}</div>
        <div class="sv-kpi-label">At-risk (1–50% fail rate)</div>
      </div>
      <div class="sv-kpi">
        <div class="sv-kpi-val sv-kv-green">{{ rows.filter(r => r.failRate === 0).length }}</div>
        <div class="sv-kpi-label">Fully compliant</div>
      </div>
    </div>

    <div v-if="loading" class="sv-loading">
      <v-progress-circular indeterminate size="32" color="#3b82f6" />
      <span class="ml-3">Loading...</span>
    </div>

    <!-- ── Ranked table ── -->
    <div v-if="!loading && rows.length" class="sv-table-wrap">
      <table class="sv-table">
        <thead>
          <tr>
            <th class="sv-th-rank">#</th>
            <th @click="setSort('name')" class="sv-th-sortable">
              {{ tab === 'supplier' ? 'Supplier' : 'Buyer' }}
              <v-icon size="11">{{ sortCol === 'name' ? (sortDir === 'asc' ? 'mdi-arrow-up' : 'mdi-arrow-down') : 'mdi-unfold-more-horizontal' }}</v-icon>
            </th>
            <th class="text-right sv-th-sortable" @click="setSort('total')">
              Invoices <v-icon size="11">{{ sortCol === 'total' ? (sortDir === 'asc' ? 'mdi-arrow-up' : 'mdi-arrow-down') : 'mdi-unfold-more-horizontal' }}</v-icon>
            </th>
            <th class="text-right sv-th-sortable" @click="setSort('failing')">
              Non-conf. <v-icon size="11">{{ sortCol === 'failing' ? (sortDir === 'asc' ? 'mdi-arrow-up' : 'mdi-arrow-down') : 'mdi-unfold-more-horizontal' }}</v-icon>
            </th>
            <th>Fail Rate</th>
            <th class="text-right sv-th-sortable" @click="setSort('avgViol')">
              Avg Violations <v-icon size="11">{{ sortCol === 'avgViol' ? (sortDir === 'asc' ? 'mdi-arrow-up' : 'mdi-arrow-down') : 'mdi-unfold-more-horizontal' }}</v-icon>
            </th>
            <th class="text-right sv-th-sortable" @click="setSort('atRisk')">
              Amount at Risk <v-icon size="11">{{ sortCol === 'atRisk' ? (sortDir === 'asc' ? 'mdi-arrow-up' : 'mdi-arrow-down') : 'mdi-unfold-more-horizontal' }}</v-icon>
            </th>
            <th class="text-center">Quality</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, idx) in sortedRows" :key="row.name"
            class="sv-row"
            :class="{ 'sv-row-selected': selectedRow === row.name }"
            @click="selectRow(row.name)">
            <td class="sv-td-rank">
              <span class="sv-rank" :class="idx < 3 ? 'svr-top3' : ''">{{ idx + 1 }}</span>
            </td>
            <td class="sv-td-name">{{ row.name }}</td>
            <td class="text-right sv-td-num">{{ row.total }}</td>
            <td class="text-right sv-td-num">
              <span :class="row.failing > 0 ? 'sv-fail-num' : 'sv-ok-num'">{{ row.failing }}</span>
            </td>
            <td class="sv-td-bar">
              <div class="sv-bar-row">
                <div class="sv-bar-wrap">
                  <div class="sv-bar" :style="{ width: row.failRate + '%' }"
                    :class="row.failRate > 50 ? 'svb-red' : row.failRate > 25 ? 'svb-amber' : row.failRate > 0 ? 'svb-yellow' : 'svb-green'">
                  </div>
                </div>
                <span class="sv-rate-label"
                  :class="row.failRate > 50 ? 'svr-red' : row.failRate > 25 ? 'svr-amber' : row.failRate > 0 ? 'svr-yellow' : 'svr-green'">
                  {{ row.failRate }}%
                </span>
              </div>
            </td>
            <td class="text-right sv-td-num">{{ row.avgViol }}</td>
            <td class="text-right sv-td-num">{{ fmtEur(row.atRisk) }}</td>
            <td class="text-center">
              <span class="sv-quality-badge"
                :class="row.failRate === 0 ? 'svq-green' : row.failRate <= 10 ? 'svq-yellow' : row.failRate <= 40 ? 'svq-amber' : 'svq-red'">
                {{ row.failRate === 0 ? 'Excellent' : row.failRate <= 10 ? 'Good' : row.failRate <= 40 ? 'Fair' : 'Poor' }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="!loading && !rows.length" class="sv-empty">
      No counterparty data available. Ensure invoices include supplier/buyer names.
    </div>

    <!-- ── Drill-down: selected counterparty invoices ── -->
    <div v-if="selectedRow" class="sv-drilldown">
      <div class="sv-dd-header">
        <v-icon size="14" color="#3b82f6" class="mr-1">mdi-filter-outline</v-icon>
        <span class="sv-dd-title">Invoices for <strong>{{ selectedRow }}</strong></span>
        <span class="sv-dd-count">{{ drillInvoices.length }} document{{ drillInvoices.length !== 1 ? 's' : '' }}</span>
        <button class="sv-dd-close" @click="selectedRow = null">
          <v-icon size="14">mdi-close</v-icon> Clear
        </button>
      </div>
      <table class="sv-dd-table">
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
            class="sv-dd-row" @click="openInvoice(inv)">
            <td class="sv-dd-doc">{{ inv.documentNumber || inv.id || '-' }}</td>
            <td>{{ inv.documentType || '-' }}</td>
            <td>{{ inv.documentDate || '-' }}</td>
            <td class="text-right">{{ inv.invoiceAmount ? fmtEur(inv.invoiceAmount) : '-' }}</td>
            <td class="text-right">
              <span class="sv-viol-pill"
                :class="inv.violationCount > 10 ? 'svvp-red' : inv.violationCount > 5 ? 'svvp-amber' : inv.violationCount > 0 ? 'svvp-yellow' : 'svvp-green'">
                {{ inv.violationCount }}
              </span>
            </td>
            <td>
              <span class="sv-status-badge"
                :class="inv.violationCount > 10 ? 'svs-red' : inv.violationCount > 5 ? 'svs-amber' : inv.violationCount > 0 ? 'svs-yellow' : 'svs-green'">
                {{ inv.violationCount > 10 ? 'Cannot Process' : inv.violationCount > 5 ? 'High Risk' : inv.violationCount > 0 ? 'Needs Review' : 'Compliant' }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { getInvoiceList } from '@/services/api.js';

const router = useRouter();

const invoices = ref([]);
const loading  = ref(true);
const tab      = ref('supplier');
const sortCol  = ref('failing');
const sortDir  = ref('desc');
const selectedRow = ref(null);

onMounted(async () => {
  try {
    invoices.value = await getInvoiceList();
  } catch {
    invoices.value = [];
  } finally {
    loading.value = false;
  }
});

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

function setSort(col) {
  if (sortCol.value === col) {
    sortDir.value = sortDir.value === 'desc' ? 'asc' : 'desc';
  } else {
    sortCol.value = col;
    sortDir.value = 'desc';
  }
}

const sortedRows = computed(() => {
  const dir = sortDir.value === 'asc' ? 1 : -1;
  return [...rows.value].sort((a, b) => {
    const av = a[sortCol.value];
    const bv = b[sortCol.value];
    if (typeof av === 'string') return dir * av.localeCompare(bv);
    return dir * (parseFloat(bv) - parseFloat(av)) * -1 || 0;
  }).sort((a, b) => {
    const av = typeof a[sortCol.value] === 'string' ? a[sortCol.value] : parseFloat(a[sortCol.value]);
    const bv = typeof b[sortCol.value] === 'string' ? b[sortCol.value] : parseFloat(b[sortCol.value]);
    if (typeof av === 'string') return sortDir.value === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
    return sortDir.value === 'asc' ? av - bv : bv - av;
  });
});

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

const fmtEur = (v) => {
  const n = parseFloat(v);
  if (!v || isNaN(n)) return '€0';
  if (n >= 1_000_000) return '€' + (n / 1_000_000).toFixed(1) + 'M';
  if (n >= 1_000)     return '€' + (n / 1_000).toFixed(1) + 'K';
  return '€' + n.toFixed(0);
};
</script>

<style scoped>
.sv-root {
  padding: 20px 24px;
  max-width: 1200px;
  font-family: 'Inter', 'Segoe UI', sans-serif;
}

/* ── Header ── */
.sv-header    { margin-bottom: 16px; }
.sv-title-row { display: flex; align-items: center; gap: 0; margin-bottom: 12px; }
.sv-title     { font-size: 16px; font-weight: 800; color: #0f172a; margin: 0 10px 0 0; letter-spacing: -.2px; }
.sv-subtitle  { font-size: 12px; color: #94a3b8; }
.sv-tab-row   { display: flex; gap: 0; border: 1px solid #e2e8f0; border-radius: 4px; overflow: hidden; width: fit-content; }
.sv-tab       { font-size: 11px; font-weight: 600; color: #64748b; background: #fff; border: none; padding: 5px 14px; cursor: pointer; display: flex; align-items: center; transition: background .1s, color .1s; }
.sv-tab:hover { background: #f1f5f9; }
.svt-active   { background: #1e293b !important; color: #fff !important; }

/* ── KPI bar ── */
.sv-kpi-bar { display: flex; gap: 0; border: 1px solid #e2e8f0; border-radius: 2px; overflow: hidden; margin-bottom: 14px; }
.sv-kpi     { flex: 1; padding: 10px 16px; border-right: 1px solid #e2e8f0; background: #fff; }
.sv-kpi:last-child { border-right: none; }
.sv-kpi-val  { font-size: 24px; font-weight: 800; color: #0f172a; line-height: 1; font-variant-numeric: tabular-nums; }
.sv-kv-red   { color: #dc2626; }
.sv-kv-amber { color: #d97706; }
.sv-kv-green { color: #16a34a; }
.sv-kpi-label { font-size: 10px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: .4px; margin-top: 3px; }

/* ── Loading ── */
.sv-loading { display: flex; align-items: center; justify-content: center; padding: 48px; color: #94a3b8; font-size: 13px; }

/* ── Table ── */
.sv-table-wrap { background: #fff; border: 1px solid #e2e8f0; border-radius: 2px; overflow: hidden; margin-bottom: 16px; }
.sv-table      { width: 100%; border-collapse: collapse; }
.sv-table thead tr { background: #1e293b; }
.sv-table th   { font-size: 10px; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: .5px; padding: 9px 12px; border-bottom: 1px solid #2d3f55; white-space: nowrap; }
.sv-th-rank    { width: 44px; text-align: center; }
.sv-th-sortable { cursor: pointer; user-select: none; }
.sv-th-sortable:hover { color: #e2e8f0; }
.sv-table td   { font-size: 12px; padding: 9px 12px; border-bottom: 1px solid #f1f5f9; color: #334155; }
.sv-row        { cursor: pointer; transition: background .1s; }
.sv-row:hover td { background: #f8fafc; }
.sv-row-selected td { background: #eff6ff !important; }
.sv-td-rank    { text-align: center; }
.sv-rank       { display: inline-flex; align-items: center; justify-content: center; width: 22px; height: 22px; border-radius: 50%; font-size: 11px; font-weight: 700; background: #f1f5f9; color: #64748b; }
.svr-top3      { background: #1e293b; color: #fff; }
.sv-td-name    { font-weight: 600; color: #0f172a; max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sv-td-num     { font-variant-numeric: tabular-nums; }
.sv-fail-num   { color: #dc2626; font-weight: 700; }
.sv-ok-num     { color: #16a34a; }

/* ── Bar ── */
.sv-td-bar     { min-width: 160px; }
.sv-bar-row    { display: flex; align-items: center; gap: 8px; }
.sv-bar-wrap   { flex: 1; height: 7px; background: #f1f5f9; border-radius: 2px; overflow: hidden; }
.sv-bar        { height: 100%; border-radius: 2px; transition: width .4s; }
.svb-red       { background: #dc2626; }
.svb-amber     { background: #d97706; }
.svb-yellow    { background: #eab308; }
.svb-green     { background: #16a34a; }
.sv-rate-label { font-size: 11px; font-weight: 700; width: 36px; text-align: right; flex-shrink: 0; }
.svr-red    { color: #dc2626; }
.svr-amber  { color: #d97706; }
.svr-yellow { color: #ca8a04; }
.svr-green  { color: #16a34a; }

/* ── Quality badge ── */
.sv-quality-badge { font-size: 10px; font-weight: 700; border-radius: 3px; padding: 2px 7px; text-transform: uppercase; letter-spacing: .3px; }
.svq-green  { background: #dcfce7; color: #15803d; }
.svq-yellow { background: #fef9c3; color: #a16207; }
.svq-amber  { background: #fef3c7; color: #92400e; }
.svq-red    { background: #fee2e2; color: #b91c1c; }

/* ── Empty ── */
.sv-empty { text-align: center; color: #94a3b8; font-size: 13px; padding: 48px 0; }

/* ── Drill-down ── */
.sv-drilldown { background: #fff; border: 1px solid #bfdbfe; border-radius: 2px; overflow: hidden; }
.sv-dd-header { display: flex; align-items: center; gap: 8px; padding: 10px 14px; background: #eff6ff; border-bottom: 1px solid #bfdbfe; }
.sv-dd-title  { font-size: 12px; font-weight: 600; color: #1d4ed8; }
.sv-dd-count  { font-size: 11px; color: #60a5fa; }
.sv-dd-close  { margin-left: auto; font-size: 11px; color: #64748b; background: transparent; border: 1px solid #cbd5e1; border-radius: 3px; padding: 2px 8px; cursor: pointer; display: flex; align-items: center; gap: 3px; }
.sv-dd-close:hover { background: #fee2e2; border-color: #fca5a5; color: #dc2626; }
.sv-dd-table  { width: 100%; border-collapse: collapse; }
.sv-dd-table th { font-size: 10px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: .4px; padding: 7px 12px; border-bottom: 1px solid #e2e8f0; background: #f8fafc; }
.sv-dd-table td { font-size: 12px; padding: 8px 12px; border-bottom: 1px solid #f1f5f9; color: #334155; }
.sv-dd-row    { cursor: pointer; transition: background .1s; }
.sv-dd-row:hover td { background: #f0f9ff; }
.sv-dd-doc    { font-weight: 600; color: #0f172a; }
.sv-viol-pill { font-size: 10px; font-weight: 700; border-radius: 10px; padding: 1px 7px; }
.svvp-red     { background: #fee2e2; color: #b91c1c; }
.svvp-amber   { background: #fef3c7; color: #92400e; }
.svvp-yellow  { background: #fef9c3; color: #a16207; }
.svvp-green   { background: #dcfce7; color: #15803d; }
.sv-status-badge { font-size: 10px; font-weight: 700; border-radius: 3px; padding: 2px 7px; }
.svs-red    { background: #fee2e2; color: #b91c1c; }
.svs-amber  { background: #fef3c7; color: #92400e; }
.svs-yellow { background: #fef9c3; color: #a16207; }
.svs-green  { background: #dcfce7; color: #15803d; }
</style>
