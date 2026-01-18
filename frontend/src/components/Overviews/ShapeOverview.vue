<template>
  <div class="shape-overview p-4">
    <!-- Loading State -->
    <div v-if="loading" class="text-center py-20">
      <p class="text-gray-600 text-lg">Loading shapes overview...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="text-center py-20">
      <p class="text-red-600 text-lg">{{ error }}</p>
      <button @click="loadOverviewData" class="mt-4 px-6 py-3 bg-blue-500 text-white rounded hover:bg-blue-600">
        Retry
      </button>
    </div>

    <!-- Main Content -->
    <div v-else>
    <!-- Tags Section -->
    <div class="grid grid-cols-4 gap-4 mb-4">
      <div
        v-for="(tag, index) in tags"
        :key="index"
        class="flex flex-row items-center bg-white rounded-lg shadow p-6 hover:shadow-md transition"
      >
        <div class="flex-grow">
          <h3 class="text-sm font-medium text-gray-600 mb-1">{{ tag.title }}</h3>
          <p class="text-3xl font-bold text-gray-800">{{ tag.value }}</p>
        </div>
      </div>
    </div>

    <!-- Plots Section -->
    <div class="grid grid-cols-3 gap-4 mb-4">
      <HistogramChart
        :title="'Distribution of Violations per Constraint'"
        :xAxisLabel="'Number of Violations per Constraint'"
        :yAxisLabel="'Number of Node Shapes'"
        :data="normalizedHistogramViolationData"
        :explanationText="'This scatter plot shows how violations correlate with the number of constraints 1.'"
      />
      <ScatterPlotChart
        :title="'Correlation Between Constraints and Violations'"
        :xAxisLabel="'Number of Constraints'"
        :yAxisLabel="'Violations / Constraint'"
        :data="coveragePlotData"
        :showQuadrants="true"
        :explanationText="'This scatter plot shows how violations correlate with the number of constraints 1.'"
      />
      <ScatterPlotChart
        :title="'Violation Diversity and Intensity'"
        :xAxisLabel="'Entropy of Constraint Violations'"
        :yAxisLabel="'Violations / Constraints'"
        :data="scatterPlotData"
        :showQuadrants="true"
        :explanationText="'This scatter plot shows how violations correlate with the number of constraints 2.'"

      />
    </div>

    <!-- Table Section -->
    <div class="bg-white border border-gray-200 p-6 rounded-lg shadow-lg">
      <h2 class="text-2xl font-bold text-gray-700 mb-4">Shape Details</h2>
      <table class="w-full border-collapse">
        <thead class="bg-gray-200">
          <tr>
            <th 
              v-for="(column, index) in columns" 
              :key="index" 
              class="text-left px-6 py-3 border-b border-gray-300 text-gray-600 font-medium cursor-pointer"
              @click="sortColumn(column)">
              {{ column.label }}
              <span class="sort-indicator" >
                {{ sortKey === column.field ? (sortOrder === 'asc' ? ' ▲' : ' ▼') : '' }}
              </span>
            </th>
            <th class="text-center px-6 py-3 border-b border-gray-300 text-gray-600 font-medium"></th>
          </tr>
        </thead>
        <tbody>
          <tr 
            v-for="shape in sortedPaginatedData" 
            :key="shape.id" 
            class="even:bg-gray-50 hover:bg-blue-50 transition-colors"
            @click="goToShape(shape)">
            <td class="px-6 py-4 border-b border-gray-300">{{ shape.name }}</td>
            <td class="px-6 py-4 border-b border-gray-300">{{ shape.violations }}</td>
            <td class="px-6 py-4 border-b border-gray-300">{{ shape.propertyShapes }}</td>
            <td class="px-6 py-4 border-b border-gray-300">{{ shape.focusNodes }}</td>
            <td class="px-6 py-4 border-b border-gray-300">{{ shape.propertyPaths }}</td>
            <td class="px-6 py-4 border-b border-gray-300">{{ shape.mostViolatedConstraint }}</td>
            <td class="px-6 py-4 border-b border-gray-300">{{ shape.violationToConstraintRatio }}</td>
            <td class="px-6 py-4 border-b border-gray-300 text-center">
              <button class="text-blue-600 hover:text-blue-800">
                <font-awesome-icon icon="arrow-right" />
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="flex justify-between items-center mt-4">
        <button
          :disabled="currentPage === 1"
          @click="prevPage"
          class="px-4 py-2 bg-gray-200 text-gray-600 rounded hover:bg-gray-300 disabled:opacity-50">
          Previous
        </button>
        <span class="text-gray-700">Page {{ currentPage }} of {{ totalPages }}</span>
        <button
          :disabled="currentPage === totalPages"
          @click="nextPage"
          class="px-4 py-2 bg-gray-200 text-gray-600 rounded hover:bg-gray-300 disabled:opacity-50">
          Next
        </button>
      </div>
    </div>
    </div>
  </div>
