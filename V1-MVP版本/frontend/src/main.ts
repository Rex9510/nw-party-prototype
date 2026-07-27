import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './utils/uni-shim'  // 把 window.uni 挂上

// 显式 import Vant 函数式 API 用的样式（unplugin-vue-components 只对模板里
// 用到的组件自动注入样式，showDialog/showConfirmDialog/showToast 这种
// 函数式调用不会触发，所以这里手动 import）
import 'vant/es/dialog/style'
import 'vant/es/toast/style'
import 'vant/es/notify/style'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
