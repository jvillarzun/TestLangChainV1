import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const PHASES = ['init', 'prd', 'ux', 'arch', 'dev', 'qa', 'infra', 'sec', 'done']
const PHASE_LABELS = {
  init: 'INIT', prd: 'PRD', ux: 'UX', arch: 'ARQ',
  dev: 'DEV', qa: 'QA', infra: 'INFRA', sec: 'SEC', done: 'DONE'
}

export const useCycleStore = defineStore('cycle', () => {
  const threadId   = ref(localStorage.getItem('mach_thread_id') || '')
  const status     = ref(null)
  const loading    = ref(false)
  const error      = ref(null)
  const polling    = ref(false)
  let   _pollTimer = null

  const phaseIndex = computed(() => {
    if (!status.value) return -1
    return PHASES.indexOf(status.value.current_phase)
  })

  const phaseStatuses = computed(() => {
    if (!status.value) return {}
    const current = status.value.current_phase
    const decisions = status.value.hitl_decisions || []
    const result = {}

    for (const phase of PHASES) {
      const idx = PHASES.indexOf(phase)
      const curIdx = PHASES.indexOf(current)
      const decision = decisions.filter(d => d.phase === phase).pop()

      if (phase === 'init' || phase === 'done') {
        result[phase] = curIdx > idx ? 'done' : curIdx === idx ? 'active' : 'pending'
        continue
      }

      if (decision?.decision === 'approve') {
        result[phase] = 'approved'
      } else if (decision?.decision === 'reject' && curIdx === idx) {
        result[phase] = 'rejected'
      } else if (curIdx === idx) {
        result[phase] = status.value.hitl_pending_phase === phase ? 'hitl' : 'active'
      } else if (curIdx > idx) {
        result[phase] = 'approved'
      } else {
        result[phase] = 'pending'
      }
    }
    return result
  })

  async function fetchStatus() {
    if (!threadId.value) return
    loading.value = true
    error.value = null
    try {
      const res = await fetch(`/api/cycle/status/${threadId.value}`)
      if (!res.ok) throw new Error(`${res.status}`)
      status.value = await res.json()
    } catch (e) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  function setThread(id) {
    threadId.value = id
    localStorage.setItem('mach_thread_id', id)
    fetchStatus()
  }

  function startPolling(intervalMs = 3000) {
    stopPolling()
    polling.value = true
    _pollTimer = setInterval(fetchStatus, intervalMs)
    fetchStatus()
  }

  function stopPolling() {
    polling.value = false
    if (_pollTimer) { clearInterval(_pollTimer); _pollTimer = null }
  }

  async function fetchRecentThreads() {
    try {
      const res = await fetch('/api/cycle/recent')
      if (!res.ok) return []
      const data = await res.json()
      return data.threads || []
    } catch { return [] }
  }

  return {
    threadId, status, loading, error, polling,
    phaseIndex, phaseStatuses,
    fetchStatus, setThread, startPolling, stopPolling, fetchRecentThreads,
    PHASES, PHASE_LABELS,
  }
})
