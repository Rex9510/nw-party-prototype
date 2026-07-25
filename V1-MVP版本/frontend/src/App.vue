<script setup lang="ts">
import { onLaunch } from '@dcloudio/uni-app'

onLaunch(() => {
  console.log('南湾党建 V1-MVP 启动')

  // 拦截所有路由跳转：未登录跳登录页（登录页自身除外）
  const allowList = ['/pages/login/index']

  uni.addInterceptor('navigateTo', {
    invoke(args) {
      const auth = uni.getStorageSync('nwparty_auth')
      if (!auth || !auth.token) {
        if (!allowList.includes(args.url.split('?')[0])) {
          uni.reLaunch({ url: '/pages/login/index' })
          return false
        }
      }
      return true
    },
  })

  uni.addInterceptor('redirectTo', {
    invoke(args) {
      const auth = uni.getStorageSync('nwparty_auth')
      if (!auth || !auth.token) {
        if (!allowList.includes(args.url.split('?')[0])) {
          uni.reLaunch({ url: '/pages/login/index' })
          return false
        }
      }
      return true
    },
  })

  uni.addInterceptor('reLaunch', {
    invoke(args) {
      const auth = uni.getStorageSync('nwparty_auth')
      if (!auth || !auth.token) {
        if (!allowList.includes(args.url.split('?')[0])) {
          args.url = '/pages/login/index'
        }
      }
      return true
    },
  })

  // 启动时检查：未登录则跳登录
  const auth = uni.getStorageSync('nwparty_auth')
  if (!auth || !auth.token) {
    const pages = getCurrentPages()
    const current = pages.length > 0 ? pages[pages.length - 1] : null
    if (!current || current.route !== 'pages/login/index') {
      uni.reLaunch({ url: '/pages/login/index' })
    }
  }
})
</script>

<style lang="scss">
page {
  background: #F7F8FA;
  font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Helvetica Neue', sans-serif;
}
</style>
