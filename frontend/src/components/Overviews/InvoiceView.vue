<template>
  <div class="invoice-view">

    <!-- Page header bar -->
    <div class="page-header">
      <div class="d-flex align-center gap-2">
        <v-btn icon="mdi-arrow-left" variant="text" size="small" color="white" @click="router.push('/')" title="Back to Dashboard" />
        <div class="page-header-breadcrumb">
          <span class="page-header-title">Invoice Detail</span>
          <span class="page-header-sub" v-if="summary.documentNumber">&nbsp;/&nbsp;{{ summary.documentNumber }}</span>
        </div>
      </div>
      <div class="d-flex align-center gap-2">
        <button class="print-btn" @click="printInvoice" title="Print / Export as PDF">
          <v-icon size="16">mdi-printer-outline</v-icon>
          <span>Print / PDF</span>
        </button>
        <div class="compliance-badge" :class="compliance.conforms ? 'badge-ok' : 'badge-fail'">
          <v-icon size="14" class="mr-1">{{ compliance.conforms ? 'mdi-check-circle' : 'mdi-alert-circle' }}</v-icon>
          {{ compliance.conforms ? 'Conforms' : 'Does Not Conform' }}
        </div>
        <div v-for="s in compliance.bySeverity" :key="s.severity" class="severity-pill" :class="'pill-' + s.severity.toLowerCase()">
          {{ s.count }} {{ s.severity }}
        </div>
      </div>
    </div>

    <div class="invoice-page-body">

    <!-- ── PROCESSING STATUS STRIP ───────────────────────────────────── -->
    <div class="status-strip" :class="'status-' + processingStatus.code">
      <div class="status-strip-left">
        <div class="status-badge" :class="'sbadge-' + processingStatus.code">
          <v-icon size="15" class="mr-1">{{ processingStatus.icon }}</v-icon>
          {{ processingStatus.label }}
        </div>
        <div class="status-summary">{{ plainLanguageSummary }}</div>
      </div>
      <div class="status-strip-right">
        <div v-if="blockingCount > 0" class="status-kpi status-kpi-block">
          <div class="status-kpi-val">{{ blockingCount }}</div>
          <div class="status-kpi-lbl">Blocking Issue{{ blockingCount !== 1 ? 's' : '' }}</div>
        </div>
        <div v-if="warningCount > 0" class="status-kpi status-kpi-warn">
          <div class="status-kpi-val">{{ warningCount }}</div>
          <div class="status-kpi-lbl">Warning{{ warningCount !== 1 ? 's' : '' }}</div>
        </div>
        <div v-if="infoCount > 0" class="status-kpi status-kpi-info">
          <div class="status-kpi-val">{{ infoCount }}</div>
          <div class="status-kpi-lbl">Info</div>
        </div>
        <div class="status-kpi status-kpi-amount">
          <div class="status-kpi-val">{{ summary.invoiceAmount ? fmtEur(summary.invoiceAmount) : '-' }}</div>
          <div class="status-kpi-lbl">Invoice Total</div>
        </div>
      </div>
    </div>

    <!-- ── ACTIONS NEEDED ────────────────────────────────────────────── -->
    <div class="actions-panel" v-if="actionsNeeded.length">
      <div class="actions-header">
        <v-icon size="15" color="#b45309" class="mr-1">mdi-clipboard-list-outline</v-icon>
        <span>Actions Needed</span>
      </div>
      <ul class="actions-list">
        <li v-for="(action, i) in actionsNeeded" :key="i" class="action-item">
          <span class="action-dot" :class="'adot-' + action.level"></span>
          <div class="action-body">
            <span class="action-text">{{ action.text }}</span>
            <span v-if="action.why" class="action-why">Why this matters: {{ action.why }}</span>
          </div>
        </li>
      </ul>
    </div>

    <!-- PAPER INVOICE -->
    <div class="paper-invoice">

      <!-- Invoice title bar -->
      <div class="inv-title-bar">
        <div class="inv-title-left">
          <span class="inv-title">INVOICE</span>
          <span class="inv-type" v-if="summary.documentType">{{ summary.documentType }}</span>
        </div>
        <div class="inv-title-right">
          <div class="inv-docnum-label">Document No.</div>
          <div class="inv-docnum">
            <ViolationWrap :violations="fieldViolations('documentNumber')">{{ summary.documentNumber || '-' }}</ViolationWrap>
          </div>
        </div>
      </div>

      <!-- Header: Supplier left, Meta centre, Buyer right -->
      <div class="inv-header">

        <!-- Supplier -->
        <div class="inv-party" v-if="supplier" v-show="!showAffectedOnly || affectedSections.has('Supplier')">
          <span class="inv-section-label">FROM (Supplier)</span>
          <div class="inv-party-name">
            <ViolationWrap :violations="partyFieldViolations(supplier.uri)">{{ supplier.name || supplier.gln || '-' }}</ViolationWrap>
          </div>
          <div v-if="supplier.street" class="inv-party-line">{{ supplier.street }}</div>
          <div v-if="supplier.city" class="inv-party-line">
            {{ [supplier.postalCode, supplier.city, supplier.countryCode].filter(Boolean).join(' ') }}
          </div>
          <div v-if="supplier.vat" class="inv-party-line">VAT: {{ supplier.vat }}</div>
          <div v-if="supplier.gln" class="inv-party-line text-mono">GLN: {{ supplier.gln }}</div>
        </div>

        <!-- Invoice meta -->
        <div class="inv-meta">
          <table class="inv-meta-table">
            <tr v-for="f in invoiceMetaFields" :key="f.label">
              <td class="inv-meta-label">{{ f.label }}</td>
              <td class="inv-meta-value">
                <ViolationWrap :violations="fieldViolations(f.path)">{{ f.value || '-' }}</ViolationWrap>
              </td>
            </tr>
          </table>
        </div>

        <!-- Buyer -->
        <div class="inv-party" v-if="buyer" v-show="!showAffectedOnly || affectedSections.has('Buyer')">
          <span class="inv-section-label">TO (Buyer)</span>
          <div class="inv-party-name">
            <ViolationWrap :violations="partyFieldViolations(buyer.uri)">{{ buyer.name || buyer.gln || '-' }}</ViolationWrap>
          </div>
          <div v-if="buyer.street" class="inv-party-line">{{ buyer.street }}</div>
          <div v-if="buyer.city" class="inv-party-line">
            {{ [buyer.postalCode, buyer.city, buyer.countryCode].filter(Boolean).join(' ') }}
          </div>
          <div v-if="buyer.vat" class="inv-party-line">VAT: {{ buyer.vat }}</div>
          <div v-if="buyer.gln" class="inv-party-line text-mono">GLN: {{ buyer.gln }}</div>
        </div>

      </div>

      <!-- Other parties strip -->
      <div v-if="otherParties.length" class="inv-other-parties">
        <div v-for="party in otherParties" :key="party.uri" class="inv-other-party">
          <span class="inv-section-label">{{ party.roles.map(r => r.replace('Role','')).join(' / ') }}</span>
          <span class="ml-2">
            <ViolationWrap :violations="partyFieldViolations(party.uri)">{{ party.name || party.gln || '-' }}</ViolationWrap>
          </span>
          <span v-if="party.city" class="text-caption text-medium-emphasis ml-2">
            {{ [party.city, party.countryCode].filter(Boolean).join(', ') }}
          </span>
        </div>
      </div>

      <!-- Line items -->
      <table class="inv-items-table" v-show="!showAffectedOnly || affectedSections.has('Line Items')">
        <thead>
          <tr>
            <th class="col-pos">#</th>
            <th class="col-desc">Description</th>
            <th class="col-ean">EAN / Part#</th>
            <th class="col-qty">Qty</th>
            <th class="col-unit">Unit</th>
            <th class="col-price">Unit Price</th>
            <th class="col-vat">VAT%</th>
            <th class="col-total">Total</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, idx) in items" :key="item.uri"
            :class="{ 'row-violation': itemHasViolation(item.uri) }"
            @mouseenter="itemHasViolation(item.uri) && showTooltip($event, violationsByNode[item.uri])"
            @mouseleave="tooltip.visible = false">
            <td class="col-pos text-medium-emphasis text-caption">
              {{ idx + 1 }}
              <span v-if="itemHasViolation(item.uri)" class="row-viol-badge"
                :title="violationsByNode[item.uri].length + ' issue(s)'">
                {{ violationsByNode[item.uri].length }}
              </span>
            </td>
            <td class="col-desc">
              <ViolationWrap :violations="itemViolations(item.uri, 'itemName')">
                <span class="font-weight-medium">{{ item.itemName || item.description || '-' }}</span>
              </ViolationWrap>
              <div v-if="item.description && item.itemName" class="text-caption text-medium-emphasis">{{ item.description }}</div>
            </td>
            <td class="col-ean text-caption text-mono">
              <ViolationWrap :violations="itemViolations(item.uri, 'internationalArticleNumber')">{{ item.ean || '-' }}</ViolationWrap>
              <div v-if="item.partNumberBuyer" class="text-caption text-medium-emphasis">{{ item.partNumberBuyer }}</div>
            </td>
            <td class="col-qty inv-cell-right">
              <ViolationWrap :violations="itemViolations(item.uri, 'invoicedQuantity')">{{ item.quantity ?? '-' }}</ViolationWrap>
            </td>
            <td class="col-unit text-caption text-medium-emphasis">{{ item.unit || '-' }}</td>
            <td class="col-price inv-cell-right">
              <ViolationWrap :violations="itemViolations(item.uri, 'hasGrosspriceOfItem')">{{ item.grossPrice != null ? fmtNum(item.grossPrice) : '-' }}</ViolationWrap>
            </td>
            <td class="col-vat inv-cell-right">
              <ViolationWrap :violations="itemViolations(item.uri, 'hasVATrate')">{{ item.vatRate != null ? item.vatRate + '%' : '-' }}</ViolationWrap>
            </td>
            <td class="col-total inv-cell-right font-weight-medium">
              <ViolationWrap :violations="itemViolations(item.uri, 'hasTotalGoodsPosition')">{{ item.totalGoodsPosition != null ? fmtNum(item.totalGoodsPosition) : '-' }}</ViolationWrap>
            </td>
          </tr>
          <tr v-if="!items.length">
            <td colspan="8" class="text-center text-medium-emphasis py-3">No items</td>
          </tr>
        </tbody>
      </table>

      <!-- Totals -->
      <div class="inv-totals" v-show="!showAffectedOnly || affectedSections.has('Totals & Tax')">
        <table class="inv-totals-table">
          <tr v-for="f in financialTotals" :key="f.label" :class="{ 'totals-grand': f.grand }">
            <td class="totals-label">{{ f.label }}</td>
            <td class="totals-value">
              <ViolationWrap :violations="fieldViolations(f.path)">{{ fmtNum(f.value) }}</ViolationWrap>
            </td>
          </tr>
        </table>
      </div>

      <!-- Notes / payment -->
      <div v-if="summary.paymentCondition || summary.supplierNote || summary.dueDate" class="inv-notes">
        <div v-if="summary.dueDate" class="inv-note-row">
          <span class="inv-note-label">Due Date:</span>
          <ViolationWrap :violations="fieldViolations('dueDate')">{{ summary.dueDate }}</ViolationWrap>
        </div>
        <div v-if="summary.paymentCondition" class="inv-note-row">
          <span class="inv-note-label">Payment Terms:</span>
          <ViolationWrap :violations="fieldViolations('paymentCondition')">{{ summary.paymentCondition }}</ViolationWrap>
        </div>
        <div v-if="summary.supplierNote" class="inv-note-row">
          <span class="inv-note-label">Note:</span>
          <ViolationWrap :violations="fieldViolations('supplierNote')">{{ summary.supplierNote }}</ViolationWrap>
        </div>
      </div>

    </div><!-- /paper-invoice -->

    <!-- ── ISSUES PANEL (grouped by business section) ─────────────────── -->
    <div class="issues-panel" v-if="violations.length" style="margin-top:16px">
      <div class="issues-header">
        <div class="d-flex align-center gap-2">
          <v-icon size="16" color="#e2e8f0">mdi-format-list-checks</v-icon>
          <span class="issues-title">Validation Issues</span>
          <span class="issues-count">{{ violations.length }}</span>
        </div>
        <div class="d-flex align-center gap-2">
          <v-text-field v-model="violationSearch" placeholder="Search issues..."
            prepend-inner-icon="mdi-magnify" density="compact" variant="outlined"
            hide-details class="toolbar-input" style="max-width:240px" />
          <button class="tech-toggle" @click="showTechnical = !showTechnical">
            <v-icon size="13" class="mr-1">mdi-code-tags</v-icon>
            {{ showTechnical ? 'Hide' : 'Show' }} technical detail
          </button>
          <button class="affected-toggle" :class="{ 'aff-active': showAffectedOnly }" @click="showAffectedOnly = !showAffectedOnly">
            <v-icon size="13" class="mr-1">mdi-filter-variant</v-icon>
            {{ showAffectedOnly ? 'Showing affected sections' : 'Focus affected sections' }}
          </button>
        </div>
      </div>

      <div v-for="group in groupedIssues" :key="group.section" class="issue-group">
        <div class="issue-group-header">
          <v-icon size="14" class="mr-1" :color="group.iconColor">{{ group.icon }}</v-icon>
          {{ group.section }}
          <span class="ig-count">
            <span v-if="group.blocking" class="ig-block">{{ group.blocking }} blocking</span>
            <span v-if="group.warnings" class="ig-warn">{{ group.warnings }} warning{{ group.warnings !== 1 ? 's' : '' }}</span>
          </span>

        </div>
        <div v-for="(v, i) in group.items" :key="i" class="issue-row"
          :class="'irow-' + v.severity.toLowerCase()">
          <div class="issue-row-left">
            <div class="issue-severity-dot" :class="'idot-' + v.severity.toLowerCase()"></div>
            <div class="issue-content">
              <div class="issue-title">{{ v.businessLabel }}</div>
              <div class="issue-desc">{{ v.businessMessage }}</div>
              <div v-if="showTechnical" class="issue-technical">
                <span>{{ v.shapeName }}</span>
                <span v-if="v.resultPathShort"> · {{ v.resultPathShort }}</span>
                <span v-if="v.constraintComponent"> · {{ v.constraintComponent }}</span>
                <span v-if="v.actualValuesInData && v.actualValuesInData.length" class="tech-value"> · value: {{ v.actualValuesInData.join(', ') }}</span>
              </div>
            </div>
          </div>
          <div class="issue-severity-label" :class="'isev-' + v.severity.toLowerCase()">
            {{ v.severity === 'Violation' ? 'Blocking' : v.severity === 'Warning' ? 'Warning' : 'Info' }}
          </div>
        </div>
      </div>

      <div v-if="!groupedIssues.length" class="text-center text-medium-emphasis py-4">
        No issues match filter
      </div>
    </div>

    </div><!-- /invoice-page-body -->

  </div>

  <!-- Violation tooltip overlay -->
  <v-menu
    v-model="tooltip.visible"
    :target="tooltip.anchor"
    location="top"
    open-on-hover
    :close-delay="200"
    :open-delay="0"
    max-width="400"
  >
    <v-card elevation="4" rounded="lg" class="pa-3" style="max-width:400px">
      <div v-for="(viol, i) in tooltip.violations" :key="i" :class="i > 0 ? 'mt-2 pt-2' : ''">
        <v-chip :color="severityChipColor(viol.severity)" size="x-small" variant="flat" class="mb-1">{{ viol.severity }}</v-chip>
        <div class="text-caption font-weight-medium">{{ viol.shapeName }}</div>
        <div v-if="viol.resultPathShort" class="text-caption text-medium-emphasis">Path: {{ viol.resultPathShort }}</div>
        <div v-if="viol.constraintComponent" class="text-caption text-medium-emphasis">{{ viol.constraintComponent }}</div>
        <div v-if="viol.message" class="text-caption mt-1">{{ viol.message }}</div>
        <div v-if="viol.actualValuesInData && viol.actualValuesInData.length" class="text-caption text-success mt-1">
          Present: {{ viol.actualValuesInData.join(', ') }}
        </div>
        <div v-else class="text-caption text-error mt-1">Value missing in data graph</div>
      </div>
    </v-card>
  </v-menu>
