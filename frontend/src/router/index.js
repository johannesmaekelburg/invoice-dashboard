/**
 * Router Configuration
 * 
 * Defines all routes for the SHACL Dashboard application.
 * Handles navigation between different views and components.
 * 
 * Routes include:
 * - Home (MainContent)
 * - Shape overview and detailed views
 * - Constraint overview and detailed views
 * - Focus Node overview and detailed views
 * - Property Path overview and detailed views
 * - About Us page
 * 
 * @dependencies
 * - vue-router
 * - Component imports from across the application
 * 
 * @returns {VueRouter} A configured Vue Router instance with history mode enabled
 * and all application routes defined, ready for integration with the Vue application.
 */
import { createRouter, createWebHistory } from "vue-router";

import AboutUs from "@/components/Overviews/AboutUs.vue";
import HomeView from "@/components/Overviews/HomeView.vue";
import InvoiceView from "@/components/Overviews/InvoiceView.vue";
import SupplierView from "@/components/Overviews/SupplierView.vue";
import FinancialRiskView from "@/components/Overviews/FinancialRiskView.vue";
import CounterpartiesView from "@/components/Overviews/CounterpartiesView.vue";
import IssuePatternsView from "@/components/Overviews/IssuePatternsView.vue";

const routes = [
  { path: "/", name: "Home", component: HomeView },
  { path: "/invoice", name: "InvoiceView", component: InvoiceView },
  { path: "/suppliers", name: "SupplierView", component: SupplierView },
  { path: "/financial-risk", name: "FinancialRiskView", component: FinancialRiskView },
  { path: "/counterparties", name: "CounterpartiesView", component: CounterpartiesView },
  { path: "/issue-patterns", name: "IssuePatternsView", component: IssuePatternsView },
  { path: "/about-us", name: "AboutUs", component: AboutUs },
];

// Create the router instance
const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
