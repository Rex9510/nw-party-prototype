/**
 * uni-app 全局 API 的 web 替代实现
 * 替代：uni.showToast / uni.showModal / uni.showActionSheet / uni.chooseFile / uni.uploadFile
 * 替代：uni.navigateTo / uni.redirectTo / uni.reLaunch / uni.switchTab / uni.navigateBack
 * 替代：uni.setStorageSync / uni.getStorageSync / uni.removeStorageSync
 * 替代：uni.getCurrentPages / uni.addInterceptor / uni.chooseMessageFile
 *
 * 通过 import { ... } from '@/utils/uni-shim' 在组件中显式调用，
 * 或在 main.ts 中挂到 window.uni
 */

import { showToast, showDialog, showConfirmDialog } from 'vant'
import router from '@/router'

const STORAGE_PREFIX = 'nwparty_'

function setStorage(key: string, value: any) {
  try { localStorage.setItem(key, JSON.stringify(value)) } catch {}
}
function getStorage(key: string): any {
  try {
    const raw = localStorage.getItem(key)
    if (raw === null || raw === undefined) return ''
    try { return JSON.parse(raw) } catch { return raw }
  } catch { return '' }
}
function removeStorage(key: string) {
  try { localStorage.removeItem(key) } catch {}
}

function showToastFn(opts: any) {
  const message = typeof opts === 'string' ? opts : (opts?.message || opts?.title || '')
  const type = opts?.icon === 'success' || opts?.type === 'success' ? 'success' :
               opts?.icon === 'error' || opts?.icon === 'none' ? 'fail' : ''
  showToast({ message, type, duration: opts?.duration || 1500 })
}

function showModalFn(opts: any) {
  return new Promise<{ confirm: boolean; cancel: boolean }>((resolve) => {
    const onOk = () => {
      const r = { confirm: true, cancel: false }
      try { opts?.success?.(r) } catch {}
      resolve(r)
    }
    const onCancel = () => {
      const r = { confirm: false, cancel: true }
      try { opts?.success?.(r) } catch {}
      resolve(r)
    }
    showDialog({
      title: opts?.title || '提示',
      message: opts?.content || '',
      showCancelButton: opts?.showCancel !== false,
      confirmButtonText: opts?.confirmText || '确认',
      cancelButtonText: opts?.cancelText || '取消',
    })
      .then(onOk)
      .catch(onCancel)
  })
}

function showActionSheetFn(opts: any) {
  return new Promise<{ tapIndex: number }>((resolve) => {
    const items = opts?.itemList || []
    showDialog({
      title: opts?.title || '请选择',
      message: items.join('\n'),
      showCancelButton: true,
    })
      .then(() => {
        const r = { tapIndex: 0 }
        try { opts?.success?.(r) } catch {}
        resolve(r)
      })
      .catch(() => {
        const r = { tapIndex: -1 }
        try { opts?.success?.(r) } catch {}
        resolve(r)
      })
  })
}

function navigateToFn(opts: any) {
  return new Promise((resolve, reject) => {
    router.push(opts.url).then(resolve).catch(reject)
  })
}

function redirectToFn(opts: any) {
  return router.replace(opts.url)
}

function reLaunchFn(opts: any) {
  return router.push(opts.url).catch(() => router.replace(opts.url))
}

function switchTabFn(opts: any) {
  return router.push(opts.url)
}

function navigateBackFn(opts: any) {
  const delta = opts?.delta || 1
  return router.go(-delta)
}

function chooseFileFn(_opts: any) {
  return new Promise<{ tempFiles: any[] }>((resolve) => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'image/*'
    input.onchange = (e: any) => {
      const f = e.target.files?.[0]
      if (f) resolve({ tempFiles: [{ path: URL.createObjectURL(f), file: f, name: f.name, size: f.size }] })
      else resolve({ tempFiles: [] })
    }
    input.click()
  })
}

function uploadFileFn(opts: any) {
  return new Promise((resolve, reject) => {
    const formData = new FormData()
    if (opts.formData) {
      for (const [k, v] of Object.entries(opts.formData)) {
        formData.append(k, String(v))
      }
    }
    if (opts.files) {
      for (const [k, file] of Object.entries(opts.files)) {
        formData.append(k, file)
      }
    } else {
      formData.append('file', opts.file)
    }
    fetch(opts.url, {
      method: 'POST',
      headers: { Authorization: `Bearer ${getStorage(STORAGE_PREFIX + 'auth')?.token || ''}` },
      body: formData,
    })
      .then(async (r) => {
        const text = await r.text()
        try {
          resolve({ data: text, statusCode: r.status })
        } catch {
          resolve({ data: text, statusCode: r.status })
        }
      })
      .catch(reject)
  })
}

function downloadFileFn(opts: any) {
  return new Promise((resolve, reject) => {
    const a = document.createElement('a')
    a.href = opts.url
    a.download = opts.filename || ''
    document.body.appendChild(a)
    a.click()
    a.remove()
    resolve({ tempFilePath: opts.url })
  })
}

function getCurrentPagesFn() {
  // 简化：返回当前路由
  return [{ route: router.currentRoute.value.path?.replace(/^\//, '') || 'pages/index/index' }]
}

function addInterceptorFn(_type: string, _handler: any) {
  // no-op for web
}

function openDocumentFn(opts: any) {
  window.open(opts.filePath, '_blank')
}

function chooseMessageFileFn(opts: any) {
  return chooseFileFn(opts)
}

function downloadFileWeb(opts: any) {
  window.open(opts.url, '_blank')
  return Promise.resolve({ tempFilePath: opts.url })
}

// 挂到 window.uni
declare global {
  interface Window {
    uni: any
  }
}

if (typeof window !== 'undefined') {
  window.uni = {
    showToast: showToastFn,
    showModal: showModalFn,
    showActionSheet: showActionSheetFn,
    navigateTo: navigateToFn,
    redirectTo: redirectToFn,
    reLaunch: reLaunchFn,
    switchTab: switchTabFn,
    navigateBack: navigateBackFn,
    chooseFile: chooseFileFn,
    chooseMessageFile: chooseMessageFileFn,
    uploadFile: uploadFileFn,
    downloadFile: downloadFileFn,
    openDocument: openDocumentFn,
    getCurrentPages: getCurrentPagesFn,
    addInterceptor: addInterceptorFn,
    setStorageSync: (k: string, v: any) => setStorage(k, v),
    getStorageSync: (k: string) => getStorage(k),
    removeStorageSync: (k: string) => removeStorage(k),
  }
}

export {
  showToastFn as showToast,
  showModalFn as showModal,
  showActionSheetFn as showActionSheet,
  navigateToFn as navigateTo,
  redirectToFn as redirectTo,
  reLaunchFn as reLaunch,
  switchTabFn as switchTab,
  navigateBackFn as navigateBack,
  chooseFileFn as chooseFile,
  uploadFileFn as uploadFile,
  downloadFileFn as downloadFile,
  setStorage,
  getStorage,
  removeStorage,
}
