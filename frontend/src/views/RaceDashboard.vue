<template>
  <div class="space-y-6 animate-slide-in">
    <!-- Thread ID input -->
    <div class="card flex items-center gap-3">
      <span class="text-slate-400 text-sm shrink-0">Thread ID:</span>
      <input
        v-model="inputThread"
        placeholder="Pega el thread_id del ciclo..."
        class="flex-1 bg-slate-800 border border-slate-600 rounded px-3 py-1.5 text-sm text-white font-mono focus:outline-none focus:border-amber-500 transition-colors"
        @keydown.enter="loadThread"
      />
      <button class="btn-primary text-sm" @click="loadThread">Cargar</button>
      <button
        class="text-sm px-3 py-1.5 rounded border transition-colors"
        :class="store.polling ? 'border-emerald-500 text-emerald-400 hover:bg-emerald-500/10' : 'btn-secondary'"
        @click="togglePolling"
      >
        {{ store.polling ? '⏹ Stop' : '▶ Polling' }}
      </button>
    </div>

    <!-- No thread state -->
    <div v-if="!store.threadId" class="card text-center py-16 text-slate-500">
      <div class="text-4xl mb-4">🏁</div>
      <p class="text-sm">Inicia un nuevo ciclo o pega un Thread ID para ver el estado de la carrera.</p>
      <RouterLink to="/new" class="btn-primary inline-block mt-4 text-sm">Nuevo Ciclo →</RouterLink>
    </div>

    <!-- Race Track -->
    <div v-else class="space-y-4">
      <div class="card">
        <div class="flex items-center justify-between mb-4">
          <div>
            <h2 class="text-white font-semibold text-lg">
              {{ store.status?.challenge_name || 'Cargando...' }}
              <span v-if="store.status?.challenge_type" class="text-xs text-slate-500 ml-2 uppercase">
                {{ store.status.challenge_type }}
              </span>
            </h2>
            <p class="text-xs text-slate-500 font-mono mt-0.5">{{ store.threadId }}</p>
          </div>
          <div class="text-right">
            <div
              class="phase-badge text-sm"
              :style="{ background: phaseColor + '22', color: phaseColor, border: `1px solid ${phaseColor}44` }"
            >
              {{ store.PHASE_LABELS[store.status?.current_phase] || '—' }}
            </div>
            <div v-if="store.status?.jira_epic_key" class="text-xs text-slate-500 mt-1">
              Jira: {{ store.status.jira_epic_key }}
            </div>
          </div>
        </div>

        <div v-if="store.loading && !store.status" class="text-center py-8 text-slate-500 text-sm">
          Cargando estado...
        </div>
        <RaceTrack
          v-else
          :phase-statuses="store.phaseStatuses"
          :current-phase="store.status?.current_phase || 'init'"
          :challenge-name="store.status?.challenge_name || ''"
        />
      </div>

      <!-- Error banner -->
      <div v-if="store.status?.error_phase" class="card border-red-500/50 bg-red-500/5">
        <div class="text-red-400 text-sm font-semibold">⚠ Error en fase {{ store.status.error_phase }}</div>
        <div class="text-red-300 text-xs mt-1 font-mono">{{ store.status.error_message }}</div>
      </div>

      <!-- HITL pending notice with manual controls -->
      <div v-if="store.status?.hitl_pending_phase" class="card border-orange-500/50 bg-orange-500/5">
        <div class="flex items-start gap-3 mb-4">
          <span class="text-2xl">⏸</span>
          <div class="flex-1">
            <div class="text-orange-300 font-semibold text-sm">Esperando aprobación humana</div>
            <div class="text-slate-400 text-xs mt-0.5">
              Fase <strong class="text-white">{{ store.status.hitl_pending_phase.toUpperCase() }}</strong>
              — puedes aprobar/rechazar aquí o desde Slack
            </div>
          </div>
        </div>

        <!-- Manual HITL Controls -->
        <div class="space-y-3">
          <!-- Action buttons -->
          <div class="flex gap-2">
            <button
              @click="approvePhase"
              :disabled="isSubmitting"
              class="flex-1 px-4 py-2 rounded font-medium text-sm transition-all"
              :class="isSubmitting 
                ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
                : 'bg-emerald-600 hover:bg-emerald-700 text-white'"
            >
              {{ isSubmitting ? '⏳ Procesando...' : '✅ Aprobar Fase' }}
            </button>
            <button
              @click="toggleRejectForm"
              :disabled="isSubmitting"
              class="flex-1 px-4 py-2 rounded font-medium text-sm transition-all"
              :class="isSubmitting 
                ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
                : showFeedbackForm 
                  ? 'bg-slate-700 text-slate-300' 
                  : 'bg-red-600 hover:bg-red-700 text-white'"
            >
              {{ showFeedbackForm ? '↩ Cancelar' : '❌ Rechazar / Enviar Feedback' }}
            </button>
          </div>

          <!-- Feedback form (shown on reject) -->
          <div v-if="showFeedbackForm" class="space-y-2 animate-slide-in">
            <label class="block text-xs text-slate-400 font-semibold">Motivo del rechazo:</label>
            <textarea
              v-model="feedbackText"
              placeholder="Describe qué debe corregirse en esta fase..."
              rows="4"
              class="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-red-500 transition-colors resize-none"
            ></textarea>
            <button
              @click="rejectPhase"
              :disabled="isSubmitting || !feedbackText.trim()"
              class="w-full px-4 py-2 rounded font-medium text-sm transition-all"
              :class="isSubmitting || !feedbackText.trim()
                ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
                : 'bg-red-600 hover:bg-red-700 text-white'"
            >
              {{ isSubmitting ? '⏳ Enviando...' : 'Confirmar Rechazo' }}
            </button>
          </div>

          <!-- Error message -->
          <div v-if="submitError" class="text-red-400 text-xs bg-red-500/10 border border-red-500/30 rounded px-3 py-2">
            ⚠ Error: {{ submitError }}
          </div>

          <!-- Success message -->
          <div v-if="submitSuccess" class="text-emerald-400 text-xs bg-emerald-500/10 border border-emerald-500/30 rounded px-3 py-2">
            ✅ {{ submitSuccess }}
          </div>
        </div>
      </div>

      <!-- Decision history -->
      <div v-if="store.status?.hitl_decisions?.length" class="card">
        <h3 class="text-slate-300 font-semibold text-sm mb-3">Historial de decisiones</h3>
        <div class="space-y-2">
          <div
            v-for="(d, i) in [...store.status.hitl_decisions].reverse()" :key="i"
            class="flex items-start gap-3 text-xs py-2 border-b border-slate-800 last:border-0"
          >
            <span class="shrink-0 text-base">{{ d.decision === 'approve' ? '✅' : '❌' }}</span>
            <div class="flex-1">
              <span class="text-white font-semibold uppercase">{{ d.phase }}</span>
              <span class="text-slate-500 ml-2">{{ d.decision }}</span>
              <span v-if="d.feedback" class="block text-slate-400 mt-0.5 italic">
                "{{ d.feedback }}"
              </span>
            </div>
            <span class="text-slate-600 shrink-0">{{ formatTime(d.timestamp) }}</span>
          </div>
        </div>
      </div>

      <!-- ROI Card -->
      <div v-if="roiData.totalTokens > 0 || store.status?.current_phase !== 'init'" class="card">
        <h3 class="text-slate-300 font-semibold text-sm mb-3">⚡ ROI del Ciclo</h3>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-4">
          <div class="bg-slate-800 rounded px-3 py-2 text-center">
            <div class="text-xs text-slate-500 uppercase tracking-wider">Tokens totales</div>
            <div class="text-white font-bold text-lg mt-0.5">{{ roiData.totalTokens.toLocaleString() }}</div>
          </div>
          <div class="bg-slate-800 rounded px-3 py-2 text-center">
            <div class="text-xs text-slate-500 uppercase tracking-wider">Costo IA</div>
            <div class="text-emerald-400 font-bold text-lg mt-0.5">${{ roiData.totalCost.toFixed(4) }}</div>
          </div>
          <div class="bg-slate-800 rounded px-3 py-2 text-center">
            <div class="text-xs text-slate-500 uppercase tracking-wider">Tiempo IA</div>
            <div class="text-amber-400 font-bold text-lg mt-0.5">{{ roiData.durationMin }} min</div>
          </div>
          <div class="bg-slate-800 rounded px-3 py-2 text-center">
            <div class="text-xs text-slate-500 uppercase tracking-wider">Ratio ahorro</div>
            <div class="text-purple-400 font-bold text-lg mt-0.5">{{ roiData.savingsRatio }}</div>
            <div class="text-xs text-slate-600">humano {{ roiData.humanCostLabel }}</div>
          </div>
        </div>
        <div class="text-[11px] text-slate-500 mb-4">
          Costo humano estimado: {{ roiData.humanCostLabel }} vs costo IA ${{ roiData.totalCost.toFixed(4) }}
        </div>
        <table v-if="roiData.perAgent.length" class="w-full text-xs">
          <thead>
            <tr class="text-slate-500 uppercase tracking-wider border-b border-slate-800">
              <th class="text-left pb-1">Agente</th>
              <th class="text-right pb-1">Tokens</th>
              <th class="text-right pb-1">Costo</th>
              <th class="text-right pb-1">Tiempo</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in roiData.perAgent" :key="row.agent" class="border-b border-slate-800/50 last:border-0">
              <td class="py-1 text-amber-400 font-semibold uppercase">{{ row.agent }}</td>
              <td class="py-1 text-right text-slate-300">{{ row.total_tokens.toLocaleString() }}</td>
              <td class="py-1 text-right text-emerald-400">${{ row.cost_usd.toFixed(4) }}</td>
              <td class="py-1 text-right text-slate-400">{{ row.duration_s }}s</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="text-xs text-slate-600 text-center py-2">Los datos de tokens aparecerán a medida que corran los agentes.</div>
      </div>

      <!-- Deliverables -->
      <div class="card">
        <h3 class="text-slate-300 font-semibold text-sm mb-3">Entregables</h3>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <a
            v-for="file in deliverables" :key="file"
            :href="`/view/${file}`" target="_blank"
            class="text-xs text-center py-2 px-3 rounded bg-slate-800 border border-slate-700 hover:border-amber-500/50 hover:text-amber-400 text-slate-300 transition-colors"
          >
            📄 {{ file }}
          </a>
        </div>
      </div>

      <!-- Pull Requests Generados -->
      <div v-if="prUrls.length > 0" class="card border-emerald-500/30 bg-emerald-500/5">
        <div class="flex items-center gap-2 mb-3">
          <span class="text-2xl">🔗</span>
          <h3 class="text-emerald-300 font-semibold text-sm">Pull Requests Generados</h3>
          <span class="text-xs text-slate-500 bg-slate-800 px-2 py-0.5 rounded">{{ prUrls.length }}</span>
        </div>
        <div class="space-y-2">
          <a
            v-for="(url, index) in prUrls" :key="url"
            :href="url"
            target="_blank"
            rel="noopener noreferrer"
            class="flex items-center gap-3 p-3 rounded bg-slate-800 border border-emerald-600/30 hover:border-emerald-500 hover:bg-emerald-500/10 transition-all group"
          >
            <span class="text-xl">🚀</span>
            <div class="flex-1">
              <div class="text-white font-medium text-sm group-hover:text-emerald-400 transition-colors">
                {{ getRepoLabel(url) }} Pull Request
              </div>
              <div class="text-xs text-slate-400 font-mono truncate mt-0.5">{{ url }}</div>
            </div>
            <svg class="w-4 h-4 text-slate-500 group-hover:text-emerald-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
            </svg>
          </a>
        </div>
      </div>
    </div>

    <!-- Recent cycles -->
    <div v-if="recentThreads.length" class="card">
      <h3 class="text-slate-400 text-xs font-semibold uppercase tracking-wider mb-2">Ciclos recientes</h3>
      <div class="space-y-1">
        <button
          v-for="t in recentThreads" :key="t"
          class="w-full text-left text-xs text-slate-400 hover:text-white font-mono py-1 px-2 rounded hover:bg-slate-800 transition-colors"
          :class="t === store.threadId ? 'text-amber-400' : ''"
          @click="store.setThread(t)"
        >
          {{ t }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useCycleStore } from '../stores/cycleStore.js'
