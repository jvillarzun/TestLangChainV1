<template>
  <div class="max-w-2xl mx-auto space-y-4 animate-slide-in">
    <div class="card">
      <h1 class="text-white font-bold text-xl mb-1">🚀 Nuevo Ciclo ADLC</h1>
      <p class="text-slate-400 text-sm">Configura y lanza un nuevo ciclo completo.</p>
    </div>

    <form @submit.prevent="submit" class="card space-y-4">
      <!-- Test mode toggle -->
      <div class="flex items-center justify-between p-3 rounded-lg bg-slate-800 border"
        :class="form.test_mode ? 'border-amber-500/50' : 'border-slate-700'">
        <div>
          <div class="text-sm font-semibold text-white">Modo Test</div>
          <div class="text-xs text-slate-400">Sin tokens Groq — stubs para HITL/Slack/Jira</div>
        </div>
        <button
          type="button"
          class="relative w-12 h-6 rounded-full transition-colors duration-200 focus:outline-none"
          :class="form.test_mode ? 'bg-amber-500' : 'bg-slate-600'"
          @click="form.test_mode = !form.test_mode"
        >
          <span
            class="absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform duration-200"
            :class="form.test_mode ? 'translate-x-6' : ''"
          />
        </button>
      </div>

      <!-- Challenge name -->
      <div>
        <label class="block text-xs text-slate-400 mb-1 uppercase tracking-wider">Nombre del Challenge</label>
        <input
          v-model="form.challenge_name"
          required
          placeholder="Ej: FraudShield, PaySplit, LoanBot..."
          class="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-amber-500 transition-colors"
        />
      </div>

      <!-- Challenge type -->
      <div>
        <label class="block text-xs text-slate-400 mb-1 uppercase tracking-wider">Tipo</label>
        <div class="flex gap-2">
          <button
            v-for="t in ['greenfield', 'brownfield']" :key="t"
            type="button"
            class="flex-1 py-2 rounded border text-sm font-semibold uppercase tracking-wider transition-colors"
            :class="form.challenge_type === t
              ? 'border-amber-500 bg-amber-500/10 text-amber-400'
              : 'border-slate-600 bg-slate-800 text-slate-400 hover:border-slate-500'"
            @click="form.challenge_type = t"
          >
            {{ t === 'greenfield' ? '🌱' : '🔧' }} {{ t }}
          </button>
        </div>
      </div>

      <!-- Description -->
      <div>
        <label class="block text-xs text-slate-400 mb-1 uppercase tracking-wider">Descripción del problema</label>
        <textarea
          v-model="form.challenge_description"
          required rows="4"
          placeholder="Describe el problema a resolver por el equipo MACH..."
          class="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-amber-500 transition-colors resize-none"
        />
      </div>

      <!-- Success criteria -->
      <div>
        <div class="flex items-center justify-between mb-1">
          <label class="text-xs text-slate-400 uppercase tracking-wider">Criterios de éxito</label>
          <button type="button" class="text-xs text-amber-400 hover:text-amber-300" @click="addCriteria">+ Agregar</button>
        </div>
        <div class="space-y-2">
          <div v-for="(_, i) in form.challenge_success_criteria" :key="i" class="flex gap-2">
            <input
              v-model="form.challenge_success_criteria[i]"
              :placeholder="`Criterio ${i + 1}...`"
              class="flex-1 bg-slate-800 border border-slate-600 rounded px-3 py-1.5 text-sm text-white font-mono focus:outline-none focus:border-amber-500 transition-colors"
            />
            <button
              v-if="form.challenge_success_criteria.length > 1"
              type="button"
              class="text-slate-500 hover:text-red-400 px-2 transition-colors"
              @click="removeCriteria(i)"
            >✕</button>
          </div>
        </div>
      </div>

      <!-- Submit -->
      <button
        type="submit"
        :disabled="submitting"
        class="w-full py-3 rounded font-bold text-sm uppercase tracking-widest transition-colors"
        :class="submitting ? 'bg-slate-700 text-slate-500 cursor-not-allowed' : 'bg-race-red hover:bg-red-700 text-white'"
      >
        {{ submitting ? '🏎️ Lanzando...' : '🏁 Lanzar Ciclo' }}
      </button>
    </form>

    <!-- Success -->
    <div v-if="result" class="card border-emerald-500/50 bg-emerald-500/5 space-y-3">
      <div class="text-emerald-400 font-semibold">✅ Ciclo iniciado</div>
      <div>
        <div class="text-xs text-slate-400 mb-1">Thread ID:</div>
        <code class="text-amber-300 text-sm font-mono break-all">{{ result.thread_id }}</code>
      </div>
      <div class="flex gap-2">
        <RouterLink to="/" class="btn-primary text-sm" @click="goToDashboard">Ver Dashboard →</RouterLink>
        <button class="btn-secondary text-sm" @click="copyThread">Copiar Thread ID</button>
      </div>
    </div>

    <!-- Error -->
    <div v-if="error" class="card border-red-500/50 bg-red-500/5 text-red-400 text-sm">
      ⚠ {{ error }}
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useCycleStore } from '../stores/cycleStore.js'

const router = useRouter()
const store = useCycleStore()

const form = reactive({
  challenge_name: '',
  challenge_type: 'greenfield',
  challenge_description: '',
  challenge_success_criteria: [''],
  test_mode: false,
})

const submitting = ref(false)
const result = ref(null)
const error = ref(null)

function addCriteria() { form.challenge_success_criteria.push('') }
function removeCriteria(i) { form.challenge_success_criteria.splice(i, 1) }

async function submit() {
  error.value = null
  result.value = null
  submitting.value = true
  try {
    const res = await fetch('/api/cycle/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...form,
        challenge_success_criteria: form.challenge_success_criteria.filter(c => c.trim()),
      }),
    })
    if (!res.ok) {
      const data = await res.json()
      throw new Error(data.detail || `Error ${res.status}`)
    }
    result.value = await res.json()
    store.setThread(result.value.thread_id)
    store.startPolling()
  } catch (e) {
    error.value = e.message
  } finally {
    submitting.value = false
  }
}

function goToDashboard() { router.push('/') }
function copyThread() {
  navigator.clipboard.writeText(result.value?.thread_id || '')
}
</script>