</template>

<script setup>
import { ref, computed, onMounted, defineComponent, h } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { getInvoiceDetail } from '@/services/api.js';

const route = useRoute();
const router = useRouter();
const invoiceUri = computed(() => route.query.uri || null);

const summary = ref({});
const parties = ref([]);
const items = ref([]);
const violationsByShape = ref([]);
const violations = ref([]);
const compliance = ref({ totalViolations: 0, bySeverity: [], affectedFocusNodes: 0, affectedPaths: 0 });
const violationSearch = ref('');
const showTechnical    = ref(false);
const showAffectedOnly = ref(false);
function printInvoice() { window.print(); }
const fmtNum = (v) => (v != null ? parseFloat(v).toFixed(2) : '-');
const fmtEur = (v) => {
  const n = parseFloat(v);
  if (!v || isNaN(n)) return '€0';
  if (n >= 1_000_000) return '€' + (n / 1_000_000).toFixed(2) + 'M';
  if (n >= 1_000) return '€' + (n / 1_000).toFixed(1) + 'K';
  return '€' + n.toFixed(2);
};

onMounted(async () => {
  const uri = invoiceUri.value;
  const detail = await getInvoiceDetail(uri).catch(() => ({}));
  summary.value = detail.summary || {};
  parties.value = detail.parties || [];
  items.value = detail.items || [];
  violationsByShape.value = detail.violationsByShape || [];
  violations.value = detail.violations || [];
  compliance.value = detail.compliance || { totalViolations: 0, bySeverity: [], affectedFocusNodes: 0, affectedPaths: 0 };
});

