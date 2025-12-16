import { createRouter, createWebHistory } from "vue-router";

import Dashboard from "@/views/Dashboard.vue";
import Parts from "@/views/Parts.vue";
import StepAnalyse from "@/views/StepAnalyse.vue";
import MachineReport from "@/views/MachineReport.vue";

const routes = [
  routes: [{ path: "/", component:  Dashboard}]
  { path: "/parts", component: Parts },
  { path: "/steps", component: StepAnalyse },
  { path: "/machines", component: MachineReport },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