</template>


<script setup>
/**
 * ShapeOverview component
 *
 * Provides a comprehensive overview of SHACL shapes in the dataset.
 * Displays statistics, visualizations, and listings of shapes with their constraints and validation results.
 *
 * @example
 * // Basic usage in a parent component template:
 * // <ShapeOverview />
 *
 * @prop {Array} [shapes=[]] - List of shapes to display
 * @prop {Boolean} [showViolations=true] - Whether to show violation data
 * @prop {Boolean} [showCharts=true] - Whether to show visualization charts
 *
 * @dependencies
 * - vue (Composition API)
 * - ../Charts/PieChart.vue
 * - ../Charts/GroupedBarChart.vue
 *
 * @style
 * - Responsive layout with cards and data tables.
 * - Data visualization components for shape statistics.
 * - Filterable and sortable shape listings with expandable details.
 * 
 * @returns {HTMLElement} A dashboard page showing shape statistics in summary cards at the top,
 * three data visualizations (histogram and scatter plots) in the middle, and a sortable, paginated 
 * data table listing all node shapes with their metrics and violation details at the bottom.
 */
// Importing components
import HistogramChart from './../Charts/HistogramChart.vue';
import ScatterPlotChart from './../Charts/ScatterPlotChart.vue';
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { calculateShannonEntropy } from "./../../utils/utils";
import {
  getNodeShapesCountInGraph,
  getNodeShapesWithViolationsCountOverview,
  getMaxViolationsForNodeShape,
  getAverageViolationsForNodeShapes,
  getViolationsDistribution,
  getCorrelationData,
  getNodeShapeDetailsTable,
  getValidationDetailsReport
} from '../../services/api.js';

// State
const loading = ref(false);
const error = ref(null);

// Prefixes for URI formatting (same as MainContent.vue)
const prefixes = ref({});

// Helper function to format URIs using prefixes (same as MainContent.vue)
const formatURI = (uri) => {
  if (!uri || typeof uri !== "string") return uri;

  let matchedPrefix = null;
  let matchedNamespace = null;

  for (const [prefix, namespace] of Object.entries(prefixes.value)) {
    if (uri.startsWith(namespace) && (!matchedNamespace || namespace.length > matchedNamespace.length)) {
      matchedPrefix = prefix;
      matchedNamespace = namespace;
    }
  }

  if (matchedPrefix) {
    return `${matchedPrefix}:${uri.slice(matchedNamespace.length)}`;
  }

  return uri;
};