import RaceTrack from '../components/RaceTrack.vue'

const store = useCycleStore()
const inputThread = ref(store.threadId)
const recentThreads = ref([])

// HITL manual controls state
const showFeedbackForm = ref(false)
const feedbackText = ref('')
const isSubmitting = ref(false)
const submitError = ref(null)
const submitSuccess = ref(null)

const DELIVERABLE_FILES = [
  'PRDSPECS.md', 'UXSPECS.md', 'ARQSPECS.md',
  'DEVSPECS.md', 'QASPECS.md', 'INFESPECS.md', 'DEVSECOPS.md'
]

const deliverables = DELIVERABLE_FILES

const PHASE_COLORS = {
  init: '#94a3b8', prd: '#f59e0b', ux: '#f59e0b', arch: '#f59e0b',
  dev: '#f59e0b', qa: '#f59e0b', infra: '#f59e0b', sec: '#f59e0b', done: '#10b981',
}

const phaseColor = computed(() =>
  PHASE_COLORS[store.status?.current_phase] || '#94a3b8'
)

const roiData = computed(() => {
  const usage = store.status?.token_usage || []
  const humanCost = 6000
  const totalTokens = usage.reduce((s, u) => s + (u.total_tokens || 0), 0)
  const totalCost   = usage.reduce((s, u) => s + (u.cost_usd || 0), 0)
  const totalSecs   = usage.reduce((s, u) => s + (u.duration_s || 0), 0)

  const cycleStart = store.status?.cycle_start_time
  const cycleEnd = store.status?.cycle_end_time
  const startedAt = cycleStart ? new Date(cycleStart).getTime() : NaN
  const endedAt = cycleEnd ? new Date(cycleEnd).getTime() : Date.now()
  const hasValidTimestamps = Number.isFinite(startedAt) && Number.isFinite(endedAt) && endedAt >= startedAt
  const durationMin = hasValidTimestamps
    ? Math.max(0, Math.round((endedAt - startedAt) / 60000))
    : Math.max(0, Math.round(totalSecs / 60))

  // Agrupa por agente sumando todos sus runs (re-runs por HITL)
  const agentMap = {}
  for (const u of usage) {
    const key = u.agent || 'unknown'
    if (!agentMap[key]) agentMap[key] = { agent: key, total_tokens: 0, cost_usd: 0, duration_s: 0 }
    agentMap[key].total_tokens += u.total_tokens || 0
    agentMap[key].cost_usd    += u.cost_usd    || 0
    agentMap[key].duration_s  += u.duration_s  || 0
  }
  const perAgent = Object.values(agentMap).map(r => ({
    ...r,
    cost_usd:   Math.round(r.cost_usd * 1e6) / 1e6,
    duration_s: Math.round(r.duration_s * 10) / 10,
  }))

  const savingsRatio = totalCost > 0
    ? `${Math.round(humanCost / totalCost).toLocaleString()}x`
    : '∞'

  return {
    totalTokens,
    totalCost,
    durationMin,
    perAgent,
    savingsRatio,
    humanCostLabel: `~$${humanCost.toLocaleString()}`,
  }
})