// Party helpers
// Supplier: prefer the role node that has a name.
// In msg_0014 that is SupplierRole; in msg_0026 that is PayeeRole.
const supplier = computed(() =>
  parties.value.find(p => p.roles.includes('SupplierRole') && p.name) ||
  parties.value.find(p => p.roles.includes('PayeeRole')    && p.name) ||
  parties.value.find(p => p.roles.includes('SupplierRole')) ||
  parties.value.find(p => p.roles.includes('PayeeRole'))
);
// Buyer: InvoiceeRole carries name+address in both datasets; BuyerRole only has a GLN.
const buyer = computed(() =>
  parties.value.find(p => p.roles.includes('InvoiceeRole') && p.name) ||
  parties.value.find(p => p.roles.includes('BuyerRole')    && p.name) ||
  parties.value.find(p => p.roles.includes('InvoiceeRole')) ||
  parties.value.find(p => p.roles.includes('BuyerRole'))
);
// Any remaining parties that weren't chosen as the main supplier/buyer.
const otherParties = computed(() => {
  const used = new Set([supplier.value?.uri, buyer.value?.uri].filter(Boolean));
  return parties.value.filter(p => !used.has(p.uri));
});

// Field lists
const invoiceMetaFields = computed(() => [
  { label: 'Date',       value: summary.value.documentDate,         path: 'documentDate' },
  { label: 'Type',       value: summary.value.documentType,         path: 'hasDocumentType' },
  { label: 'Order #',    value: summary.value.orderNumberBuyer,     path: 'orderNumberBuyer' },
  { label: 'Order Date', value: summary.value.dateOrderNumberBuyer, path: 'dateOrderNumberBuyer' },
  { label: 'Delivery',   value: summary.value.deliveryDate,         path: 'actualDeliveryDate' },
  { label: 'Currency',   value: summary.value.currency || summary.value.invoiceCurrency, path: 'currency' },
].filter(f => f.value));

