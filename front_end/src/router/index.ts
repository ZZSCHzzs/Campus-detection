// src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router';
import type { RouteRecordRaw } from 'vue-router';
import Home from '../views/HomePage.vue';
import Areas from '../views/AreasView.vue';
import DataScreen from "../views/DataScreen.vue";

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
];

const router = createRouter({
    history: createWebHistory(), // 使用 HTML5 历史模式
    routes,
});

export default router;