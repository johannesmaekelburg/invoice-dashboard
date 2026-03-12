<template>
  <div class="invoice-view pa-6">

    <!-- Header -->
    <div class="d-flex align-center mb-6 gap-3">
      <v-btn
        icon="mdi-arrow-left"
        variant="text"
        size="small"
        @click="router.push('/')"
        title="Back to Dashboard"
      />
      <v-icon size="32" color="primary">mdi-file-document-outline</v-icon>
      <div>
        <h1 class="text-h5 font-weight-bold">
          {{ summary.documentNumber || invoiceUri?.split('/').pop() || 'E-Invoice' }}
        </h1>
        <span class="text-caption text-medium-emphasis">SHACL Compliance Analysis</span>
      </div>
      <v-spacer />
      <v-chip :color="compliance.conforms ? 'success' : 'error'" variant="flat" size="large">
        <v-icon start>{{ compliance.conforms ? 'mdi-check-circle' : 'mdi-alert-circle' }}</v-icon>
        {{ compliance.conforms ? 'Conforms' : 'Does Not Conform' }}
      </v-chip>
    </div>

    <!-- Compliance KPI row -->
    <v-row class="mb-4">
      <v-col cols="12" sm="6" md="3">
        <v-card rounded="lg" elevation="1" class="pa-4 text-center">
          <div class="text-h4 font-weight-bold text-error">{{ compliance.totalViolations ?? '-' }}</div>
          <div class="text-caption text-medium-emphasis mt-1">Total Violations</div>
        </v-card>
      </v-col>
      <v-col v-for="s in compliance.bySeverity" :key="s.severity" cols="12" sm="6" md="3">
        <v-card rounded="lg" elevation="1" class="pa-4 text-center">
          <div class="text-h4 font-weight-bold" :class="severityColor(s.severity)">{{ s.count }}</div>
          <div class="text-caption text-medium-emphasis mt-1">{{ s.severity }}</div>
          <v-chip :color="severityChipColor(s.severity)" size="x-small" class="mt-1">{{ s.severity }}</v-chip>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card rounded="lg" elevation="1" class="pa-4 text-center">
          <div class="text-h4 font-weight-bold text-warning">{{ compliance.affectedFocusNodes ?? '-' }}</div>
          <div class="text-caption text-medium-emphasis mt-1">Affected Nodes</div>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card rounded="lg" elevation="1" class="pa-4 text-center">
          <div class="text-h4 font-weight-bold text-info">{{ compliance.affectedPaths ?? '-' }}</div>
          <div class="text-caption text-medium-emphasis mt-1">Affected Paths</div>
        </v-card>
      </v-col>
    </v-row>

    <v-row>
      <!-- Invoice Details -->
      <v-col cols="12" md="6">
        <v-card rounded="lg" elevation="1" class="mb-4">
          <v-card-title class="text-subtitle-1 font-weight-semibold pa-4 pb-2">
            <v-icon class="mr-2" color="primary">mdi-receipt-text</v-icon>Invoice Details
          </v-card-title>
          <v-divider />
          <v-card-text>
            <v-list density="compact" lines="one">
              <v-list-item v-for="field in invoiceFields" :key="field.label">
                <template #prepend>
                  <span class="text-caption text-medium-emphasis" style="min-width:160px">{{ field.label }}</span>
                </template>
                <span class="font-weight-medium">{{ field.value ?? '-' }}</span>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Financial Summary -->
      <v-col cols="12" md="6">
        <v-card rounded="lg" elevation="1" class="mb-4">
          <v-card-title class="text-subtitle-1 font-weight-semibold pa-4 pb-2">
            <v-icon class="mr-2" color="success">mdi-currency-eur</v-icon>Financial Summary
          </v-card-title>
          <v-divider />
          <v-card-text>
            <v-list density="compact" lines="one">
              <v-list-item v-for="field in financialFields" :key="field.label">
                <template #prepend>
                  <span class="text-caption text-medium-emphasis" style="min-width:160px">{{ field.label }}</span>
                </template>
                <span class="font-weight-medium">{{ field.numeric ? fmtNum(field.value) : (field.value ?? '-') }}</span>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Parties -->
    <v-card rounded="lg" elevation="1" class="mb-4">
      <v-card-title class="text-subtitle-1 font-weight-semibold pa-4 pb-2">
        <v-icon class="mr-2" color="purple">mdi-account-group</v-icon>Involved Parties
      </v-card-title>
      <v-divider />
      <v-card-text>
        <v-row>
          <v-col v-for="party in parties" :key="party.uri" :cols="12" :sm="Math.floor(12 / parties.length) || 12">
            <v-card variant="outlined" rounded="lg" class="pa-3">
              <div class="d-flex flex-wrap gap-1 mb-2">
                <v-chip v-for="role in party.roles" :key="role" size="x-small"
                  :color="roleChipColor(role)" variant="flat">
                  {{ role.replace('Role', '') }}
                </v-chip>
              </div>
              <div v-if="party.name" class="font-weight-medium text-body-2 mb-1">{{ party.name }}</div>
              <div v-if="party.gln" class="d-flex align-center gap-1">
                <span class="text-caption text-medium-emphasis">GLN:</span>
                <span class="text-caption font-mono">{{ party.gln }}</span>
              </div>
              <div v-if="party.vat" class="d-flex align-center gap-1">
                <span class="text-caption text-medium-emphasis">VAT:</span>
                <span class="text-caption">{{ party.vat }}</span>
              </div>
              <div v-if="party.street || party.city || party.countryCode" class="text-caption text-medium-emphasis mt-1">
                <span v-if="party.street">{{ party.street }}, </span>
                <span v-if="party.postalCode">{{ party.postalCode }} </span>
                <span v-if="party.city">{{ party.city }}</span>
                <span v-if="party.countryCode"> ({{ party.countryCode }})</span>
              </div>
              <div v-if="party.contact" class="text-caption text-medium-emphasis mt-1">
                <v-icon size="x-small">mdi-account</v-icon> {{ party.contact }}
                <span v-if="party.phone"><v-icon size="x-small" class="mx-1">mdi-phone</v-icon>{{ party.phone }}</span>
              </div>
              <v-chip v-if="partyViolationCount(party.uri) > 0" color="error"
                size="x-small" class="mt-2">
                {{ partyViolationCount(party.uri) }} violation(s)
              </v-chip>
            </v-card>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Line Items -->
    <v-card rounded="lg" elevation="1" class="mb-4">
      <v-card-title class="text-subtitle-1 font-weight-semibold pa-4 pb-2 d-flex align-center">
        <v-icon class="mr-2" color="teal">mdi-package-variant</v-icon>
        Line Items
        <v-spacer />
        <v-btn
          size="x-small"
          variant="text"
          :prepend-icon="showAllCols ? 'mdi-eye-off-outline' : 'mdi-eye-outline'"
          @click="showAllCols = !showAllCols"
          class="text-caption text-medium-emphasis"
        >{{ showAllCols ? 'Fewer columns' : 'More columns' }}</v-btn>
      </v-card-title>
      <v-divider />
      <v-card-text class="pa-0">
        <v-table density="compact">
          <thead>
            <tr>
              <th>Description</th>
              <th>EAN</th>
              <th>Part # (Buyer)</th>
              <th>Gross Price</th>
              <th v-if="showAllCols">Net Price</th>
              <th>Qty / Unit</th>
              <th v-if="showAllCols">VAT %</th>
              <th v-if="showAllCols">Total Position</th>
              <th v-if="showAllCols">Allowance</th>
              <th>Violations</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.uri">
              <td class="font-weight-medium" style="max-width:200px">
                <div>{{ item.itemName || '-' }}</div>
                <div v-if="item.description" class="text-caption text-medium-emphasis text-truncate">{{ item.description }}</div>
              </td>
              <td>{{ item.ean || '-' }}</td>
              <td>{{ item.partNumberBuyer ?? item.productId ?? '-' }}</td>
              <td>{{ item.grossPrice != null ? fmtNum(item.grossPrice) : '-' }}</td>
              <td v-if="showAllCols">{{ item.netPrice != null ? fmtNum(item.netPrice) : '-' }}</td>
              <td>{{ item.quantity ?? '-' }}<span v-if="item.unit" class="text-caption text-medium-emphasis"> {{ item.unit }}</span></td>
              <td v-if="showAllCols">{{ item.vatRate != null ? item.vatRate + '%' : '-' }}</td>
              <td v-if="showAllCols">{{ item.totalGoodsPosition != null ? fmtNum(item.totalGoodsPosition) : '-' }}</td>
              <td v-if="showAllCols">
                <span v-if="item.allowanceAmount">{{ fmtNum(item.allowanceAmount) }}
                  <span v-if="item.allowanceReason" class="text-caption text-medium-emphasis"> ({{ item.allowanceReason }})</span>
                </span>
                <span v-else>-</span>
              </td>
              <td>
                <v-chip v-if="partyViolationCount(item.uri) > 0"
                  color="warning" size="x-small">
                  {{ partyViolationCount(item.uri) }}
                </v-chip>
                <v-icon v-else color="success" size="small">mdi-check-circle</v-icon>
              </td>
            </tr>
            <tr v-if="!items.length">
              <td colspan="10" class="text-center text-medium-emphasis py-4">No items found</td>
            </tr>
          </tbody>
        </v-table>
      </v-card-text>
    </v-card>

    <!-- Top Issues Summary -->
    <v-card rounded="lg" elevation="1" class="mb-4" v-if="violationsByShape.length">
      <v-card-text class="pa-4">
        <div class="d-flex align-center mb-3">
          <v-icon class="mr-1" color="error">mdi-trending-up</v-icon>
          <span class="text-subtitle-2 font-weight-semibold">Top Issues</span>
          <span class="text-caption text-medium-emphasis ml-2">(most frequent SHACL violations)</span>
        </div>
        <div class="d-flex flex-wrap gap-2">
          <v-chip
            v-for="s in violationsByShape.slice(0, 5)"
            :key="s.shape + s.severity"
            :color="severityChipColor(s.severity)"
            variant="elevated"
            size="small"
          >
            <span class="font-weight-bold mr-1">{{ s.count }}x</span>{{ s.shapeName }}
          </v-chip>
        </div>
      </v-card-text>
    </v-card>

    <!-- Violations by Shape -->
    <v-card rounded="lg" elevation="1" class="mb-4">
      <v-card-title class="text-subtitle-1 font-weight-semibold pa-4 pb-2">
        <v-icon class="mr-2" color="orange">mdi-shape-outline</v-icon>Violations by SHACL Shape
      </v-card-title>
      <v-divider />
      <v-card-text class="pa-0">
        <v-table density="compact">
          <thead>
            <tr>
              <th>Shape</th>
              <th>Severity</th>
              <th>Violations</th>
              <th>Progress</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in violationsByShape" :key="s.shape + s.severity">
              <td class="font-weight-medium">{{ s.shapeName }}</td>
              <td>
                <v-chip :color="severityChipColor(s.severity)" size="x-small" variant="flat">
                  {{ s.severity }}
                </v-chip>
              </td>
              <td>{{ s.count }}</td>
              <td style="min-width:100px">
                <v-progress-linear
                  :model-value="(s.count / compliance.totalViolations) * 100"
                  :color="severityChipColor(s.severity)"
                  height="6" rounded />
              </td>
            </tr>
          </tbody>
        </v-table>
      </v-card-text>
    </v-card>

    <!-- Detailed Enriched Violations Table -->
    <v-card rounded="lg" elevation="1">
      <v-card-title class="text-subtitle-1 font-weight-semibold pa-4 pb-2">
        <v-icon class="mr-2" color="red">mdi-alert-circle-outline</v-icon>
        All Violations — Enriched with Data Graph Context
      </v-card-title>
      <v-divider />
      <v-card-text class="pa-2">
        <v-text-field v-model="violationSearch" placeholder="Filter violations..."
          prepend-inner-icon="mdi-magnify" density="compact" variant="outlined"
          hide-details class="mb-3" />
        <v-table density="compact">
          <thead>
            <tr>
              <th>Severity</th>
              <th>Shape</th>
              <th>Focus Node</th>
              <th>Type</th>
              <th>Result Path</th>
              <th>Constraint</th>
              <th>Values Present in Data</th>
              <th>Message</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(v, i) in filteredViolations" :key="i">
              <td>
                <v-chip :color="severityChipColor(v.severity)" size="x-small" variant="flat">
                  {{ v.severity }}
                </v-chip>
              </td>
              <td class="text-caption">{{ v.shapeName }}</td>
              <td class="text-caption font-mono">{{ v.focusNodeShort }}</td>
              <td class="text-caption">{{ v.focusNodeTypeShort ?? '-' }}</td>
              <td class="text-caption">{{ v.resultPathShort ?? '-' }}</td>
              <td class="text-caption">{{ v.constraintComponent }}</td>
              <td>
                <span v-if="v.actualValuesInData.length" class="text-caption text-success">
                  {{ v.actualValuesInData.join(', ') }}
                </span>
                <span v-else class="text-caption text-error">missing</span>
              </td>
              <td class="text-caption text-medium-emphasis" style="max-width:250px">{{ v.message }}</td>
            </tr>
            <tr v-if="!filteredViolations.length">
              <td colspan="8" class="text-center text-medium-emphasis py-4">No violations match filter</td>
            </tr>
          </tbody>
        </v-table>
      </v-card-text>
    </v-card>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
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
const showAllCols = ref(false);
const fmtNum = (v) => v != null ? parseFloat(v).toFixed(2) : '-';

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