const shapeViolations2 = ref([
  { name: "PersonShape", violations: { "sh:minCount": 20, "sh:datatype": 10 }, totalViolations: 30, constraints: 10 },
  { name: "AddressShape", violations: { "sh:pattern": 5, "sh:datatype": 15, "sh:maxCount": 10 }, totalViolations: 30, constraints: 8 },
  { name: "OrganizationShape", violations: { "sh:minCount": 25 }, totalViolations: 25, constraints: 5 },
  { name: "EventShape", violations: { "sh:pattern": 10, "sh:minCount": 15, "sh:maxCount": 5 }, totalViolations: 30, constraints: 12 },
  { name: "ProductShape", violations: { "sh:datatype": 20, "sh:pattern": 10 }, totalViolations: 30, constraints: 9 },
  { name: "LocationShape", violations: { "sh:maxCount": 8, "sh:nodeKind": 5 }, totalViolations: 13, constraints: 7 },
  { name: "BuildingShape", violations: { "sh:minCount": 12, "sh:pattern": 8 }, totalViolations: 20, constraints: 8 },
  { name: "VehicleShape", violations: { "sh:datatype": 14, "sh:maxCount": 6 }, totalViolations: 20, constraints: 6 },
  { name: "CityShape", violations: { "sh:pattern": 10, "sh:minCount": 5, "sh:maxExclusive": 10 }, totalViolations: 25, constraints: 10 },
  { name: "CountryShape", violations: { "sh:minCount": 18, "sh:datatype": 12 }, totalViolations: 30, constraints: 9 },
  { name: "SchoolShape", violations: { "sh:pattern": 15, "sh:datatype": 10 }, totalViolations: 25, constraints: 7 },
  { name: "HospitalShape", violations: { "sh:minCount": 12, "sh:maxCount": 8 }, totalViolations: 20, constraints: 6 },
  { name: "AirportShape", violations: { "sh:nodeKind": 7, "sh:maxExclusive": 10 }, totalViolations: 17, constraints: 8 },
  { name: "UniversityShape", violations: { "sh:datatype": 25, "sh:pattern": 15 }, totalViolations: 40, constraints: 12 },
  { name: "LibraryShape", violations: { "sh:minCount": 10, "sh:datatype": 10 }, totalViolations: 20, constraints: 7 },
  { name: "ParkShape", violations: { "sh:pattern": 8, "sh:maxCount": 7 }, totalViolations: 15, constraints: 5 },
  { name: "MuseumShape", violations: { "sh:minCount": 15, "sh:nodeKind": 10 }, totalViolations: 25, constraints: 10 },
  { name: "BridgeShape", violations: { "sh:pattern": 12, "sh:datatype": 8 }, totalViolations: 20, constraints: 6 },
  { name: "RiverShape", violations: { "sh:minCount": 8, "sh:maxExclusive": 6 }, totalViolations: 14, constraints: 8 },
  { name: "StreetShape", violations: { "sh:nodeKind": 10, "sh:pattern": 5 }, totalViolations: 15, constraints: 6 },
  { name: "EmployeeShape", violations: { "sh:minCount": 2,  }, totalViolations: 5, constraints: 10 },
  { name: "DepartmentShape", violations: { "sh:datatype": 3 }, totalViolations: 3, constraints: 8 },
  { name: "ProjectShape", violations: { "sh:maxCount": 1 }, totalViolations: 1, constraints: 12 },
  { name: "TaskShape", violations: { "sh:pattern": 2 }, totalViolations: 4, constraints: 7 },
  { name: "TeamShape", violations: { "sh:nodeKind": 3 }, totalViolations: 3, constraints: 15 }
]);

const zeroViolationShapes = ref([
  { name: "CustomerShape", violations: {}, totalViolations: 0, constraints: 8 },
  { name: "OrderShape", violations: {}, totalViolations: 0, constraints: 6 },
  { name: "InvoiceShape", violations: {}, totalViolations: 0, constraints: 10 },
  { name: "ReceiptShape", violations: {}, totalViolations: 0, constraints: 7 },
  { name: "PaymentShape", violations: {}, totalViolations: 0, constraints: 9 },
  { name: "AccountShape", violations: {}, totalViolations: 0, constraints: 5 },
  { name: "VendorShape", violations: {}, totalViolations: 0, constraints: 6 },
  { name: "SupplierShape", violations: {}, totalViolations: 0, constraints: 8 },
  { name: "WarehouseShape", violations: {}, totalViolations: 0, constraints: 12 },
  { name: "InventoryShape", violations: {}, totalViolations: 0, constraints: 10 },
  { name: "LogisticsShape", violations: {}, totalViolations: 0, constraints: 11 },
  { name: "ShipmentShape", violations: {}, totalViolations: 0, constraints: 6 },
  { name: "RegionShape", violations: {}, totalViolations: 0, constraints: 9 },
  { name: "SectorShape", violations: {}, totalViolations: 0, constraints: 7 },
  { name: "DistrictShape", violations: {}, totalViolations: 0, constraints: 10 }
]);

