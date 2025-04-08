// src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router';
import type { RouteRecordRaw } from 'vue-router';
import Home from '../views/HomePage.vue';
import Areas from '../views/AreasView.vue';
import DataScreen from "../views/DataScreen.vue";
import Auth from "../views/AuthView.vue";
import AdminView from '../views/AdminView.vue'
import UserView from '../views/UserView.vue';
import AlertNotice from "../views/AlertNotice.vue";
import { useAuthStore } from '../stores/auth'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    name: 'Home',
    component: Home,
  },
  {
    path: '/index',
    redirect: '/',
  },
  {
    path: '/areas',
    name: 'Areas',
    component: Areas,
  },
  {
    path: '/screen',
    name: 'DataScreen',
    component: DataScreen,
  },
  {
    path: '/auth',
    name: 'Auth',
    component: Auth,
  },
  {
    path: '/alerts',
    name: 'AlertNotice',
    component: AlertNotice,
  },
  {
    path: '/profile',
    name: 'UserProfile',
    component: UserView,
    meta: { requiresAuth: true } // 需要认证的路由
  },
  {
    path: '/admin',
    name: 'admin',
    component: AdminView,
    meta: { requiresAuth: true }
  }
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

// 添加路由守卫
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  // 检查路由是否需要认证
  if (to.matched.some(record => record.meta.requiresAuth)) {
    // 如果需要认证且用户未登录，重定向到登录页
    if (!authStore.isAuthenticated) {
      next({
        path: '/auth',
        query: { mode: 'login', redirect: to.fullPath }
      })
    } else {
      next() // 已登录，正常跳转
    }
  } else {
    next() // 不需要认证，正常跳转
  }
})

export default router