const invoiceFields = computed(() => [
  { label: 'Document Number', value: summary.value.documentNumber },
  { label: 'Document Date', value: summary.value.documentDate },
  { label: 'Document Type', value: summary.value.documentType },
  { label: 'Document Function', value: summary.value.documentFunction },
  { label: 'Process', value: summary.value.process },
  { label: 'Order Number (Buyer)', value: summary.value.orderNumberBuyer },
  { label: 'Date of Order (Buyer)', value: summary.value.dateOrderNumberBuyer },
  { label: 'Delivery Date', value: summary.value.deliveryDate },
  { label: 'Delivery Condition', value: summary.value.deliveryCondition },
  { label: 'Due Date', value: summary.value.dueDate },
  { label: 'Payment Condition', value: summary.value.paymentCondition },
  { label: 'Supplier Note', value: summary.value.supplierNote },
].filter(f => f.value != null));

const financialFields = computed(() => [
  { label: 'Invoice Amount', value: summary.value.invoiceAmount, numeric: true },
  { label: 'Taxable Amount', value: summary.value.taxableAmount, numeric: true },
  { label: 'Total Line Item Amount', value: summary.value.totalLineItemAmount, numeric: true },
  { label: 'Discount Amount', value: summary.value.discountAmount, numeric: true },
  { label: 'Charge Amount', value: summary.value.chargeAmount, numeric: true },
  { label: 'Charge Reason', value: summary.value.chargeReason },
  { label: 'Freight Charge', value: summary.value.freightCharge, numeric: true },
  { label: 'Tax Amount', value: summary.value.taxAmount, numeric: true },
  { label: 'VAT Amount', value: summary.value.vatAmount, numeric: true },
  { label: 'VAT Rate (%)', value: summary.value.vatRate },
  { label: 'Currency', value: summary.value.currency },
  { label: 'Invoice Currency', value: summary.value.invoiceCurrency },
].filter(f => f.value != null));

