/**
 * 设备检测：判断当前是 PC 还是 H5 移动端。
 * 断点：>= 768px 视为 PC。
 * 监听 resize 实时更新，SSR 友好。
 */
import { ref, onMounted, onBeforeUnmount } from 'vue'

const BREAKPOINT = 768

const isPC = ref(false)
const windowWidth = ref(0)
const windowHeight = ref(0)

function update() {
  if (typeof window === 'undefined') return
  windowWidth.value = window.innerWidth
  windowHeight.value = window.innerHeight
  isPC.value = window.innerWidth >= BREAKPOINT
}

let inited = false
let off: (() => void) | null = null

export function useDevice() {
  if (typeof window === 'undefined') {
    return { isPC, windowWidth, windowHeight, isMobile: isPC }
  }
  if (!inited) {
    inited = true
    update()
    const handler = () => update()
    window.addEventListener('resize', handler)
    off = () => window.removeEventListener('resize', handler)
  }
  // 让组件 setup 时也能拿到（reactive 已自动同步）
  return {
    isPC,
    windowWidth,
    windowHeight,
    isMobile: isPC, // 反向 alias（语义更清晰，使用时按需用）
  }
}

// 在 setup 外访问（如 router 守卫中）也能用
export function getIsPC() {
  if (typeof window === 'undefined') return false
  return window.innerWidth >= BREAKPOINT
}
