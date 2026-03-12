<template>
  <div class="home-view">

    <!-- Page header -->
    <div class="page-header">
      <div>
        <span class="page-title">E-Invoice Compliance Dashboard</span>
        <span class="page-sub">SHACL Validation Overview</span>
      </div>
      <div class="kpi-strip">
        <div class="kpi-item">
          <span class="kpi-val">{{ stats.totalInvoices ?? '-' }}</span>
          <span class="kpi-label">Invoices</span>
        </div>
        <div class="kpi-sep"></div>
        <div class="kpi-item">
          <span class="kpi-val kpi-error">{{ stats.totalViolations ?? '-' }}</span>
          <span class="kpi-label">Violations</span>
        </div>
        <div class="kpi-sep"></div>
        <div class="kpi-item">
          <span class="kpi-val kpi-green">{{ conformingCount }}</span>
          <span class="kpi-label">Conforming</span>
        </div>
        <div class="kpi-sep"></div>
        <div class="kpi-item">
          <span class="kpi-val kpi-warn">{{ nonConformingCount }}</span>
          <span class="kpi-label">Non-Conforming</span>
        </div>
        <div class="kpi-sep"></div>
        <div class="kpi-item">
          <span class="kpi-val">{{ stats.totalItems ?? '-' }}</span>
          <span class="kpi-label">Line Items</span>
        </div>
      </div>
    </div>

    <div class="body-pad">

      <!-- ── Analytics dashboard ─────────────────────────────────────── -->
      <div class="analysis-grid" v-if="!loading && invoices.length">

        <!-- ① Conformance Rate — compact donut -->
        <div class="chart-card chart-donut">
          <div class="chart-card-title">Conformance Rate</div>
          <div class="donut-wrap">
            <svg viewBox="0 0 120 120" class="donut-svg">
              <circle cx="60" cy="60" r="50" fill="none" stroke="#e2e8f0" stroke-width="16"/>
              <circle cx="60" cy="60" r="50" fill="none"
                stroke="#16a34a" stroke-width="16" stroke-linecap="round"
                :stroke-dasharray="`${conformingPct * 3.14159} 314.159`"
                stroke-dashoffset="0" transform="rotate(-90 60 60)"
              />
              <circle cx="60" cy="60" r="50" fill="none"
                stroke="#dc2626" stroke-width="16" stroke-linecap="round"
                :stroke-dasharray="`${nonConformingPct * 3.14159} 314.159`"
                :stroke-dashoffset="`${-(conformingPct * 3.14159)}`"
                transform="rotate(-90 60 60)"
              />
            </svg>
            <div class="donut-center">
              <div class="donut-pct">{{ Math.round(conformingPct) }}%</div>
              <div class="donut-pct-label">Conforming</div>
            </div>
          </div>
          <div class="donut-legend">
            <div class="legend-row"><span class="legend-dot green"></span>OK: <strong>{{ conformingCount }}</strong></div>
            <div class="legend-row"><span class="legend-dot red"></span>Fail: <strong>{{ nonConformingCount }}</strong></div>
          </div>
          <div class="compliance-score-badge"
            :class="conformingPct >= 80 ? 'score-ok' : conformingPct >= 50 ? 'score-mid' : 'score-bad'">
            <v-icon size="12" style="margin-right:4px">
              {{ conformingPct >= 80 ? 'mdi-check-circle-outline' : conformingPct >= 50 ? 'mdi-alert-outline' : 'mdi-alert-circle-outline' }}
            </v-icon>
            {{ conformingPct >= 80 ? 'Excellent' : conformingPct >= 50 ? 'Needs Attention' : 'Critical' }}
          </div>
        </div>

        <!-- ② Violations by Severity -->
        <div class="chart-card chart-severity">
          <div class="chart-card-title">Violations by Severity</div>
          <div class="chart-card-sub">Breakdown of all {{ stats.totalViolations ?? 0 }} violations by classification</div>
          <div class="severity-bars" v-if="stats.bySeverity && stats.bySeverity.length">
            <div v-for="s in stats.bySeverity" :key="s.severity" class="sev-row">
              <span class="sev-icon">
                <v-icon size="14" :color="s.severity === 'Violation' ? '#dc2626' : s.severity === 'Warning' ? '#d97706' : '#2563eb'">
                  {{ s.severity === 'Violation' ? 'mdi-close-circle' : s.severity === 'Warning' ? 'mdi-alert' : 'mdi-information' }}
                </v-icon>
              </span>
              <div class="sev-label">{{ s.severity }}</div>
              <div class="sev-bar-track">
                <div class="sev-bar-fill"
                  :class="'fill-' + s.severity.toLowerCase()"
                  :style="{ width: stats.totalViolations ? Math.round((s.count / stats.totalViolations) * 100) + '%' : '0%' }">
                </div>
              </div>
              <div class="sev-pct">{{ stats.totalViolations ? Math.round((s.count / stats.totalViolations) * 100) : 0 }}%</div>
              <div class="sev-count">{{ s.count }}</div>
            </div>
          </div>
          <div v-else class="no-data">No violation data</div>
        </div>

        <!-- ③ Financial Exposure at Risk -->
        <div class="chart-card chart-exposure">
          <div class="chart-card-title">Financial Exposure at Risk</div>
          <div class="chart-card-sub">Total invoice value in non-compliant documents</div>
          <div class="exp-risk-level"
            :class="financialExposure.atRiskPct > 50 ? 'risk-high' : financialExposure.atRiskPct > 20 ? 'risk-mid' : 'risk-low'">
            <v-icon size="13" style="margin-right:4px">
              {{ financialExposure.atRiskPct > 50 ? 'mdi-fire' : financialExposure.atRiskPct > 20 ? 'mdi-alert-outline' : 'mdi-shield-check-outline' }}
            </v-icon>
            {{ financialExposure.atRiskPct > 50 ? 'High Risk' : financialExposure.atRiskPct > 20 ? 'Moderate Risk' : 'Low Risk' }}
          </div>
          <div class="exp-hero">
            <div class="exp-risk-amount">{{ fmtEur(financialExposure.atRisk) }}</div>
            <div class="exp-risk-meta">
              <span class="exp-risk-badge">{{ financialExposure.atRiskPct }}% at risk</span>
              <span class="exp-risk-sub">{{ nonConformingCount }} invoice{{ nonConformingCount !== 1 ? 's' : '' }} flagged</span>
            </div>
          </div>
          <div class="exp-bar-track">
            <div class="exp-bar-risk" :style="{ width: financialExposure.atRiskPct + '%' }"></div>
            <div class="exp-bar-safe" :style="{ width: financialExposure.compliantPct + '%' }"></div>
          </div>
          <div class="exp-legend-row">
            <div class="exp-leg-item"><span class="legend-dot red"></span><span>At Risk <strong>{{ fmtEur(financialExposure.atRisk) }}</strong></span></div>
            <div class="exp-leg-item"><span class="legend-dot green"></span><span>Compliant <strong>{{ fmtEur(financialExposure.compliant) }}</strong></span></div>
          </div>
        </div>

        <!-- ④ Compliance Rate by Invoice Type (wide) -->
        <div class="chart-card chart-type">
          <div class="chart-card-title">Compliance Rate by Invoice Type</div>
          <div class="chart-card-sub">Non-conformance breakdown per document category — sorted by failure rate</div>
          <div class="type-bars" v-if="byDocType.length">
            <div v-for="t in byDocType" :key="t.type" class="type-row">
              <div class="type-label" :title="t.type">{{ t.type }}</div>
              <div class="type-count-pill">{{ t.total }}</div>
              <div class="type-stacked-bar">
                <div class="type-seg-ok" :style="{ width: (100 - Math.round(t.failRate * 100)) + '%' }">
                  <span v-if="100 - Math.round(t.failRate * 100) > 15">{{ 100 - Math.round(t.failRate * 100) }}%</span>
                </div>
                <div class="type-seg-err" :style="{ width: Math.round(t.failRate * 100) + '%' }">
                  <span v-if="Math.round(t.failRate * 100) > 15">{{ Math.round(t.failRate * 100) }}%</span>
                </div>
              </div>
              <div class="type-failure-rate"
                :class="t.failRate > 0.5 ? 'rate-high' : t.failRate > 0.2 ? 'rate-mid' : 'rate-low'">
                {{ Math.round(t.failRate * 100) }}%
              </div>
            </div>
          </div>
          <div v-else class="no-data">No invoice type data</div>
          <div class="type-legend">
            <span class="legend-dot green" style="border-radius:2px;width:14px;height:10px;"></span><span>Conforming</span>
            <span class="legend-dot red" style="border-radius:2px;width:14px;height:10px;margin-left:16px;"></span><span>Non-conforming</span>
          </div>
        </div>

        <!-- ⑤ Violation Load Distribution -->
        <div class="chart-card chart-histogram">
          <div class="chart-card-title">Violation Load Distribution</div>
          <div class="chart-card-sub">Count of invoices per violation bucket</div>
          <div class="histogram">
            <div v-for="b in violationBuckets" :key="b.label" class="histo-col">
              <div class="histo-bar-slot">
                <div class="histo-bar-fill"
                  :class="b.label === '0' ? 'fill-ok' : 'fill-err'"
                  :style="{ height: histoHeightPx(b.count) + 'px' }">
                </div>
              </div>
              <div class="histo-count">{{ b.count }}</div>
              <div class="histo-label">{{ b.label }}</div>
            </div>
          </div>
          <div class="histo-legend">
            <span><span class="histo-dot ok-dot"></span>0 violations</span>
            <span><span class="histo-dot err-dot"></span>Has violations</span>
          </div>
        </div>

      </div><!-- /analysis-grid -->

      <!-- ── Top Failing Entities ──────────────────────────────────────── -->
      <div class="top-failing-panel" v-if="!loading && topFailingRows.length">
        <div class="tfp-header">
          <v-icon size="14" color="#64748b" class="mr-1">mdi-chart-bar</v-icon>
          <span class="tfp-title">Top Failing</span>
          <div class="tfp-tabs">
            <button class="tfp-tab" :class="{ 'tfpt-active': topFailingTab === 'supplier' }" @click="topFailingTab = 'supplier'">Suppliers</button>
            <button class="tfp-tab" :class="{ 'tfpt-active': topFailingTab === 'buyer' }" @click="topFailingTab = 'buyer'">Buyers</button>
            <button class="tfp-tab" :class="{ 'tfpt-active': topFailingTab === 'doctype' }" @click="topFailingTab = 'doctype'">Doc&nbsp;Types</button>
          </div>
          <span class="tfp-sub">by non-conforming invoice count</span>
        </div>
        <div class="tfp-list">
          <div v-for="s in topFailingRows" :key="s.name" class="tfp-row">
            <div class="tfp-name" :title="s.name">{{ s.name }}</div>
            <div class="tfp-bar-wrap">
              <div class="tfp-bar" :style="{ width: s.rate + '%' }"
                :class="s.rate > 50 ? 'tfpb-red' : s.rate > 25 ? 'tfpb-amber' : 'tfpb-green'"></div>
            </div>
            <div class="tfp-rate" :class="s.rate > 50 ? 'tfpr-red' : s.rate > 25 ? 'tfpr-amber' : 'tfpr-green'">{{ s.rate }}%</div>
            <div class="tfp-count">{{ s.failing }}/{{ s.total }}</div>
          </div>
        </div>
      </div>

      <!-- ── Top 10 Needing Attention worklist ─────────────────────── -->
      <div class="worklist-panel" v-if="!loading && top10Worklist.length">
        <div class="worklist-header">
          <v-icon size="14" style="color:#f87171;margin-right:6px">mdi-alert-circle-outline</v-icon>
          <span class="worklist-title">Top Needing Attention</span>
          <span class="worklist-count">{{ top10Worklist.length }}</span>
          <span class="worklist-sub">{{ worklistSort === 'risk-score' ? 'Ranked by violations × amount (high-value + high-risk first)' : 'Ranked by violation count' }} — click to inspect</span>
          <div class="wl-sort-toggle">
            <button class="wls-btn" :class="{ 'wls-active': worklistSort === 'violations' }" @click="worklistSort = 'violations'">Violations</button>
            <button class="wls-btn" :class="{ 'wls-active': worklistSort === 'risk-score' }" @click="worklistSort = 'risk-score'">Risk Score</button>
          </div>
        </div>
        <table class="worklist-table">
          <thead>
            <tr>
              <th class="wl-th-rank">#</th>
              <th>Document No.</th>
              <th>Type</th>
              <th class="text-right">Amount</th>
              <th class="text-right">Violations</th>
              <th>Status</th>
              <th class="text-right">Risk Score</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(inv, idx) in top10Worklist" :key="inv.uri"
              class="wl-row" @click="openInvoice(inv)">
              <td class="wl-td-rank">
                <span class="wl-rank-num" :class="idx < 3 ? 'rank-top3' : ''">{{ idx + 1 }}</span>
              </td>
              <td class="wl-doc-num">
                <div>{{ inv.documentNumber || inv.id || '-' }}</div>
                <div v-if="inv.supplierName || inv.buyerName" class="wl-counterparty">
                  <span v-if="inv.supplierName" class="wl-cp-supplier" :title="'Supplier: ' + inv.supplierName">{{ inv.supplierName }}</span>
                  <span v-if="inv.supplierName && inv.buyerName" class="wl-cp-sep">→</span>
                  <span v-if="inv.buyerName" class="wl-cp-buyer" :title="'Buyer: ' + inv.buyerName">{{ inv.buyerName }}</span>
                </div>
              </td>
              <td class="wl-type">{{ inv.documentType || '-' }}</td>
              <td class="text-right wl-amount">{{ inv.invoiceAmount ? fmtEur(inv.invoiceAmount) : '-' }}</td>
              <td class="text-right">
                <span class="wl-viol-pill"
                  :class="inv.violationCount > 10 ? 'pill-critical' : inv.violationCount > 5 ? 'pill-high' : 'pill-med'">
                  {{ inv.violationCount }}
                </span>
              </td>
              <td>
                <span class="wl-status-badge"
                  :class="inv.violationCount > 10 ? 'wlb-critical' : inv.violationCount > 5 ? 'wlb-high' : 'wlb-review'">
                  {{ inv.violationCount > 10 ? 'Cannot Process' : inv.violationCount > 5 ? 'High Risk' : 'Needs Review' }}
                </span>
              </td>
              <td class="text-right wl-risk-score">
                <span class="wl-score-pill"
                  :class="inv.riskScore >= 70 ? 'wlsc-red' : inv.riskScore >= 40 ? 'wlsc-amber' : 'wlsc-blue'">
                  {{ inv.riskScore }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- ── Business filters bar ───────────────────────────────────── -->
      <div class="filter-bar" v-if="!loading">
        <div class="filter-bar-left">
          <v-icon size="14" color="#64748b" style="margin-right:4px">mdi-filter-outline</v-icon>
          <span class="filter-label">Filters:</span>
          <button class="filter-chip" :class="{ 'chip-active': nonConformingOnly }" @click="nonConformingOnly = !nonConformingOnly">
            <v-icon size="12" style="margin-right:4px">{{ nonConformingOnly ? 'mdi-checkbox-marked' : 'mdi-checkbox-blank-outline' }}</v-icon>
            Non-conforming only
          </button>
          <button class="filter-chip" :class="{ 'chip-active': criticalOnly }" @click="criticalOnly = !criticalOnly">
            <v-icon size="12" style="margin-right:4px">{{ criticalOnly ? 'mdi-checkbox-marked' : 'mdi-checkbox-blank-outline' }}</v-icon>
            Critical only (&gt;5 violations)
          </button>
          <v-select
            v-model="docTypeFilter"
            :items="docTypeOptions"
            item-title="title"
            item-value="value"
            density="compact"
            variant="outlined"
            hide-details
            style="max-width:190px"
            class="filter-select"
          />
          <v-select
            v-model="supplierFilter"
            :items="supplierOptions"
            item-title="title"
            item-value="value"
            density="compact"
            variant="outlined"
            hide-details
            style="max-width:190px"
            class="filter-select"
          />
          <v-select
            v-model="buyerFilter"
            :items="buyerOptions"
            item-title="title"
            item-value="value"
            density="compact"
            variant="outlined"
            hide-details
            style="max-width:190px"
            class="filter-select"
          />
        </div>
        <button v-if="nonConformingOnly || criticalOnly || docTypeFilter || supplierFilter || buyerFilter"
          class="clear-filters-btn"
          @click="nonConformingOnly=false; criticalOnly=false; docTypeFilter=''; supplierFilter=''; buyerFilter=''">
          <v-icon size="12" style="margin-right:4px">mdi-close-circle-outline</v-icon>Clear filters
        </button>
      </div>

      <!-- ── Invoice toolbar ─────────────────────────────────────────── -->
      <div class="inv-toolbar">
        <div class="inv-toolbar-left">
          <v-icon size="18" class="mr-1" color="#94a3b8">mdi-file-document-multiple-outline</v-icon>
          <span class="inv-toolbar-title">Invoices</span>
          <span class="inv-toolbar-count">{{ filteredInvoices.length }}</span>
        </div>
        <div class="inv-toolbar-right">
          <v-text-field
            v-model="search"
            placeholder="Search..."
            prepend-inner-icon="mdi-magnify"
            density="compact"
            variant="outlined"
            hide-details
            style="max-width:220px"
            class="toolbar-input"
          />
          <v-select
            v-model="sortBy"
            :items="sortOptions"
            item-title="title"
            item-value="value"
            density="compact"
            variant="outlined"
            hide-details
            style="max-width:190px"
            prepend-inner-icon="mdi-sort"
            class="toolbar-input"
          />
          <div class="view-toggle">
            <button class="vt-btn" :class="{ active: viewMode === 'grid' }" @click="viewMode = 'grid'" title="Grid view">
              <v-icon size="18">mdi-view-grid-outline</v-icon>
            </button>
            <button class="vt-btn" :class="{ active: viewMode === 'list' }" @click="viewMode = 'list'" title="List view">
              <v-icon size="18">mdi-view-list-outline</v-icon>
            </button>
          </div>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="text-center py-10">
        <v-progress-circular indeterminate color="primary" size="48" />
        <div class="text-medium-emphasis mt-3">Loading invoices...</div>
      </div>

      <!-- Empty -->
      <div v-else-if="filteredInvoices.length === 0" class="text-center py-10">
        <v-icon size="48" color="medium-emphasis">mdi-file-search-outline</v-icon>
        <div class="text-medium-emphasis mt-2">No invoices found</div>
      </div>

      <!-- ══ GRID VIEW ══ -->
      <div v-else-if="viewMode === 'grid'" class="invoice-grid">
        <div
          v-for="invoice in filteredInvoices"
          :key="invoice.uri"
          class="inv-card"
          :class="{ 'inv-card-error': invoice.violationCount > 0 }"
          @click="openInvoice(invoice)"
        >
          <div class="inv-card-top">
            <span class="inv-card-num">{{ invoice.documentNumber || invoice.id || '(no number)' }}</span>
            <span class="inv-viol-badge" :class="invoice.violationCount > 0 ? 'badge-err' : 'badge-ok'">
              {{ invoice.violationCount }}
            </span>
          </div>
          <div class="inv-card-meta">
            <span v-if="invoice.documentDate">
              <v-icon size="11" class="mr-1">mdi-calendar-outline</v-icon>{{ invoice.documentDate }}
            </span>
            <span v-if="invoice.invoiceAmount">
              <v-icon size="11" class="mr-1">mdi-currency-eur</v-icon>{{ fmtNum(invoice.invoiceAmount) }}
            </span>
          </div>
          <div v-if="invoice.documentType" class="inv-card-type">{{ invoice.documentType }}</div>
        </div>
      </div>

      <!-- ══ LIST VIEW ══ -->
      <div v-else class="invoice-list">
        <table class="inv-table">
          <thead>
            <tr>
              <th>Document No.</th>
              <th>Date</th>
              <th>Type</th>
              <th class="text-right">Amount</th>
              <th>Currency</th>
              <th class="text-right">Violations</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="invoice in filteredInvoices" :key="invoice.uri"
              class="inv-row"
              :class="{ 'inv-row-error': invoice.violationCount > 0 }"
              @click="openInvoice(invoice)">
              <td class="inv-td-num">{{ invoice.documentNumber || invoice.id || '-' }}</td>
              <td class="text-caption text-slate">{{ invoice.documentDate || '-' }}</td>
              <td class="text-caption text-slate">{{ invoice.documentType || '-' }}</td>
              <td class="text-right font-mono">{{ invoice.invoiceAmount ? fmtNum(invoice.invoiceAmount) : '-' }}</td>
              <td class="text-caption text-slate">{{ invoice.currency || '-' }}</td>
              <td class="text-right">
                <span class="inv-viol-badge" :class="invoice.violationCount > 0 ? 'badge-err' : 'badge-ok'">
                  {{ invoice.violationCount }}
                </span>
              </td>
              <td class="text-right">
                <v-icon size="14" color="#94a3b8">mdi-arrow-right</v-icon>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

    </div><!-- /body-pad -->
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { getInvoiceList, getGlobalStats } from '@/services/api.js';

const router   = useRouter();
const invoices = ref([]);
const stats    = ref({});
const loading  = ref(true);
const search            = ref('');
const viewMode          = ref('grid');
const sortBy            = ref('violations-desc');
const nonConformingOnly = ref(false);
const criticalOnly      = ref(false);
const docTypeFilter     = ref('');
const supplierFilter    = ref('');
const buyerFilter       = ref('');
const worklistSort      = ref('risk-score');

const sortOptions = [
  { title: 'Most violations',   value: 'violations-desc' },
  { title: 'Fewest violations', value: 'violations-asc'  },
  { title: 'Document number',   value: 'doc-number'      },
  { title: 'Highest amount',    value: 'amount-desc'     },
];

const fmtNum = (v) => v != null ? parseFloat(v).toFixed(2) : '-';
const fmtEur = (v) => {
  const n = parseFloat(v);
  if (!v || isNaN(n)) return '€0';
  if (n >= 1_000_000) return '€' + (n / 1_000_000).toFixed(1) + 'M';
  if (n >= 1_000)     return '€' + (n / 1_000).toFixed(1) + 'K';
  return '€' + n.toFixed(0);
};

onMounted(async () => {
  const [list, globalStats] = await Promise.all([
    getInvoiceList().catch(() => []),
    getGlobalStats().catch(() => ({})),
  ]);
  invoices.value = list;
  stats.value    = globalStats;
  loading.value  = false;
});

// ── Conformance ──────────────────────────────────────────────────────────────
const conformingCount    = computed(() => invoices.value.filter(i => i.violationCount === 0).length);
const nonConformingCount = computed(() => invoices.value.filter(i => i.violationCount  > 0).length);
const total              = computed(() => invoices.value.length || 1);
const conformingPct      = computed(() => (conformingCount.value    / total.value) * 100);
const nonConformingPct   = computed(() => (nonConformingCount.value / total.value) * 100);

// ── Financial Exposure ───────────────────────────────────────────────────────
const financialExposure = computed(() => {
  let compliant = 0, atRisk = 0;
  for (const inv of invoices.value) {
    const amt = parseFloat(inv.invoiceAmount || 0);
    if (inv.violationCount === 0) compliant += amt;
    else atRisk += amt;
  }
  const tot = compliant + atRisk || 1;
  return {
    compliant,
    atRisk,
    compliantPct: Math.round((compliant / tot) * 100),
    atRiskPct:    Math.round((atRisk    / tot) * 100),
  };
});

// ── Compliance by Invoice Type ───────────────────────────────────────────────
const byDocType = computed(() => {
  const map = {};
  for (const inv of invoices.value) {
    const key = inv.documentType || 'Unknown';
    if (!map[key]) map[key] = { type: key, total: 0, failures: 0 };
    map[key].total++;
    if (inv.violationCount > 0) map[key].failures++;
  }
  return Object.values(map)
    .map(d => ({ ...d, failRate: d.failures / d.total }))
    .sort((a, b) => b.failRate - a.failRate)
    .slice(0, 7);
});

// ── Doc-type filter options ─────────────────────────────────────────────────
const docTypeOptions = computed(() => [
  { title: 'All Types', value: '' },
  ...Object.keys(
    invoices.value.reduce((m, i) => { m[i.documentType || 'Unknown'] = 1; return m; }, {})
  ).sort().map(t => ({ title: t, value: t })),
]);

const supplierOptions = computed(() => [
  { title: 'All Suppliers', value: '' },
  ...[...new Set(invoices.value.map(i => i.supplierName).filter(Boolean))].sort().map(s => ({ title: s, value: s })),
]);

const buyerOptions = computed(() => [
  { title: 'All Buyers', value: '' },
  ...[...new Set(invoices.value.map(i => i.buyerName).filter(Boolean))].sort().map(s => ({ title: s, value: s })),
]);

// ── Top failing entities ─────────────────────────────────────────────────────
const topFailingTab = ref('supplier');
function buildTopFailing(keyFn) {
  const map = {};
  for (const inv of invoices.value) {
    const key = keyFn(inv);
    if (!key) continue;
    if (!map[key]) map[key] = { name: key, total: 0, failing: 0 };
    map[key].total++;
    if (inv.violationCount > 0) map[key].failing++;
  }
  return Object.values(map)
    .filter(s => s.failing > 0)
    .sort((a, b) => b.failing - a.failing || b.total - a.total)
    .slice(0, 6)
    .map(s => ({ ...s, rate: Math.round((s.failing / s.total) * 100) }));
}
const topFailingSuppliers  = computed(() => buildTopFailing(i => i.supplierName || null));
const topFailingBuyers     = computed(() => buildTopFailing(i => i.buyerName    || null));
const topFailingDocTypes   = computed(() => buildTopFailing(i => i.documentType || null));
const topFailingRows = computed(() => {
  if (topFailingTab.value === 'buyer')   return topFailingBuyers.value;
  if (topFailingTab.value === 'doctype') return topFailingDocTypes.value;
  return topFailingSuppliers.value;
});

// ── Top-10 worklist ──────────────────────────────────────────────────────────
const top10Worklist = computed(() => {
  const list = invoices.value.filter(i => i.violationCount > 0);
  const maxAmt  = Math.max(...list.map(i => parseFloat(i.invoiceAmount || 0)), 1);
  const maxViol = Math.max(...list.map(i => i.violationCount), 1);
  const withScore = list.map(i => ({
    ...i,
    riskScore: Math.round(
      ((i.violationCount / maxViol) * 0.6 + (parseFloat(i.invoiceAmount || 0) / maxAmt) * 0.4) * 100
    ),
  }));
  if (worklistSort.value === 'risk-score') {
    return [...withScore].sort((a, b) => b.riskScore - a.riskScore).slice(0, 10);
  }
  return [...withScore].sort((a, b) => b.violationCount - a.violationCount).slice(0, 10);
});

// ── Violation Distribution ───────────────────────────────────────────────────
const bucketDefs = [
  { label: '0',     min: 0,  max: 0        },
  { label: '1-2',   min: 1,  max: 2        },
  { label: '3-5',   min: 3,  max: 5        },
  { label: '6-10',  min: 6,  max: 10       },
  { label: '11-20', min: 11, max: 20       },
  { label: '21+',   min: 21, max: Infinity },
];
const violationBuckets = computed(() =>
  bucketDefs.map(b => ({
    label: b.label,
    count: invoices.value.filter(i => i.violationCount >= b.min && i.violationCount <= b.max).length,
  }))
);
const maxBucketCount = computed(() => Math.max(...violationBuckets.value.map(b => b.count), 1));
// Returns a pixel height (0–110 px) — percentage does NOT work in this flex layout
const histoHeightPx = (n) => Math.round((n / maxBucketCount.value) * 110);

// ── Invoice list ─────────────────────────────────────────────────────────────
const filteredInvoices = computed(() => {
  const q = search.value.trim().toLowerCase();
  let list = q
    ? invoices.value.filter(i => (i.documentNumber || i.id || '').toLowerCase().includes(q))
    : [...invoices.value];
  if (nonConformingOnly.value) list = list.filter(i => i.violationCount > 0);
  if (criticalOnly.value)      list = list.filter(i => i.violationCount > 5);
  if (docTypeFilter.value)     list = list.filter(i => (i.documentType || 'Unknown') === docTypeFilter.value);
  if (supplierFilter.value)    list = list.filter(i => i.supplierName === supplierFilter.value);
  if (buyerFilter.value)       list = list.filter(i => i.buyerName    === buyerFilter.value);
  const sorters = {
    'violations-desc': (a, b) => b.violationCount - a.violationCount,
    'violations-asc':  (a, b) => a.violationCount - b.violationCount,
    'doc-number':      (a, b) => (a.documentNumber || '').localeCompare(b.documentNumber || ''),
    'amount-desc':     (a, b) => parseFloat(b.invoiceAmount || 0) - parseFloat(a.invoiceAmount || 0),
  };
  return list.sort(sorters[sortBy.value] ?? sorters['violations-desc']);
});

const openInvoice = (invoice) => router.push({ path: '/invoice', query: { uri: invoice.uri } });
</script>

<style scoped>
/* ── Shell ─────────────────────────────────────────────────────────── */
.home-view {
  min-height: 100vh;
  background: #eef0f3;
  font-family: 'Inter', 'Segoe UI', 'Roboto', sans-serif;
}

/* ── Page header ───────────────────────────────────────────────────── */
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
.kpi-item   { display: flex; flex-direction: column; align-items: center; padding: 6px 18px; }
.kpi-sep    { width: 1px; background: #334155; align-self: stretch; }
.kpi-val    { font-size: 18px; font-weight: 700; color: #f1f5f9; line-height: 1.2; font-variant-numeric: tabular-nums; }
.kpi-error  { color: #fca5a5; }
.kpi-green  { color: #86efac; }
.kpi-warn   { color: #fde68a; }
.kpi-label  { font-size: 10px; color: #64748b; text-transform: uppercase; letter-spacing: .5px; margin-top: 1px; }

/* ── Body ──────────────────────────────────────────────────────────── */
.body-pad { padding: 20px 24px; }

/* ── Analytics named-area grid ─────────────────────────────────────── */
/*
  Row 1 (3 cols):  [donut compact] [severity medium] [exposure fill]
  Row 2 (2 cols):  [type wide 2fr] [histogram 1fr]
*/
.analysis-grid {
  display: grid;
  grid-template-areas:
    "donut   severity exposure"
    "type    type     histogram";
  grid-template-columns: 210px 1fr 1fr;
  grid-template-rows: auto auto;
  gap: 16px;
  margin-bottom: 20px;
}
.chart-donut     { grid-area: donut;     }
.chart-severity  { grid-area: severity;  }
.chart-exposure  { grid-area: exposure;  }
.chart-type      { grid-area: type;      }
.chart-histogram { grid-area: histogram; }

.chart-card {
  background: #fff;
  border: 1px solid #cbd5e1;
  border-radius: 2px;
  padding: 18px 20px;
  min-height: 200px;
}
.chart-card-title {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .7px;
  color: #64748b;
  margin-bottom: 4px;
}
.chart-card-sub { font-size: 11px; color: #94a3b8; margin-bottom: 14px; }

/* Conformance score badge */
.compliance-score-badge {
  display: inline-flex;
  align-items: center;
  margin-top: 10px;
  font-size: 11px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 12px;
}
.score-ok  { background: #dcfce7; color: #15803d; }
.score-mid { background: #fef3c7; color: #92400e; }
.score-bad { background: #fee2e2; color: #b91c1c; }

/* Severity icon */
.sev-icon { width: 18px; flex-shrink: 0; display: flex; align-items: center; }
.sev-pct  { font-size: 10px; color: #94a3b8; width: 28px; text-align: right; flex-shrink: 0; }

/* Financial exposure risk level pill */
.exp-risk-level {
  display: inline-flex;
  align-items: center;
  font-size: 11px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 12px;
  margin-bottom: 12px;
}
.risk-high { background: #fee2e2; color: #b91c1c; }
.risk-mid  { background: #fef3c7; color: #92400e; }
.risk-low  { background: #dcfce7; color: #15803d; }

/* Invoice type count pill */
.type-count-pill {
  font-size: 10px;
  background: #f1f5f9;
  color: #64748b;
  padding: 1px 6px;
  border-radius: 8px;
  flex-shrink: 0;
  font-weight: 600;
}

/* Shared legend atoms */
.legend-dot       { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; display: inline-block; }
.legend-dot.green { background: #16a34a; }
.legend-dot.red   { background: #dc2626; }
.legend-row       { display: flex; align-items: center; gap: 6px; margin-bottom: 5px; font-size: 12px; color: #475569; }
.no-data          { font-size: 12px; color: #94a3b8; text-align: center; padding: 24px 0; }

/* ── 1. Conformance donut ──────────────────────────────────────────── */
.donut-wrap { position: relative; width: 140px; margin: 10px auto 14px; }
.donut-svg  { width: 140px; height: 140px; }
.donut-center {
  position: absolute; top: 50%; left: 50%;
  transform: translate(-50%,-50%); text-align: center;
}
.donut-pct       { font-size: 26px; font-weight: 700; color: #0f172a; line-height: 1; }
.donut-pct-label { font-size: 9px; color: #64748b; text-transform: uppercase; letter-spacing: .5px; }
.donut-legend    { font-size: 12px; color: #475569; }

/* ── 2. Violations by Severity ─────────────────────────────────────── */
.severity-bars { display: flex; flex-direction: column; gap: 12px; }
.sev-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.sev-icon  { width: 18px; flex-shrink: 0; display: flex; align-items: center; }
.sev-label { font-size: 12px; font-weight: 600; color: #334155; width: 68px; flex-shrink: 0; }
.sev-bar-track {
  flex: 1;
  height: 12px;
  background: #f1f5f9;
  border-radius: 3px;
  overflow: hidden;
}
.sev-bar-fill  { height: 100%; border-radius: 3px; transition: width .45s ease; }
.fill-violation { background: #dc2626; }
.fill-warning   { background: #d97706; }
.fill-info      { background: #2563eb; }
.sev-pct   { font-size: 10px; color: #94a3b8; width: 30px; text-align: right; flex-shrink: 0; }
.sev-count { font-size: 11px; font-weight: 700; color: #334155; width: 36px; text-align: right; flex-shrink: 0; }

/* ── 3. Financial Exposure ─────────────────────────────────────────── */
.exp-hero {
  display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap; margin-bottom: 16px;
}
.exp-risk-amount {
  font-size: 38px; font-weight: 800; color: #dc2626;
  letter-spacing: -1px; font-variant-numeric: tabular-nums; line-height: 1;
}
.exp-risk-meta  { display: flex; flex-direction: column; gap: 4px; }
.exp-risk-badge {
  display: inline-block; background: #fee2e2; color: #dc2626;
  font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 10px;
}
.exp-risk-sub   { font-size: 11px; color: #94a3b8; }
.exp-bar-track  {
  display: flex; height: 14px; border-radius: 3px; overflow: hidden;
  margin-bottom: 12px; background: #f1f5f9;
}
.exp-bar-risk   { background: #dc2626; transition: width .4s; }
.exp-bar-safe   { background: #16a34a; transition: width .4s; }
.exp-legend-row { display: flex; gap: 20px; flex-wrap: wrap; }
.exp-leg-item   { display: flex; align-items: center; gap: 6px; font-size: 12px; color: #475569; }

/* ── 3. Compliance by Invoice Type ─────────────────────────────────── */
.type-bars  { display: flex; flex-direction: column; gap: 10px; margin-bottom: 12px; }
.type-row   { display: flex; align-items: center; gap: 10px; }
.type-label {
  font-size: 11px; font-weight: 600; color: #334155;
  width: 110px; flex-shrink: 0;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.type-stacked-bar {
  flex: 1; height: 18px; display: flex; border-radius: 2px; overflow: hidden; background: #f1f5f9;
}
.type-seg-ok, .type-seg-err {
  display: flex; align-items: center; justify-content: center;
  font-size: 9px; color: #fff; font-weight: 700;
  transition: width .4s; overflow: hidden; white-space: nowrap;
}
.type-seg-ok  { background: #16a34a; }
.type-seg-err { background: #dc2626; }
.type-failure-rate { font-size: 11px; font-weight: 700; width: 36px; text-align: right; flex-shrink: 0; }
.rate-high { color: #dc2626; }
.rate-mid  { color: #d97706; }
.rate-low  { color: #16a34a; }
.type-legend { display: flex; align-items: center; gap: 6px; font-size: 11px; color: #64748b; margin-top: 6px; }

/* ── 4. Violation Load Distribution histogram ──────────────────────── */
/*
   FIX: percentage heights don't resolve inside a flex-direction:column
   container. We use an explicit fixed-height .histo-bar-slot (110px) and
   set the bar height in PIXELS via histoHeightPx() in JS.
*/
.histogram {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  padding-bottom: 0;
  margin-bottom: 10px;
}
.histo-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.histo-bar-slot {
  width: 100%;
  height: 110px;          /* Fixed reference height for px bars */
  display: flex;
  align-items: flex-end;
  justify-content: center;
}
.histo-bar-fill {
  width: 72%;
  border-radius: 3px 3px 0 0;
  min-height: 3px;
  transition: height .45s ease;
}
.fill-ok  { background: #22c55e; }
.fill-err { background: #f87171; }
.histo-count { font-size: 11px; color: #334155; font-weight: 700; margin-top: 4px; }
.histo-label { font-size: 9px; color: #94a3b8; margin-top: 2px; white-space: nowrap; }
.histo-legend {
  display: flex; gap: 16px; font-size: 11px; color: #64748b; align-items: center;
}
.histo-dot {
  display: inline-block; width: 10px; height: 10px;
  border-radius: 2px; margin-right: 4px; vertical-align: middle;
}
.ok-dot  { background: #22c55e; }
.err-dot { background: #f87171; }

/* ── Invoice toolbar ─────────────────────────────────────────────────── */
.inv-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  background: #1e293b; padding: 9px 14px;
  border-radius: 0; gap: 8px; flex-wrap: wrap;
}
.inv-toolbar-left  { display: flex; align-items: center; }
.inv-toolbar-title { font-size: 12px; font-weight: 700; color: #e2e8f0; text-transform: uppercase; letter-spacing: .6px; }
.inv-toolbar-count {
  font-size: 11px; background: rgba(255,255,255,.12); color: #94a3b8;
  padding: 1px 8px; border-radius: 10px; margin-left: 8px; font-weight: 600;
}
.inv-toolbar-right { display: flex; align-items: center; gap: 8px; }

/* Force white text on Vuetify inputs sitting on dark navy background */
.toolbar-input :deep(.v-field__input)                { color: #e2e8f0 !important; font-size: 12px; }
.toolbar-input :deep(.v-select__selection-text)      { color: #e2e8f0 !important; }
.toolbar-input :deep(.v-label)                       { color: #64748b !important; }
.toolbar-input :deep(.v-field)                       { background: rgba(255,255,255,.06) !important; }
.toolbar-input :deep(.v-field__outline__start),
.toolbar-input :deep(.v-field__outline__notch),
.toolbar-input :deep(.v-field__outline__end)         { border-color: #334155 !important; }
.toolbar-input :deep(.v-icon)                        { color: #94a3b8 !important; }

.view-toggle { display: flex; border: 1px solid #334155; border-radius: 3px; overflow: hidden; }
.vt-btn {
  display: flex; align-items: center; justify-content: center;
  padding: 5px 9px; background: transparent; color: #64748b;
  border: none; cursor: pointer; transition: background .15s, color .15s;
}
.vt-btn:hover  { background: rgba(255,255,255,.08); color: #e2e8f0; }
.vt-btn.active { background: #3b82f6; color: #fff; }

/* ── Invoice grid ────────────────────────────────────────────────────── */
.invoice-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1px; background: #cbd5e1;
  border: 1px solid #cbd5e1; border-top: none;
}
.inv-card { background: #fff; padding: 12px 14px; cursor: pointer; transition: background .12s; }
.inv-card:hover { background: #f8fafc; }
.inv-card-error              { border-left: 3px solid #dc2626; }
.inv-card:not(.inv-card-error) { border-left: 3px solid #16a34a; }
.inv-card-top   { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px; }
.inv-card-num   { font-size: 13px; font-weight: 600; color: #0f172a; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 130px; }
.inv-viol-badge { font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 10px; flex-shrink: 0; }
.badge-err { background: #fee2e2; color: #dc2626; }
.badge-ok  { background: #dcfce7; color: #16a34a; }
.inv-card-meta { display: flex; flex-wrap: wrap; gap: 8px; font-size: 11px; color: #64748b; margin-bottom: 4px; }
.inv-card-type { font-size: 10px; color: #94a3b8; text-transform: uppercase; letter-spacing: .4px; }

/* ── Invoice list ────────────────────────────────────────────────────── */
.invoice-list { border: 1px solid #cbd5e1; border-top: none; background: #fff; overflow-x: auto; }
.inv-table    { width: 100%; border-collapse: collapse; font-size: 13px; }
.inv-table thead tr { background: #f1f5f9; }
.inv-table th {
  padding: 8px 12px; font-size: 10px; font-weight: 700;
  text-transform: uppercase; letter-spacing: .6px; color: #64748b;
  border-bottom: 1px solid #e2e8f0; white-space: nowrap; text-align: left;
}
.inv-row                   { cursor: pointer; transition: background .1s; border-bottom: 1px solid #f1f5f9; }
.inv-row:hover > td        { background: #f8fafc; }
.inv-row-error             { border-left: 3px solid #dc2626; }
.inv-row:not(.inv-row-error) { border-left: 3px solid #16a34a; }
.inv-table td  { padding: 9px 12px; color: #334155; vertical-align: middle; }
.inv-td-num    { font-weight: 600; color: #0f172a; }
.text-right    { text-align: right; }
.text-caption.text-slate, .text-slate { color: #64748b; font-size: 12px; }
.font-mono     { font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 12px; }

/* ── Worklist panel ──────────────────────────────────────────────────── */
.worklist-panel {
  background: #fff;
  border: 1px solid #cbd5e1;
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 16px;
}
.worklist-header {
  display: flex;
  align-items: center;
  background: #1e293b;
  padding: 9px 14px;
  gap: 0;
}
.worklist-title {
  font-size: 12px; font-weight: 700; color: #e2e8f0;
  text-transform: uppercase; letter-spacing: .6px;
}
.worklist-count {
  font-size: 11px; background: rgba(255,255,255,.12); color: #94a3b8;
  padding: 1px 8px; border-radius: 10px; margin-left: 8px; font-weight: 600;
}
.worklist-sub { font-size: 11px; color: #475569; margin-left: 16px; }
.worklist-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.worklist-table thead tr { background: #f8fafc; }
.worklist-table th {
  padding: 7px 12px; font-size: 10px; font-weight: 700;
  text-transform: uppercase; letter-spacing: .6px; color: #64748b;
  border-bottom: 1px solid #e2e8f0; text-align: left; white-space: nowrap;
}
.wl-th-rank { width: 44px; text-align: center; }
.wl-row {
  cursor: pointer;
  border-bottom: 1px solid #f1f5f9;
  border-left: 3px solid #dc2626;
  transition: background .1s;
}
.wl-row:last-child { border-bottom: none; }
.wl-row:hover > td { background: #fff5f5; }
.worklist-table td { padding: 8px 12px; vertical-align: middle; color: #334155; }
.wl-td-rank { text-align: center; }
.wl-rank-num {
  display: inline-flex; align-items: center; justify-content: center;
  width: 22px; height: 22px; border-radius: 50%;
  font-size: 11px; font-weight: 700; background: #f1f5f9; color: #475569;
}
.rank-top3   { background: #fef3c7; color: #92400e; }
.wl-doc-num  { font-weight: 600; color: #0f172a; }
.wl-counterparty { display: flex; align-items: center; gap: 4px; margin-top: 2px; flex-wrap: nowrap; overflow: hidden; }
.wl-cp-supplier  { font-size: 10px; font-weight: 500; color: #475569; max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.wl-cp-buyer     { font-size: 10px; color: #94a3b8; max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.wl-cp-sep       { font-size: 10px; color: #cbd5e1; flex-shrink: 0; }
.wl-type     { font-size: 12px; color: #64748b; }
.wl-amount   { font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 12px; color: #334155; }
.wl-viol-pill {
  font-size: 11px; font-weight: 700; padding: 2px 9px; border-radius: 10px;
}
.pill-critical { background: #fecaca; color: #b91c1c; }
.pill-high     { background: #fed7aa; color: #c2410c; }
.pill-med      { background: #fef3c7; color: #92400e; }
.wl-status-badge {
  font-size: 10px; font-weight: 700; padding: 2px 8px;
  border-radius: 10px; white-space: nowrap;
}
.wlb-critical { background: #fee2e2; color: #b91c1c; }
.wlb-high     { background: #ffedd5; color: #c2410c; }
.wlb-review   { background: #fef3c7; color: #92400e; }

/* ── Filter bar ──────────────────────────────────────────────────────── */
.filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 2px 2px 0 0;
  padding: 8px 14px;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 0;
}
.filter-bar-left { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.filter-label { font-size: 11px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: .4px; }
.filter-chip {
  display: inline-flex; align-items: center;
  font-size: 11px; color: #475569;
  background: #fff; border: 1px solid #cbd5e1;
  border-radius: 12px; padding: 3px 10px; cursor: pointer;
  transition: background .12s, border-color .12s, color .12s;
  white-space: nowrap;
}
.filter-chip:hover { border-color: #94a3b8; color: #0f172a; }
.chip-active { background: #3b82f6; border-color: #3b82f6; color: #fff; }
.filter-select :deep(.v-field__input)  { font-size: 12px; }
.clear-filters-btn {
  display: inline-flex; align-items: center;
  font-size: 11px; color: #94a3b8;
  background: transparent; border: 1px solid #e2e8f0;
  border-radius: 12px; padding: 3px 10px; cursor: pointer;
  transition: color .12s, border-color .12s;
  white-space: nowrap;
}
.clear-filters-btn:hover { color: #dc2626; border-color: #dc2626; }

/* ── Top Failing Suppliers panel ─────────────────────────────────────────── */
.top-failing-panel {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 2px;
  padding: 12px 16px;
  margin-bottom: 12px;
}
.tfp-header {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
  gap: 4px;
}
.tfp-title   { font-size: 11px; font-weight: 700; color: #334155; text-transform: uppercase; letter-spacing: .5px; }
.tfp-tabs    { display: flex; border: 1px solid #e2e8f0; border-radius: 3px; overflow: hidden; margin-left: 10px; }
.tfp-tab     { font-size: 10px; font-weight: 600; color: #64748b; background: transparent; border: none; padding: 2px 9px; cursor: pointer; transition: background .1s, color .1s; }
.tfp-tab:hover  { background: #f1f5f9; }
.tfpt-active    { background: #1e293b !important; color: #fff !important; }
.tfp-sub     { font-size: 11px; color: #94a3b8; margin-left: 8px; }
.tfp-list    { display: flex; flex-direction: column; gap: 7px; }
.tfp-row     { display: flex; align-items: center; gap: 10px; }
.tfp-name    { font-size: 11px; color: #334155; font-weight: 500; width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex-shrink: 0; }
.tfp-bar-wrap { flex: 1; height: 8px; background: #f1f5f9; border-radius: 2px; overflow: hidden; }
.tfp-bar     { height: 100%; border-radius: 2px; transition: width .4s; }
.tfpb-red    { background: #dc2626; }
.tfpb-amber  { background: #d97706; }
.tfpb-green  { background: #16a34a; }
.tfp-rate    { font-size: 11px; font-weight: 700; width: 34px; text-align: right; flex-shrink: 0; }
.tfpr-red    { color: #dc2626; }
.tfpr-amber  { color: #d97706; }
.tfpr-green  { color: #16a34a; }
.tfp-count   { font-size: 11px; color: #94a3b8; width: 40px; text-align: right; flex-shrink: 0; }

.wl-risk-score { min-width: 72px; }
.wl-score-pill { display: inline-block; font-size: 11px; font-weight: 800; border-radius: 3px; padding: 1px 6px; font-variant-numeric: tabular-nums; }
.wlsc-red   { background: #fee2e2; color: #b91c1c; }
.wlsc-amber { background: #fef3c7; color: #92400e; }
.wlsc-blue  { background: #dbeafe; color: #1d4ed8; }

/* ── Worklist sort toggle ─────────────────────────────────────────────── */
.wl-sort-toggle { display: flex; margin-left: auto; border: 1px solid #334155; border-radius: 3px; overflow: hidden; flex-shrink: 0; }
.wls-btn  { font-size: 10px; font-weight: 600; color: #64748b; background: transparent; border: none; padding: 3px 10px; cursor: pointer; transition: background .12s, color .12s; white-space: nowrap; }
.wls-btn:hover { background: rgba(255,255,255,.08); color: #e2e8f0; }
.wls-active    { background: #3b82f6 !important; color: #fff !important; }
</style>