const realViolations = ref([
{'violation_entropy': 0.39, 'num_violations': 729, 'num_constraints': 22}, 
{'violation_entropy': 0.0, 'num_violations': 718, 'num_constraints': 8}, 
{'violation_entropy': 0.18, 'num_violations': 1896, 'num_constraints': 65}, 
{'violation_entropy': 0.7, 'num_violations': 830, 'num_constraints': 25}, 
{'violation_entropy': 0.13, 'num_violations': 1203, 'num_constraints': 22}, 
{'violation_entropy': 0.0, 'num_violations': 1045, 'num_constraints': 17}, 
{'violation_entropy': 0.82, 'num_violations': 576, 'num_constraints': 25}, 
{'violation_entropy': 0.22, 'num_violations': 1283, 'num_constraints': 23}, 
{'violation_entropy': 0.4, 'num_violations': 384, 'num_constraints': 24}, 
{'violation_entropy': 0.2, 'num_violations': 1165, 'num_constraints': 27}, 
{'violation_entropy': 0.5, 'num_violations': 892, 'num_constraints': 55}, 
{'violation_entropy': 0.63, 'num_violations': 387, 'num_constraints': 24}, 
{'violation_entropy': 0.0, 'num_violations': 0, 'num_constraints': 16}, 
{'violation_entropy': 0.13, 'num_violations': 656, 'num_constraints': 15}, 
{'violation_entropy': 0.14, 'num_violations': 732, 'num_constraints': 22}, 
{'violation_entropy': 0.0, 'num_violations': 642, 'num_constraints': 21}, 
{'violation_entropy': 0.49, 'num_violations': 1452, 'num_constraints': 58}, 
{'violation_entropy': 0.04, 'num_violations': 997, 'num_constraints': 48}, 
{'violation_entropy': 0.45, 'num_violations': 1507, 'num_constraints': 75}, 
{'violation_entropy': 0.55, 'num_violations': 1086, 'num_constraints': 63}, 
{'violation_entropy': 0.18, 'num_violations': 968, 'num_constraints': 40}, 
{'violation_entropy': 0.24, 'num_violations': 1941, 'num_constraints': 38}, 
{'violation_entropy': 0.0, 'num_violations': 0, 'num_constraints': 22}, 
{'violation_entropy': 0.43, 'num_violations': 34, 'num_constraints': 19}, 
{'violation_entropy': 0.0, 'num_violations': 41, 'num_constraints': 20}, 
{'violation_entropy': 0.4, 'num_violations': 2379, 'num_constraints': 49}, 
{'violation_entropy': 0.29, 'num_violations': 2241, 'num_constraints': 29}, 
{'violation_entropy': 0.23, 'num_violations': 949, 'num_constraints': 24}, 
{'violation_entropy': 0.0, 'num_violations': 0, 'num_constraints': 39}, 
{'violation_entropy': 0.02, 'num_violations': 659, 'num_constraints': 32}])


const shapeViolations = computed(() => [...shapeViolations2.value, ...zeroViolationShapes.value]);

// Scatter plot data - will be loaded from API
const coveragePlotData = ref({
  datasets: [{
    label: "Shapes",
    data: []
  }]
});

const scatterPlotData = ref({
  datasets: [{
    label: "Shapes",
    data: []
  }]
});


// Router for navigation
const router = useRouter();

// Tags data - will be loaded from API
const tags = ref([
  { title: "Total Node Shapes", value: 0 },
  { title: "Node Shapes with Violations (%)", value: "0%" },
  { title: "Max Violations per Node Shape", value: 0 },
  { title: "Avg Violations per Node Shape", value: 0 },
]);

const normalizedViolationBins = [0, 0.5, 1, 1.5, 2, 2.5, 3]; // Define bins for the histogram

// Chart data - will be loaded from API
const normalizedHistogramViolationData = ref({
  labels: [],
  datasets: []
});



const normalizedHistogramData = {
  labels: normalizedViolationBins.map((bin, index) =>
    index < normalizedViolationBins.length - 1
      ? `${bin} - ${normalizedViolationBins[index + 1]}`
      : `${bin}+`
  ),
  datasets: [
    {
      label: "Normalized Violations",
      data: normalizedViolationBins.map((bin, index) => {
        const lowerBound = bin;
        const upperBound = normalizedViolationBins[index + 1] || Infinity;

        return shapeViolations.value.filter(
          (shape) =>
            shape.totalViolations / shape.constraints >= lowerBound &&
            shape.totalViolations / shape.constraints < upperBound
        ).length;
      })
    },
  ],
};

const columns = ref([
  { label: "Node Shape Name", field: "name" },
  { label: "Violations", field: "violations" },
  { label: "Number of Property Shapes", field: "propertyShapes" },
  { label: "Focus Nodes Affected", field: "focusNodes" },
  { label: "Property Paths", field: "propertyPaths" },
  { label: "Most Violated Constraint Component", field: "mostViolatedConstraint" },
  { label: "Violation-to-Constraint Ratio", field: "violationToConstraintRatio" },
]);

// Table data - will be loaded from API
const shapes = ref([]);

