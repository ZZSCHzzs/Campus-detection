import { createApp } from 'vue'
import { createPinia } from 'pinia'

import App from './App.vue'
import router from './router'

import ElementPlusPlugin from './plugins/element-plus'

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(ElementPlusPlugin)

app.mount('#app')