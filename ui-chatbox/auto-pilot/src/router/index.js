
import { createRouter, createWebHistory } from "vue-router";
import WorkflowView from "@/views/WorkflowView.vue";

export default createRouter({
  history: createWebHistory(),
  routes: [{ path: "/", component: WorkflowView }]
});
