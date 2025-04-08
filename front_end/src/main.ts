import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import ElementPlusPlugin from './plugins/element-plus'
import { useAuthStore } from './stores/auth'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(ElementPlusPlugin)

// 初始化认证状态
// 必须在挂载前初始化Pinia
const authStore = useAuthStore()
if (authStore.isAuthenticated) {
  console.log('应用启动时检测到登录状态，验证会话...')
  authStore.validateSession().then((valid) => {
    console.log('会话验证结果:', valid ? '有效' : '无效')
  })
}

app.mount('#app')