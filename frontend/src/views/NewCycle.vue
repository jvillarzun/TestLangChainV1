<template>
  <div class="max-w-2xl mx-auto space-y-4 animate-slide-in">

    <!-- ── STEP 1: Formulario ───────────────────────────────────────────── -->
    <template v-if="step === 1">
      <div class="card">
        <h1 class="text-white font-bold text-xl mb-1">🚀 Nuevo Ciclo ADLC</h1>
        <p class="text-slate-400 text-sm">Configura el challenge y genera el plan antes de ejecutar.</p>
      </div>

      <form @submit.prevent="generatePlan" class="card space-y-4">
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

        <!-- Generate plan button -->
        <button
          type="submit"
          :disabled="generating"
          class="w-full py-3 rounded font-bold text-sm uppercase tracking-widest transition-colors"
          :class="generating ? 'bg-slate-700 text-slate-500 cursor-not-allowed' : 'bg-amber-600 hover:bg-amber-700 text-white'"
        >
          {{ generating ? '🧠 Generando plan...' : '🧠 Generar Plan →' }}
        </button>
      </form>

      <div v-if="error" class="card border-red-500/50 bg-red-500/5 text-red-400 text-sm">
        ⚠ {{ error }}
      </div>
    </template>

    <!-- ── STEP 2: Revisión del plan ────────────────────────────────────── -->
    <template v-if="step === 2">
      <div class="card">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-white font-bold text-xl mb-1">📋 Revisión del Plan</h1>
            <p class="text-slate-400 text-sm">
              Edita las instrucciones por fase antes de lanzar el ciclo.
            </p>
          </div>
          <button @click="step = 1" class="text-xs text-slate-400 hover:text-white border border-slate-700 hover:border-slate-500 px-3 py-1.5 rounded transition-colors">
            ← Volver
          </button>
        </div>

        <!-- Analysis summary -->
        <div v-if="analysis.domain" class="mt-4 grid grid-cols-2 gap-2 text-xs">
          <div class="bg-slate-800 rounded px-3 py-2">
            <span class="text-slate-500 uppercase tracking-wider">Dominio</span>
            <div class="text-white font-semibold mt-0.5 capitalize">{{ analysis.domain }}</div>
          </div>
          <div class="bg-slate-800 rounded px-3 py-2">
            <span class="text-slate-500 uppercase tracking-wider">Complejidad</span>
            <div class="font-semibold mt-0.5 capitalize" :class="complexityColor">{{ analysis.complexity }}</div>
          </div>
          <div v-if="analysis.key_risks?.length" class="col-span-2 bg-slate-800 rounded px-3 py-2">
            <span class="text-slate-500 uppercase tracking-wider">Riesgos clave</span>
            <div class="flex flex-wrap gap-1 mt-1">
              <span v-for="r in analysis.key_risks" :key="r" class="text-orange-300 bg-orange-500/10 border border-orange-500/20 rounded px-2 py-0.5">{{ r }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Phase cards (editable) -->
      <div class="space-y-3">
        <div
          v-for="(phase, i) in planPhases" :key="phase.phase"
          class="card border-slate-700"
        >
          <div class="flex items-center gap-2 mb-2">
            <span class="text-xs font-bold uppercase tracking-widest text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded px-2 py-0.5">
              {{ i + 1 }}. {{ phase.phase }}
            </span>
            <span class="text-xs text-slate-500">{{ phase.agent }}</span>
            <span v-if="phase.depends_on?.length" class="text-xs text-slate-600 ml-auto">
              depende de: {{ phase.depends_on.join(', ') }}
            </span>
          </div>

          <div>
            <label class="text-xs text-slate-500 uppercase tracking-wider">Instrucciones para el agente</label>
            <textarea
              v-model="phase.instructions"
              rows="3"
              class="mt-1 w-full bg-slate-800 border border-slate-700 focus:border-amber-500 rounded px-3 py-2 text-sm text-white font-mono focus:outline-none transition-colors resize-none"
            />
          </div>

          <div v-if="phase.key_outputs?.length" class="flex flex-wrap gap-1 mt-2">
            <span v-for="o in phase.key_outputs" :key="o" class="text-xs text-slate-400 bg-slate-800 border border-slate-700 rounded px-2 py-0.5">
              📄 {{ o }}
            </span>
          </div>
        </div>
      </div>

      <!-- Launch button -->
      <div class="card space-y-3">
        <div class="text-xs text-slate-500 flex items-center gap-2">
          <span class="w-2 h-2 rounded-full" :class="form.test_mode ? 'bg-amber-400' : 'bg-slate-600'"></span>
          Modo test: <strong class="text-slate-300">{{ form.test_mode ? 'activado' : 'desactivado' }}</strong>
        </div>
        <button
          :disabled="submitting"
          class="w-full py-3 rounded font-bold text-sm uppercase tracking-widest transition-colors"
          :class="submitting ? 'bg-slate-700 text-slate-500 cursor-not-allowed' : 'bg-race-red hover:bg-red-700 text-white'"
          @click="launchCycle"
        >
          {{ submitting ? '🏎️ Lanzando...' : '🏁 Confirmar y Ejecutar' }}
        </button>
      </div>

      <div v-if="error" class="card border-red-500/50 bg-red-500/5 text-red-400 text-sm">
        ⚠ {{ error }}
      </div>
    </template>

    <!-- ── STEP 3: Ciclo iniciado ───────────────────────────────────────── -->
    <template v-if="step === 3">
      <div class="card border-emerald-500/50 bg-emerald-500/5 space-y-3">
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
    </template>

  </div>
</template>

<script setup>
import { reactive, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useCycleStore } from '../stores/cycleStore.js'

const router = useRouter()
const store = useCycleStore()

const step = ref(1)
const generating = ref(false)
const submitting = ref(false)
const error = ref(null)
const result = ref(null)

const planPhases = ref([])
const analysis = ref({})

const form = reactive({
  challenge_name: '',
  challenge_type: 'greenfield',
  challenge_description: '',
  challenge_success_criteria: [''],
  test_mode: false,
})

const complexityColor = computed(() => ({
  high: 'text-red-400',
  medium: 'text-amber-400',
  low: 'text-emerald-400',
}[analysis.value.complexity] || 'text-slate-300'))

function addCriteria() { form.challenge_success_criteria.push('') }
function removeCriteria(i) { form.challenge_success_criteria.splice(i, 1) }

async function generatePlan() {
  error.value = null
  generating.value = true
  try {
    const res = await fetch('/api/plan/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        challenge_name: form.challenge_name,
        challenge_type: form.challenge_type,
        challenge_description: form.challenge_description,
        challenge_success_criteria: form.challenge_success_criteria.filter(c => c.trim()),
      }),
    })
    if (!res.ok) {
      const data = await res.json()
      throw new Error(data.detail || `Error ${res.status}`)
    }
    const data = await res.json()
    planPhases.value = data.plan_phases
    analysis.value = data.analysis || {}
    step.value = 2
  } catch (e) {
    error.value = e.message
  } finally {
    generating.value = false
  }
}

async function launchCycle() {
  error.value = null
  submitting.value = true
  try {
    const res = await fetch('/api/cycle/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...form,
        challenge_success_criteria: form.challenge_success_criteria.filter(c => c.trim()),
        plan_phases: planPhases.value,
      }),
    })
    if (!res.ok) {
      const data = await res.json()
      throw new Error(data.detail || `Error ${res.status}`)
    }
    result.value = await res.json()
    store.setThread(result.value.thread_id)
    store.startPolling()
    step.value = 3
  } catch (e) {
    error.value = e.message
  } finally {
    submitting.value = false
  }
}

function goToDashboard() { router.push('/') }
function copyThread() { navigator.clipboard.writeText(result.value?.thread_id || '') }
</script>
