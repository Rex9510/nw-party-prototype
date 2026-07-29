/**
 * 日期时间格式化工具
 */

/** 把 ISO datetime（"2026-07-29T10:00:00"）格式化成 "2026-07-29 10:00"。 */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return ''
  // 处理带毫秒/时区/不带 T 的各种情况
  const s = String(iso).replace('T', ' ').replace('Z', '').replace(/\.\d+/, '')
  // 去掉小数秒和时区偏移："2026-07-29 10:00:00+08:00" → "2026-07-29 10:00:00"
  // 然后截到分钟
  const m = s.match(/^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})/)
  if (m) return `${m[1]} ${m[2]}`
  return s
}

/** 把 ISO date（"2026-07-29"）格式化成 "2026年07月29日"。 */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return ''
  const m = String(iso).match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (m) return `${m[1]}年${Number(m[2])}月${Number(m[3])}日`
  return String(iso)
}
