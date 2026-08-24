// 时间排序状态管理 — 支持 localStorage 持久化 + 响应式排序
import { ref, watch } from 'vue'

const STORAGE_KEY = 'techhub_sort_prefs'

function loadPrefs() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch { return {} }
}

function savePrefs(prefs) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs))
}

const prefs = loadPrefs()

export function useSort(moduleKey) {
  const order = ref(prefs[moduleKey] || 'desc')

  watch(order, (val) => {
    prefs[moduleKey] = val
    savePrefs(prefs)
  })

  function sortItems(items) {
    if (!items || !items.length) return items
    return [...items].sort((a, b) => {
      const ta = a.created_at || a.date || String(a.id || '')
      const tb = b.created_at || b.date || String(b.id || '')
      return order.value === 'asc' ? String(ta).localeCompare(String(tb)) : String(tb).localeCompare(String(ta))
    })
  }

  /**
   * 返回响应式排序结果 — 当 order 或 sourceItems 变化时自动重新排序
   */
  function useSorted(sourceRef) {
    const sorted = ref([])
    watch(
      [sourceRef, order],
      () => {
        sorted.value = sortItems(sourceRef.value)
      },
      { immediate: true, deep: false }
    )
    return sorted
  }

  return { order, useSorted }
}