// Load all overview data from API
const loadOverviewData = async () => {
  loading.value = true;
  error.value = null;

  try {
    // First, fetch prefixes from validation details (same as MainContent.vue)
    const prefixData = await getValidationDetailsReport(1, 0);
    prefixes.value = prefixData["@prefixes"] || {};

    // Load tags data in parallel
    const [totalShapesData, shapesWithViolationsData, maxViolationsData, avgViolationsData] = 
      await Promise.all([
        getNodeShapesCountInGraph(),
        getNodeShapesWithViolationsCountOverview(),
        getMaxViolationsForNodeShape(),
        getAverageViolationsForNodeShapes()
      ]);

    // Update tags
    const totalShapes = totalShapesData.nodeShapeCount || 0;
    tags.value[0].value = totalShapes;
    
    const violationsCount = shapesWithViolationsData.nodeShapesWithViolationsCount || 0;
    const percentage = totalShapes > 0 
      ? ((violationsCount / totalShapes) * 100).toFixed(1)
      : 0;
    tags.value[1].value = `${percentage}%`;
    
    tags.value[2].value = maxViolationsData.violationCount || 0;
    tags.value[3].value = avgViolationsData.averageViolations || 0;

    // Load chart data in parallel
    const [histogramData, correlationData, tableData] = await Promise.all([
      getViolationsDistribution(10),
      getCorrelationData(),
      getNodeShapeDetailsTable()
    ]);

    // Update histogram
    normalizedHistogramViolationData.value = histogramData;

    // Update scatter plots from correlation data
    coveragePlotData.value = {
      datasets: [{
        label: "Shapes",
        data: correlationData.map(item => ({
          x: item.num_constraints,
          y: item.num_constraints > 0 ? item.num_violations / item.num_constraints : 0,
          label: "",
          hasZeroViolations: item.num_violations === 0
        }))
      }]
    };

    scatterPlotData.value = {
      datasets: [{
        label: "Shapes",
        data: correlationData.map(item => ({
          x: item.violation_entropy,
          y: item.num_constraints > 0 ? item.num_violations / item.num_constraints : 0,
          label: ""
        }))
      }]
    };

    // Format URIs with prefixes AND store original
    shapes.value = (tableData.nodeShapes || []).map(shape => ({
      ...shape,
      originalName: shape.name,  // Keep full URI for navigation
      name: formatURI(shape.name),  // Display prefixed version
      mostViolatedConstraint: formatURI(shape.mostViolatedConstraint)
    }));

  } catch (err) {
    console.error('Error loading overview data:', err);
    error.value = 'Failed to load overview data. Please try again.';
  } finally {
    loading.value = false;
  }
};
const currentPage = ref(1);
const pageSize = ref(10);
const totalPages = computed(() => Math.ceil(shapes.value.length / pageSize.value));

const paginatedData = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return shapes.value.slice(start, start + pageSize.value);
});

const sortedPaginatedData = computed(() => {
  const data = paginatedData.value;
  if (sortKey.value) {
    return [...data].sort((a, b) => {
      const result = a[sortKey.value].toString().localeCompare(b[sortKey.value].toString(), undefined, { numeric: true });
      return sortOrder.value === "asc" ? result : -result;
    });
  }
  return data;
});

const prevPage = () => {
  if (currentPage.value > 1) currentPage.value--;
};

const nextPage = () => {
  if (currentPage.value < totalPages.value) currentPage.value++;
};

// Use originalName (full URI) for navigation, not the prefixed name
const goToShape = (shape) => {
  // URL-encode the shape URI to handle special characters and slashes
  const encodedShapeId = encodeURIComponent(shape.originalName);
  router.push({ name: "ShapeView", params: { shapeId: encodedShapeId } });
};

const sortKey = ref("");
const sortOrder = ref("asc");

const sortColumn = (column) => {
  if (sortKey.value === column.field) {
    sortOrder.value = sortOrder.value === "asc" ? "desc" : "asc";
  } else {
    sortKey.value = column.field;
    sortOrder.value = "asc";
  }
};

// Load data on mount
onMounted(() => {
  loadOverviewData();
});
</script>


<style scoped>
.grid-cols-4 {
  grid-template-columns: repeat(4, 1fr);
}

th, td {
  padding: 12px;
}

tbody tr:hover {
  background-color: #f0f8ff;
}

tbody tr {
  cursor: pointer;
}

.grid {
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
}

.chart-container {
  height: 100%;
  width: 100%;
  background: white;
  border-radius: 8px;
  padding: 10px;
}

.shape-overview {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.sort-indicator {
  font-size: 0.8em; /* Makes the triangle smaller */
  margin-left: 5px;
  opacity: 0.8; /* Optional: makes it slightly faded */
}
</style>
