import { createRouter, createWebHistory } from 'vue-router';
import type { RouteRecordRaw } from 'vue-router';
import { ElMessage } from 'element-plus'
import Home from '../views/HomePage.vue';
import Areas from '../views/AreasView.vue';
import DataScreen from "../views/DataScreen.vue";
import Auth from "../views/AuthView.vue";
import AdminView from '../views/AdminView.vue'
import UserView from '../views/UserView.vue';
import AlertNotice from "../views/AlertNotice.vue";
import NotFound from "../views/NotFound.vue";
import TerminalView from '../views/TerminalView.vue';
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
    path: '/login',
    name: 'Login',
    component: Auth,
    meta: { authMode: 'login' }
  },
  {
    path: '/register',
    name: 'Register',
    component: Auth,
    meta: { authMode: 'register' }
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
    meta: { requiresAuth: true }
  },
  {
    path: '/terminal',
    name: 'terminal',
    component: TerminalView,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/admin',
    name: 'admin',
    component: AdminView,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: NotFound
  }
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  if (to.matched.some(record => record.meta.requiresAuth)) {
    if (!authStore.isAuthenticated) {
      next({
        path: '/login',
      })
    } 
    else if (to.matched.some(record => record.meta.requiresAdmin) && authStore.user?.role !== 'admin') {
      ElMessage.error('您没有访问管理面板的权限')
      next({ path: '/' }) 
    }
    else {
      next() 
    }
  } else {
    next() 
  }
})

export default router