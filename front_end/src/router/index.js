import { createRouter, createWebHistory } from 'vue-router';

// 导入视图组件
import Index from "@/views/Index.vue";
import Areas from "@/views/Areas.vue";
import DataScreen from "@/views/DataScreen.vue";
import Map from "@/views/2DMap.vue";
const routes = [
  { path: '/', redirect: '/index' },
  { path: '/index', name: 'index', component: Index },
  { path: '/areas', name: 'areas', component: Areas },
  { path: '/data-screen', name: 'data-screen', component: DataScreen },
  { path: '/map', name: 'map', component: Map },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;