const financialTotals = computed(() => [
  { label: 'Subtotal (Line Items)', value: summary.value.totalLineItemAmount, path: 'hasTotalLineItemAmount' },
  { label: 'Discount',              value: summary.value.discountAmount,      path: 'hasDiscountAmount' },
  { label: 'Charge',                value: summary.value.chargeAmount,        path: 'hasChargeAmount' },
  { label: 'Freight',               value: summary.value.freightCharge,       path: 'hasFreightCharge' },
  { label: 'Taxable Amount',        value: summary.value.taxableAmount,       path: 'hasTaxableAmount' },
  { label: 'VAT (' + (summary.value.vatRate || '-') + '%)', value: summary.value.vatAmount, path: 'hasVATamount' },
  { label: 'TOTAL', value: summary.value.invoiceAmount, path: 'hasInvoiceAmount', grand: true },
].filter(f => f.value != null));

// Violation maps
const violationsByNode = computed(() => {
  const map = {};
  for (const v of violations.value) {
    (map[v.focusNode] = map[v.focusNode] || []).push(v);
  }
  return map;
});

const partyFieldViolations = (uri) => violationsByNode.value[uri] || [];

const itemViolations = (uri, pathKeyword) => {
  const all = violationsByNode.value[uri] || [];
  return all.filter(v => v.resultPath && v.resultPath.includes(pathKeyword));
};

const itemHasViolation = (uri) => (violationsByNode.value[uri] || []).length > 0;

const fieldViolations = (pathKeyword) =>
  violations.value.filter(v => v.resultPath && v.resultPath.includes(pathKeyword));

// Tooltip
const tooltip = ref({ visible: false, anchor: null, violations: [] });
function showTooltip(event, viols) {
  if (!viols.length) return;
  tooltip.value = { visible: true, anchor: event.currentTarget, violations: viols };
}

// ViolationWrap inline component
const ViolationWrap = defineComponent({
  props: { violations: { type: Array, default: () => [] } },
  setup(props, { slots }) {
    return () => {
      const hasV = props.violations.length > 0;
      if (!hasV) return slots.default?.();
      return h('span', {
        class: 'violation-field',
        title: props.violations.map(v =>
          '[' + v.severity + '] ' + v.shapeName + (v.message ? ': ' + v.message : '')
        ).join('\n'),
        onMouseenter: (e) => showTooltip(e, props.violations),
        onMouseleave: () => { tooltip.value.visible = false; },
        onClick: (e) => showTooltip(e, props.violations),
      }, [
        slots.default?.(),
        h('span', { class: 'violation-icon', style: 'font-size:10px;margin-left:2px;' }, ' ⚠'),
      ]);
    };
  },
});

// ── Processing status ────────────────────────────────────────────────────────
const blockingCount = computed(() =>
  violations.value.filter(v => v.severity === 'Violation').length
);
const warningCount = computed(() =>
  violations.value.filter(v => v.severity === 'Warning').length
);
const infoCount = computed(() =>
  violations.value.filter(v => v.severity === 'Info').length
);

const processingStatus = computed(() => {
  if (compliance.value.conforms)
    return { code: 'ready',    label: 'Ready to Process',     icon: 'mdi-check-circle-outline' };
  if (blockingCount.value > 0)
    return { code: 'blocked',  label: 'Cannot Be Processed',  icon: 'mdi-alert-circle-outline' };
  return   { code: 'review',   label: 'Needs Review',         icon: 'mdi-alert-outline' };
});

// ── Plain-language summary sentence ─────────────────────────────────────────
const PLAIN_LABELS = {
  documentNumber: 'invoice number',
  documentDate: 'invoice date',
  orderNumberBuyer: 'buyer order number',
  dateOrderNumberBuyer: 'buyer order date',
  dueDate: 'due date',
  currency: 'currency',
  invoiceAmount: 'invoice total',
  vatAmount: 'VAT amount',
  vatRate: 'VAT rate',
  invoicedQuantity: 'quantity',
  hasGrosspriceOfItem: 'unit price',
  hasTotalGoodsPosition: 'line total',
  internationalArticleNumber: 'EAN / article number',
  itemName: 'item name',
  hasTotalLineItemAmount: 'subtotal',
  paymentCondition: 'payment terms',
};