// Pull Requests URLs del agente DEV
const prUrls = computed(() => {
  const urls = store.status?.dev_pr_urls || []
  // Fallback: si dev_pr_urls está vacío pero existe dev_pr_url, usarlo
  if (urls.length === 0 && store.status?.dev_pr_url) {
    return [store.status.dev_pr_url]
  }
  return urls
})

function loadThread() {
  if (inputThread.value.trim()) {
    store.setThread(inputThread.value.trim())
  }
}

function togglePolling() {
  if (store.polling) store.stopPolling()
  else store.startPolling()
}

function toggleRejectForm() {
  showFeedbackForm.value = !showFeedbackForm.value
  if (!showFeedbackForm.value) {
    feedbackText.value = ''
  }
  submitError.value = null
  submitSuccess.value = null
}

async function approvePhase() {
  if (!store.threadId || isSubmitting.value) return
  
  isSubmitting.value = true
  submitError.value = null
  submitSuccess.value = null

  try {
    const response = await fetch('/api/cycle/resume', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        thread_id: store.threadId,
        decision: 'approve',
        feedback: ''
      })
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || `Error ${response.status}`)
    }

    submitSuccess.value = 'Fase aprobada exitosamente. Actualizando estado...'
    
    // Wait a bit and reload state
    setTimeout(() => {
      store.fetchStatus()
      submitSuccess.value = null
    }, 1500)
  } catch (error) {
    submitError.value = error.message
  } finally {
    isSubmitting.value = false
  }
}

