<template>
  <div class="invoice-view pa-6">

    <!-- Header -->
    <div class="d-flex align-center mb-6 gap-3">
      <v-icon size="32" color="primary">mdi-file-document-outline</v-icon>
      <div>
        <h1 class="text-h5 font-weight-bold">E-Invoice Dashboard</h1>
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
          <div class="text-h4 font-weight-bold text-error">{{ compliance.totalViolations ?? '–' }}</div>
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
          <div class="text-h4 font-weight-bold text-warning">{{ compliance.affectedFocusNodes ?? '–' }}</div>
          <div class="text-caption text-medium-emphasis mt-1">Affected Nodes</div>
        </v-card>
      </v-col>
      <v-col cols="12" sm="6" md="3">
        <v-card rounded="lg" elevation="1" class="pa-4 text-center">
          <div class="text-h4 font-weight-bold text-info">{{ compliance.affectedPaths ?? '–' }}</div>
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
                <span class="font-weight-medium">{{ field.value ?? '—' }}</span>
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
                <span class="font-weight-medium">{{ field.value ?? '—' }}</span>
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
              <div class="text-caption text-medium-emphasis">GLN</div>
              <div class="font-weight-medium text-body-2">{{ party.gln ?? '—' }}</div>
              <div class="text-caption text-medium-emphasis mt-1">ID</div>
              <div class="text-caption font-mono text-truncate">{{ party.id }}</div>
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
      <v-card-title class="text-subtitle-1 font-weight-semibold pa-4 pb-2">
        <v-icon class="mr-2" color="teal">mdi-package-variant</v-icon>Line Items
      </v-card-title>
      <v-divider />
      <v-card-text class="pa-0">
        <v-table density="compact">
          <thead>
            <tr>
              <th>Item Name</th>
              <th>EAN</th>
              <th>Product ID</th>
              <th>Gross Price</th>
              <th>Quantity</th>
              <th>Line Amount</th>
              <th>Violations</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.uri">
              <td class="font-weight-medium">{{ item.itemName ?? '—' }}</td>
              <td>{{ item.ean ?? '—' }}</td>
              <td>{{ item.productId ?? '—' }}</td>
              <td>{{ item.grossPrice ?? '—' }}</td>
              <td>{{ item.quantity ?? '—' }}</td>
              <td>{{ item.lineAmount ?? '—' }}</td>
              <td>
                <v-chip v-if="partyViolationCount(item.uri) > 0"
                  color="warning" size="x-small">
                  {{ partyViolationCount(item.uri) }}
                </v-chip>
                <span v-else class="text-success text-caption">✓</span>
              </td>
            </tr>
            <tr v-if="!items.length">
              <td colspan="7" class="text-center text-medium-emphasis py-4">No items found</td>
            </tr>
          </tbody>
        </v-table>
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
              <td class="text-caption">{{ v.focusNodeTypeShort ?? '—' }}</td>
              <td class="text-caption">{{ v.resultPathShort ?? '—' }}</td>
              <td class="text-caption">{{ v.constraintComponent }}</td>
              <td>
                <span v-if="v.actualValuesInData.length" class="text-caption text-success">
                  {{ v.actualValuesInData.join(', ') }}
                </span>
                <span v-else class="text-caption text-error">∅ missing</span>
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
import {
  getInvoiceSummary,
  getInvoiceParties,
  getInvoiceItems,
  getInvoiceViolationsByShape,
  getInvoiceViolationsEnriched,
  getInvoiceCompliance,
} from '@/services/api.js';

const summary = ref({});
const parties = ref([]);
const items = ref([]);
const violationsByShape = ref([]);
const violations = ref([]);
const compliance = ref({ totalViolations: 0, bySeverity: [], affectedFocusNodes: 0, affectedPaths: 0 });
const violationSearch = ref('');

onMounted(async () => {
  const [s, p, it, vs, ve, c] = await Promise.all([
    getInvoiceSummary().catch(() => ({})),
    getInvoiceParties().catch(() => []),
    getInvoiceItems().catch(() => []),
    getInvoiceViolationsByShape().catch(() => []),
    getInvoiceViolationsEnriched().catch(() => []),
    getInvoiceCompliance().catch(() => ({})),
  ]);
  summary.value = s;
  parties.value = p;
  items.value = it;
  violationsByShape.value = vs;
  violations.value = ve;
  compliance.value = c;
});

const invoiceFields = computed(() => [
  { label: 'Document Number', value: summary.value.documentNumber },
  { label: 'Document Date', value: summary.value.documentDate },
  { label: 'Document Type', value: summary.value.documentType },
  { label: 'Document Function', value: summary.value.documentFunction },
  { label: 'Order Number (Buyer)', value: summary.value.orderNumberBuyer },
  { label: 'Process', value: summary.value.process },
  { label: 'Delivery Date', value: summary.value.deliveryDate },
  { label: 'Due Date', value: summary.value.dueDate },
  { label: 'Payment Condition', value: summary.value.paymentCondition },
]);

const financialFields = computed(() => [
  { label: 'Invoice Amount', value: summary.value.invoiceAmount },
  { label: 'Taxable Amount', value: summary.value.taxableAmount },
  { label: 'Total Line Item Amount', value: summary.value.totalLineItemAmount },
  { label: 'Discount Amount', value: summary.value.discountAmount },
  { label: 'Tax Amount', value: summary.value.taxAmount },
  { label: 'VAT Amount', value: summary.value.vatAmount },
  { label: 'VAT Rate (%)', value: summary.value.vatRate },
  { label: 'Currency', value: summary.value.currency },
]);

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
