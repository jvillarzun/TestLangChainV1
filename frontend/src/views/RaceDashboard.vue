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

      <!-- HITL pending notice -->
      <div v-if="store.status?.hitl_pending_phase" class="card border-orange-500/50 bg-orange-500/5 flex items-center gap-3">
        <span class="text-2xl">⏸</span>
        <div>
          <div class="text-orange-300 font-semibold text-sm">Esperando aprobación humana</div>
          <div class="text-slate-400 text-xs mt-0.5">
            Fase <strong class="text-white">{{ store.status.hitl_pending_phase.toUpperCase() }}</strong>
            — revisar DM en Slack
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

function loadThread() {
  if (inputThread.value.trim()) {
    store.setThread(inputThread.value.trim())
  }
}

function togglePolling() {
  if (store.polling) store.stopPolling()
  else store.startPolling()
}

function formatTime(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' })
  } catch { return iso }
}

onMounted(async () => {
  recentThreads.value = await store.fetchRecentThreads()
  if (store.threadId) store.startPolling()
})

onUnmounted(() => store.stopPolling())
</script>