async function rejectPhase() {
  if (!store.threadId || isSubmitting.value || !feedbackText.value.trim()) return

  isSubmitting.value = true
  submitError.value = null
  submitSuccess.value = null

  try {
    const response = await fetch('/api/cycle/resume', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        thread_id: store.threadId,
        decision: 'reject',
        feedback: feedbackText.value.trim()
      })
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.detail || `Error ${response.status}`)
    }

    submitSuccess.value = 'Feedback enviado exitosamente. El agente re-ejecutará la fase.'
    feedbackText.value = ''
    showFeedbackForm.value = false
    
    // Wait a bit and reload state
    setTimeout(() => {
      store.fetchStatus()
      submitSuccess.value = null
    }, 1500)
  } catch (error) {
    submitError.value = error.message
  } finally {
    isSubmitting.value = false
  }
}

function formatTime(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' })
  } catch { return iso }
}

function getRepoLabel(url) {
  if (!url) return 'GitHub'
  const lower = url.toLowerCase()
  if (lower.includes('backend')) return '🏭 Backend'
  if (lower.includes('frontend')) return '🎨 Frontend'
  // Intentar extraer el nombre del repo de la URL
  const match = url.match(/github\.com\/[^\/]+\/([^\/]+)/)
  return match ? match[1] : 'GitHub'
}

onMounted(async () => {
  recentThreads.value = await store.fetchRecentThreads()
  if (store.threadId) store.startPolling()
})

onUnmounted(() => store.stopPolling())
</script>
