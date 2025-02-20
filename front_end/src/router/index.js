import { createRouter, createWebHistory } from 'vue-router';

// 导入视图组件
import HomeView from '../views/HomeView.vue';
import RealTimeView from '../views/RealTimeView.vue';
import HistoryView from '../views/HistoryView.vue';
import AlertsView from '../views/AlertsView.vue';
import SettingsView from '../views/SettingsView.vue';

const routes = [
  { path: '/', name: 'Home', component: HomeView },
  { path: '/realtime', name: 'RealTime', component: RealTimeView },
  { path: '/history', name: 'History', component: HistoryView },
  { path: '/alerts', name: 'Alerts', component: AlertsView },
  { path: '/settings', name: 'Settings', component: SettingsView },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;