function pathToLabel(path) {
  if (!path) return 'a field';
  for (const [key, label] of Object.entries(PLAIN_LABELS)) {
    if (path.includes(key)) return label;
  }
  const last = path.split(/[/#]/).filter(Boolean).pop() || path;
  return last.replace(/([A-Z])/g, ' $1').toLowerCase().trim();
}

const plainLanguageSummary = computed(() => {
  if (compliance.value.conforms || !violations.value.length)
    return 'This invoice passes all validation checks and is ready for processing.';
  const blockers = violations.value.filter(v => v.severity === 'Violation');
  const lineItemIssues = blockers.filter(v => items.value.some(i => v.focusNode === i.uri));
  const headerIssues = blockers.filter(v => !items.value.some(i => v.focusNode === i.uri));
  const parts = [];
  if (headerIssues.length) {
    const fields = [...new Set(headerIssues.map(v => pathToLabel(v.resultPath)))].slice(0, 3);
    parts.push(fields.join(', ') + ' ' + (fields.length === 1 ? 'is' : 'are') + ' missing or invalid');
  }
  if (lineItemIssues.length) {
    const affectedItems = new Set(lineItemIssues.map(v => v.focusNode)).size;
    parts.push(affectedItems + ' line item' + (affectedItems !== 1 ? 's have' : ' has') + ' data errors');
  }
  if (!parts.length && warningCount.value > 0)
    return 'This invoice has ' + warningCount.value + ' warning' + (warningCount.value !== 1 ? 's' : '') + ' that should be reviewed before processing.';
  return 'This invoice cannot be processed: ' + parts.join(' and ') + '.';
});

// ── Actions needed ───────────────────────────────────────────────────────────
const ACTION_MAP = [
  { match: 'orderNumberBuyer',     level: 'block', text: 'Enter the buyer order number',                      why: 'Invoice cannot be matched to a purchase order (PO) without this.' },
  { match: 'dateOrderNumberBuyer', level: 'block', text: 'Enter the buyer order date',                        why: 'Required to verify the PO reference is current and valid.' },
  { match: 'documentDate',         level: 'block', text: 'Enter or correct the invoice date',                 why: 'Mandatory for legal compliance and payment scheduling.' },
  { match: 'documentNumber',       level: 'block', text: 'Enter or correct the invoice number',               why: 'The unique invoice identifier is required for processing and archiving.' },
  { match: 'dueDate',              level: 'block', text: 'Set the payment due date',                          why: 'Accounts payable cannot schedule payment without a due date.' },
  { match: 'currency',             level: 'block', text: 'Specify the invoice currency',                      why: 'Ambiguous currency prevents correct financial booking.' },
  { match: 'invoiceAmount',        level: 'block', text: 'Correct the invoice total amount',                  why: 'The total must match the sum of line items plus charges.' },
  { match: 'vatAmount',            level: 'block', text: 'Correct or enter the VAT amount',                   why: 'Incorrect VAT creates tax compliance liabilities.' },
  { match: 'vatRate',              level: 'warn',  text: 'Verify the VAT rate on affected items',             why: 'Wrong rate may result in over- or underpayment of tax.' },
  { match: 'hasGrosspriceOfItem',  level: 'block', text: 'Correct unit price on flagged line items',          why: 'Line totals cannot be verified without a valid unit price.' },
  { match: 'invoicedQuantity',     level: 'block', text: 'Enter quantity for flagged line items',              why: 'Quantity is required to calculate and validate the line total.' },
  { match: 'hasTotalGoodsPosition',level: 'warn',  text: 'Verify line totals match quantity × unit price',    why: 'A discrepancy triggers a payment hold during three-way matching.' },
  { match: 'internationalArticleNumber', level: 'warn', text: 'Add EAN / article number on flagged items',   why: 'Article number is required for automated goods receipt matching.' },
  { match: 'itemName',             level: 'block', text: 'Enter item description on flagged line items',      why: 'Item description is legally required on the invoice document.' },
  { match: 'hasTotalLineItemAmount', level: 'warn', text: 'Verify subtotal equals sum of line items',         why: 'A subtotal mismatch indicates a calculation error.' },
  { match: 'PaymentCondition',     level: 'warn',  text: 'Review or enter payment terms',                     why: 'Missing payment terms may delay early-payment discount eligibility.' },
  { match: 'SupplierRole',         level: 'block', text: 'Complete supplier information (name, address, or GLN)', why: 'Supplier identity must be verifiable for legal and payment purposes.' },
  { match: 'BuyerRole',            level: 'block', text: 'Complete buyer information (name, address, or GLN)',  why: 'Buyer identity is required for correct routing and financial booking.' },
];

const actionsNeeded = computed(() => {
  const seen = new Set();
  const result = [];
  for (const v of violations.value) {
    const path = (v.resultPath || '') + (v.focusNode || '') + (v.shapeName || '');
    for (const rule of ACTION_MAP) {
      if (path.includes(rule.match) && !seen.has(rule.match)) {
        seen.add(rule.match);
        result.push({ level: rule.level, text: rule.text, why: rule.why });
      }
    }
  }
  // Sort: blocking first
  return result.sort((a, b) => (a.level === 'block' ? -1 : 1) - (b.level === 'block' ? -1 : 1));
});

// ── Section grouping ─────────────────────────────────────────────────────────
const SECTION_MAP = [
  { section: 'Invoice Header',  icon: 'mdi-file-document-outline',          iconColor: '#3b82f6', patterns: ['documentNumber','documentDate','documentType','orderNumber','currency','dueDate','paymentCondition','supplierNote','deliveryDate','totalLine','Invoice'], nextStep: 'Fix in ERP',       nextStepIcon: 'mdi-wrench-outline'   },
  { section: 'Supplier',        icon: 'mdi-office-building-outline',         iconColor: '#8b5cf6', patterns: ['SupplierRole','PayeeRole','supplier','Supplier'],                                                                                                       nextStep: 'Contact supplier', nextStepIcon: 'mdi-phone-outline'    },
  { section: 'Buyer',           icon: 'mdi-account-outline',                 iconColor: '#0ea5e9', patterns: ['BuyerRole','InvoiceeRole','buyer','Buyer'],                                                                                                                nextStep: 'Fix in ERP',       nextStepIcon: 'mdi-wrench-outline'   },
  { section: 'Line Items',      icon: 'mdi-format-list-bulleted',            iconColor: '#f59e0b', patterns: ['Item','item','invoicedQuantity','GoodsPosition','GrossPrice','VATrate','ArticleNumber'],                                                                    nextStep: 'Contact supplier', nextStepIcon: 'mdi-phone-outline'    },
  { section: 'Totals & Tax',    icon: 'mdi-calculator-variant-outline',      iconColor: '#10b981', patterns: ['TotalAmount','vatAmount','vatRate','taxable','charge','discount','freight','Amount'],                                                                      nextStep: 'Review manually',  nextStepIcon: 'mdi-eye-outline'      },
  { section: 'Other',           icon: 'mdi-dots-horizontal-circle-outline',  iconColor: '#64748b', patterns: [],                                                                                                                                                          nextStep: 'Accept warning',   nextStepIcon: 'mdi-check-outline'    },
];

function classifyViolation(v) {
  const haystack = (v.resultPath || '') + (v.shapeName || '') + (v.focusNodeTypeShort || '');
  for (const sec of SECTION_MAP.slice(0, -1)) {
    if (sec.patterns.some(p => haystack.includes(p))) return sec.section;
  }
  return 'Other';
}

function toBusinessViolation(v) {
  const path = v.resultPath || '';
  let label = pathToLabel(path);
  label = label.charAt(0).toUpperCase() + label.slice(1);
  const missing = !v.actualValuesInData || v.actualValuesInData.length === 0;
  let msg = v.message || '';
  if (!msg || msg.length < 5) {
    msg = missing ? `${label} is missing — this field is required.`
                  : `${label} has an invalid value (${v.actualValuesInData.join(', ')}).`;
  }
  return { ...v, businessLabel: label, businessMessage: msg };
}

const groupedIssues = computed(() => {
  const q = violationSearch.value.toLowerCase();
  const active = q
    ? violations.value.filter(v =>
        [v.shapeName, v.resultPathShort, v.message, v.severity, v.focusNodeShort]
          .some(s => s && s.toLowerCase().includes(q)))
    : violations.value;

  const map = {};
  for (const v of active) {
    const sec = classifyViolation(v);
    if (!map[sec]) map[sec] = [];
    map[sec].push(toBusinessViolation(v));
  }

  return SECTION_MAP
    .map(s => ({
      section:  s.section,
      icon:     s.icon,
      iconColor:s.iconColor,
      items:    map[s.section] || [],
      blocking:     (map[s.section] || []).filter(v => v.severity === 'Violation').length,
      warnings:     (map[s.section] || []).filter(v => v.severity === 'Warning').length,
      nextStep:     s.nextStep,
      nextStepIcon: s.nextStepIcon,
    }))
    .filter(g => g.items.length > 0);
});

// Filtered violations table
// ── Derived helpers ─────────────────────────────────────────────────────────
const affectedSections = computed(() => new Set(groupedIssues.value.map(g => g.section)));

const timelineSteps = computed(() => {
  const code = processingStatus.value.code;
  return [
    { label: 'Imported',        state: 'done',                                           active: false },
    { label: 'Validated',       state: 'done',                                           active: false },
    { label: 'Under Review',    state: code === 'ready'   ? 'done'    : 'active',        active: code !== 'ready' },
    { label: code === 'blocked' ? 'Action Required' : code === 'review' ? 'Pending Approval' : 'Approved',
                                state: code === 'ready'   ? 'done'    : code === 'blocked' ? 'blocked' : 'pending',
                                active: true },
  ];
});

const filteredViolations = computed(() => {  const q = violationSearch.value.toLowerCase();
  if (!q) return violations.value;
  return violations.value.filter(v =>
    [v.shapeName, v.focusNodeShort, v.resultPathShort, v.constraintComponent, v.message, v.severity]
      .some(s => s && s.toLowerCase().includes(q))
  );
});

const severityChipColor = (s) => ({ Violation: 'error', Warning: 'warning', Info: 'info' }[s] ?? 'default');
const severityRowClass  = (s) => ({ Violation: 'row-viol-error', Warning: 'row-viol-warn', Info: 'row-viol-info' }[s] ?? '');
</script>

<style scoped>
/* ── Page shell ─────────────────────────────────────────────────────── */
.invoice-view {
  min-height: 100vh;
  background: #eef0f3;
  font-family: 'Inter', 'Segoe UI', 'Roboto', sans-serif;
}

/* Page header bar */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #1e293b;
  color: #fff;
  padding: 10px 24px;
  min-height: 52px;
  position: sticky;
  top: 0;
  z-index: 10;
  box-shadow: 0 2px 8px rgba(0,0,0,.25);
}
.page-header-title {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: .3px;
  color: #fff;
}
.page-header-sub  { font-size: 13px; color: #94a3b8; }
.compliance-badge {
  display: inline-flex;
  align-items: center;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: .4px;
  padding: 3px 10px;
  border-radius: 3px;
}
.badge-ok   { background: #166534; color: #bbf7d0; }
.badge-fail { background: #7f1d1d; color: #fecaca; }
.severity-pill {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 9px;
  border-radius: 3px;
  background: rgba(255,255,255,.1);
  color: #e2e8f0;
  letter-spacing: .3px;
}
.pill-violation { background: rgba(220,38,38,.25); color: #fca5a5; }
.pill-warning   { background: rgba(234,179,8,.2);  color: #fde68a; }
.pill-info      { background: rgba(59,130,246,.2); color: #bfdbfe; }

/* Page body padding */
.invoice-page-body { padding: 24px 24px 0; }

/* ── Processing status strip ─────────────────────────────────────────── */
.status-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-radius: 2px;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 12px;
}
.status-ready   { background: #f0fdf4; border: 1px solid #bbf7d0; }
.status-blocked { background: #fff5f5; border: 1px solid #fecaca; }
.status-review  { background: #fffbeb; border: 1px solid #fde68a; }
.status-strip-left  { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.status-strip-right { display: flex; align-items: center; gap: 1px; flex-shrink: 0; }
.status-badge {
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  font-weight: 700;
  padding: 4px 12px;
  border-radius: 12px;
  align-self: flex-start;
  letter-spacing: .3px;
}
.sbadge-ready   { background: #dcfce7; color: #15803d; }
.sbadge-blocked { background: #fee2e2; color: #b91c1c; }
.sbadge-review  { background: #fef3c7; color: #92400e; }
.status-summary { font-size: 13px; color: #334155; max-width: 600px; line-height: 1.5; }
.status-kpi {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 16px;
  border-left: 1px solid rgba(0,0,0,.07);
  min-width: 70px;
}
.status-kpi:first-child { border-left: none; }
.status-kpi-val  { font-size: 22px; font-weight: 800; line-height: 1; font-variant-numeric: tabular-nums; }
.status-kpi-lbl  { font-size: 9px; text-transform: uppercase; letter-spacing: .5px; color: #64748b; margin-top: 2px; white-space: nowrap; }
.status-kpi-block .status-kpi-val { color: #dc2626; }
.status-kpi-warn  .status-kpi-val { color: #d97706; }
.status-kpi-info  .status-kpi-val { color: #2563eb; }
.status-kpi-amount .status-kpi-val { color: #0f172a; }

/* ── Actions needed panel ────────────────────────────────────────────── */
.actions-panel {
  background: #fffbeb;
  border: 1px solid #fde68a;
  border-left: 4px solid #d97706;
  border-radius: 2px;
  padding: 12px 16px;
  margin-bottom: 12px;
}
.actions-header {
  display: flex;
  align-items: center;
  font-size: 12px;
  font-weight: 700;
  color: #92400e;
  text-transform: uppercase;
  letter-spacing: .5px;
  margin-bottom: 8px;
}
.actions-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 5px; }
.action-item  { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #334155; }
.action-dot   { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.adot-block   { background: #dc2626; }
.adot-warn    { background: #d97706; }

/* ── Issues panel ────────────────────────────────────────────────────── */
.issues-panel {
  border: 1px solid #cbd5e1;
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 24px;
}
.issues-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #1e293b;
  padding: 10px 16px;
  flex-wrap: wrap;
  gap: 8px;
}
.issues-title { font-size: 12px; font-weight: 700; color: #e2e8f0; text-transform: uppercase; letter-spacing: .6px; }
.issues-count {
  font-size: 11px;
  background: rgba(255,255,255,.12);
  color: #94a3b8;
  padding: 1px 8px;
  border-radius: 10px;
  font-weight: 600;
}
.tech-toggle {
  font-size: 11px;
  color: #64748b;
  background: rgba(255,255,255,.06);
  border: 1px solid #334155;
  border-radius: 3px;
  padding: 4px 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  transition: color .15s;
}
.tech-toggle:hover { color: #e2e8f0; }
.issues-header :deep(.toolbar-input .v-field__input) { color: #e2e8f0 !important; font-size: 12px; }
.issues-header :deep(.toolbar-input .v-field)        { background: rgba(255,255,255,.06) !important; }
.issues-header :deep(.toolbar-input .v-field__outline__start),
.issues-header :deep(.toolbar-input .v-field__outline__notch),
.issues-header :deep(.toolbar-input .v-field__outline__end)  { border-color: #334155 !important; }
.issues-header :deep(.toolbar-input .v-icon) { color: #64748b !important; }

.issue-group { border-bottom: 1px solid #e2e8f0; }
.issue-group:last-child { border-bottom: none; }
.issue-group-header {
  display: flex;
  align-items: center;
  padding: 8px 16px;
  background: #f8fafc;
  font-size: 11px;
  font-weight: 700;
  color: #334155;
  text-transform: uppercase;
  letter-spacing: .5px;
  gap: 6px;
  border-bottom: 1px solid #e2e8f0;
}
.ig-count  { margin-left: auto; display: flex; gap: 8px; font-size: 10px; font-weight: 600; }
.ig-block  { background: #fee2e2; color: #b91c1c; padding: 1px 7px; border-radius: 8px; }
.ig-warn   { background: #fef3c7; color: #92400e; padding: 1px 7px; border-radius: 8px; }

.issue-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 10px 16px;
  border-bottom: 1px solid #f1f5f9;
  gap: 12px;
}
.issue-row:last-child { border-bottom: none; }
.irow-violation { background: #fff5f5; }
.irow-warning   { background: #fffdf5; }
.irow-info      { background: #f8fafc; }
.irow-violation:hover { background: #ffe4e6; }
.irow-warning:hover   { background: #fef9c3; }
.irow-info:hover      { background: #f1f5f9; }
.issue-row-left { display: flex; align-items: flex-start; gap: 10px; flex: 1; min-width: 0; }
.issue-severity-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; margin-top: 4px; }
.idot-violation { background: #dc2626; }
.idot-warning   { background: #d97706; }
.idot-info      { background: #2563eb; }
.issue-content { min-width: 0; }
.issue-title   { font-size: 13px; font-weight: 600; color: #0f172a; }
.issue-desc    { font-size: 12px; color: #475569; margin-top: 2px; line-height: 1.4; }
.issue-technical {
  font-size: 10px;
  color: #94a3b8;
  font-family: 'Cascadia Code', 'Consolas', monospace;
  margin-top: 4px;
  word-break: break-all;
}
.tech-value    { color: #16a34a; }
.issue-severity-label {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 8px;
  flex-shrink: 0;
  align-self: flex-start;
  margin-top: 2px;
}
.isev-violation { background: #fee2e2; color: #b91c1c; }
.isev-warning   { background: #fef3c7; color: #92400e; }
.isev-info      { background: #dbeafe; color: #1d4ed8; }

/* ── Print / PDF button ──────────────────────────────────────────────── */
.print-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 600;
  color: #94a3b8;
  background: rgba(255,255,255,.07);
  border: 1px solid #334155;
  border-radius: 3px;
  padding: 4px 10px;
  cursor: pointer;
  transition: color .15s, background .15s;
}
.print-btn:hover { color: #e2e8f0; background: rgba(255,255,255,.13); }

/* ── Workflow timeline ────────────────────────────────────────────────── */
.timeline-panel {
  display: flex;
  align-items: flex-start;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 2px;
  padding: 14px 20px;
  margin-bottom: 12px;
  gap: 0;
  overflow-x: auto;
}
.timeline-step {
  display: flex;
  align-items: flex-start;
  flex-shrink: 0;
}
.tl-connector {
  width: 52px;
  height: 2px;
  margin-top: 15px;
  flex-shrink: 0;
  background: #e2e8f0;
}
.tl-con-done { background: #16a34a; }
.tl-con-pend { background: #e2e8f0; }
.tl-dot {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.tldot-done    { background: #16a34a; }
.tldot-active  { background: #3b82f6; }
.tldot-blocked { background: #dc2626; }
.tldot-pending { background: #e2e8f0; }
.tl-info { display: flex; flex-direction: column; align-items: center; width: 100px; padding: 0 4px; }
.tl-label { font-size: 10px; font-weight: 600; text-align: center; margin-top: 6px; color: #475569; white-space: nowrap; }
.tllbl-done    { color: #15803d; }
.tllbl-active  { color: #1d4ed8; }
.tllbl-blocked { color: #b91c1c; }
.tllbl-pending { color: #94a3b8; }
.tl-chip {
  font-size: 9px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 8px;
  margin-top: 3px;
  white-space: nowrap;
  text-transform: uppercase;
  letter-spacing: .3px;
}
.tlc-ready   { background: #dcfce7; color: #15803d; }
.tlc-blocked { background: #fee2e2; color: #b91c1c; }
.tlc-review  { background: #fef3c7; color: #92400e; }

/* ── Action panel why-this-matters ──────────────────────────────────── */
.action-body  { display: flex; flex-direction: column; gap: 1px; }
.action-why   { font-size: 11px; color: #92400e; font-style: italic; line-height: 1.4; }

/* ── Show only affected sections toggle ─────────────────────────────── */
.affected-toggle {
  display: inline-flex;
  align-items: center;
  font-size: 11px;
  color: #64748b;
  background: rgba(255,255,255,.06);
  border: 1px solid #334155;
  border-radius: 3px;
  padding: 4px 10px;
  cursor: pointer;
  transition: color .15s, background .15s;
}
.affected-toggle:hover { color: #e2e8f0; }
.aff-active { background: #3b82f6 !important; border-color: #3b82f6 !important; color: #fff !important; }

/* ── Print media ─────────────────────────────────────────────────────── */
@media print {
  .page-header, .status-strip, .timeline-panel, .actions-panel, .issues-panel { display: none !important; }
  .invoice-page-body { padding: 0 !important; }
  .paper-invoice {
    box-shadow: none !important;
    border: none !important;
    margin: 0 !important;
    padding: 12mm 14mm !important;
  }
  body, .invoice-view { background: #fff !important; }
}

/* ── Paper invoice shell ────────────────────────────────────────────── */
.paper-invoice {
  background: #fff;
  border: 1px solid #cbd5e1;
  border-radius: 2px;
  box-shadow: 0 1px 4px rgba(0,0,0,.06), 0 4px 16px rgba(0,0,0,.06);
  font-size: 13px;
  color: #1e293b;
  max-width: 100%;
  overflow: hidden;
}

/* Title bar — dark band */
.inv-title-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #1e293b;
  color: #fff;
  padding: 14px 28px;
}
.inv-title-left { display: flex; align-items: baseline; gap: 14px; }
.inv-title {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 3px;
  color: #fff;
}
.inv-type {
  font-size: 11px;
  color: #94a3b8;
  letter-spacing: 1px;
  text-transform: uppercase;
  font-weight: 500;
}
.inv-title-right { text-align: right; }
.inv-docnum-label { font-size: 10px; color: #64748b; letter-spacing: .8px; text-transform: uppercase; margin-bottom: 2px; }
.inv-docnum { font-size: 16px; font-weight: 600; color: #fff; }

/* Header three-column section */
.inv-header {
  display: grid;
  grid-template-columns: 1fr 220px 1fr;
  gap: 0;
  border-bottom: 1px solid #e2e8f0;
}
.inv-party {
  padding: 20px 28px;
}
.inv-party:first-child { border-right: 1px solid #e2e8f0; }
.inv-party:last-child  { border-left: 1px solid #e2e8f0; }
.inv-section-label {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 1.2px;
  text-transform: uppercase;
  color: #94a3b8;
  margin-bottom: 6px;
  display: block;
}
.inv-party-name {
  font-weight: 700;
  font-size: 14px;
  color: #0f172a;
  margin-bottom: 4px;
  line-height: 1.3;
}
.inv-party-line { color: #475569; line-height: 1.6; font-size: 12.5px; }

/* Meta panel */
.inv-meta {
  background: #f8fafc;
  padding: 20px 18px;
  border-right: none;
  border-left: none;
}
.inv-meta-table  { width: 100%; border-collapse: collapse; }
.inv-meta-table tr + tr td { padding-top: 5px; }
.inv-meta-label {
  color: #64748b;
  font-size: 10.5px;
  padding-right: 10px;
  white-space: nowrap;
  font-weight: 600;
  letter-spacing: .3px;
  text-transform: uppercase;
  vertical-align: top;
  padding-top: 1px;
}
.inv-meta-value { font-weight: 600; font-size: 12.5px; color: #1e293b; }

/* Other parties strip */
.inv-other-parties {
  display: flex;
  flex-wrap: wrap;
  gap: 24px;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
  border-bottom: 1px solid #e2e8f0;
  padding: 10px 28px;
  font-size: 12px;
}
.inv-other-party { display: flex; align-items: center; }

/* Line items table */
.inv-items-table { width: 100%; border-collapse: collapse; }
.inv-items-table thead tr {
  background: #1e293b;
}
.inv-items-table th {
  color: #94a3b8;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .8px;
  padding: 9px 12px;
  white-space: nowrap;
  text-align: left;
  border: none;
}
.inv-items-table tbody tr:nth-child(even) td { background: #f8fafc; }
.inv-items-table tbody tr:nth-child(odd)  td { background: #fff; }
.inv-items-table td {
  padding: 9px 12px;
  border-bottom: 1px solid #e2e8f0;
  vertical-align: top;
  color: #334155;
}
.inv-items-table tr:last-child td { border-bottom: none; }
.col-pos   { width: 36px; color: #94a3b8; }
.col-qty   { width: 56px; }
.col-unit  { width: 56px; }
.col-price { width: 90px; }
.col-vat   { width: 60px; }
.col-total { width: 100px; }
.col-ean   { width: 130px; }
.inv-cell-right { text-align: right; }

/* Row violation (even rows already have a tint — override both) */
.row-violation td,
.row-violation:nth-child(even) td,
.row-violation:nth-child(odd) td { background: #fff1f2 !important; }
.row-violation:hover td { background: #ffe4e6 !important; cursor: help; }
.row-viol-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #dc2626;
  color: #fff;
  font-size: 9px;
  font-weight: 700;
  border-radius: 8px;
  min-width: 14px;
  height: 14px;
  padding: 0 3px;
  margin-left: 3px;
  vertical-align: middle;
  line-height: 1;
}

/* Totals block */
.inv-totals {
  display: flex;
  justify-content: flex-end;
  border-top: 2px solid #1e293b;
  padding: 16px 28px 20px;
  background: #f8fafc;
}
.inv-totals-table { width: 300px; border-collapse: collapse; }
.inv-totals-table td { padding: 4px 10px; font-size: 13px; color: #334155; }
.totals-label  { text-align: right; font-size: 11px; text-transform: uppercase; letter-spacing: .5px; color: #64748b; font-weight: 600; }
.totals-value  { text-align: right; font-weight: 600; min-width: 90px; font-variant-numeric: tabular-nums; }
.totals-grand td {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
  background: #e2e8f0;
  padding-top: 10px;
  padding-bottom: 10px;
}

/* Notes */
.inv-notes {
  margin: 0;
  border-top: 1px solid #e2e8f0;
  padding: 14px 28px;
  font-size: 12px;
  color: #475569;
  background: #f8fafc;
  display: flex;
  gap: 32px;
  flex-wrap: wrap;
}
.inv-note-row  { display: flex; flex-direction: column; }
.inv-note-label { font-size: 10px; font-weight: 700; letter-spacing: .5px; text-transform: uppercase; color: #94a3b8; margin-bottom: 2px; }

/* ── Violations panel ───────────────────────────────────────────────── */
.violations-panel {
  border: 1px solid #cbd5e1;
  border-radius: 2px;
  margin-bottom: 24px;
  background: #fff;
}
.violations-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #1e293b;
  padding: 10px 16px;
  border-radius: 2px 2px 0 0;
}
.violations-title {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: .8px;
  text-transform: uppercase;
  color: #e2e8f0;
}
.violations-count {
  font-size: 11px;
  background: #7f1d1d;
  color: #fecaca;
  padding: 1px 8px;
  border-radius: 10px;
  margin-left: 8px;
  font-weight: 600;
}

/* Violation table rows */
.row-viol-error { background: #fff5f5; }
.row-viol-warn  { background: #fffbf0; }
.row-viol-info  { background: #f0f6ff; }

/* ── Violation field highlighting ───────────────────────────────────── */
.violation-field {
  border-bottom: 2px solid #dc2626;
  color: #dc2626;
  cursor: pointer;
  font-weight: 600;
}
.violation-field:hover { background: #fee2e2; border-radius: 2px; }
.violation-icon { color: #dc2626; }

.text-mono { font-family: 'Cascadia Code', 'Consolas', monospace; }
</style>