const violationCountByNode = computed(() => {
  const map = {};
  for (const v of violations.value) {
    map[v.focusNode] = (map[v.focusNode] || 0) + 1;
  }
  return map;
});

const partyViolationCount = (uri) => violationCountByNode.value[uri] ?? 0;

const filteredViolations = computed(() => {
  const q = violationSearch.value.toLowerCase();
  if (!q) return violations.value;
  return violations.value.filter(v =>
    [v.shapeName, v.focusNodeShort, v.resultPathShort, v.constraintComponent, v.message, v.severity]
      .some(s => s && s.toLowerCase().includes(q))
  );
});

const severityColor = (s) => ({
  Violation: 'text-error',
  Warning: 'text-warning',
  Info: 'text-info',
}[s] ?? 'text-medium-emphasis');

const severityChipColor = (s) => ({
  Violation: 'error',
  Warning: 'warning',
  Info: 'info',
}[s] ?? 'default');

const roleChipColor = (role) => {
  const map = {
    SupplierRole: 'blue',
    BuyerRole: 'green',
    InvoiceeRole: 'purple',
    DeliveryPartyRole: 'teal',
    CentralRegulatorRole: 'orange',
  };
  return map[role] ?? 'grey';
};
</script>

<style scoped>
.font-mono {
  font-family: monospace;
}
</style>
