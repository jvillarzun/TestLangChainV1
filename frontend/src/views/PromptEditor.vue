<template>
  <div class="space-y-4 animate-slide-in">
    <div class="card">
      <h1 class="text-white font-bold text-xl mb-1">✏️ Editor de Prompts</h1>
      <p class="text-slate-400 text-sm">Edita los prompts de cada agente sin tocar Python.</p>
    </div>

    <!-- Agent tabs -->
    <div class="flex gap-1 flex-wrap">
      <button
        v-for="agent in agents" :key="agent.agent"
        class="px-3 py-1.5 rounded text-xs font-semibold uppercase tracking-wider border transition-all"
        :class="selected === agent.agent
          ? 'border-amber-500 bg-amber-500/15 text-amber-400'
          : 'border-slate-700 bg-slate-900 text-slate-400 hover:border-slate-500 hover:text-white'"
        @click="selectAgent(agent.agent)"
      >
        {{ agent.label }}
      </button>
    </div>

    <!-- Editor area -->
    <div v-if="selected" class="card space-y-3">
      <div class="flex items-center justify-between">
        <div class="text-sm text-white font-semibold">
          nodes/{{ selected }}/{{ selected }}_prompt.md
        </div>
        <div class="flex items-center gap-2">
          <span v-if="dirty" class="text-xs text-amber-400">● cambios sin guardar</span>
          <span v-if="saved" class="text-xs text-emerald-400 animate-slide-in">✓ guardado</span>
          <button
            class="btn-primary text-xs py-1 px-3"
            :disabled="saving || !dirty"
            @click="save"
          >
            {{ saving ? 'Guardando...' : 'Guardar' }}
          </button>
          <button class="btn-secondary text-xs py-1 px-3" @click="reset">Reset</button>
        </div>
      </div>

      <div v-if="loadingContent" class="text-center py-8 text-slate-500 text-sm">
        Cargando prompt...
      </div>
      <div v-else>
        <textarea
          v-model="content"
          class="w-full bg-slate-950 border border-slate-700 rounded px-4 py-3 text-sm text-slate-100 font-mono focus:outline-none focus:border-amber-500/60 transition-colors resize-none leading-relaxed"
          :style="{ height: editorHeight }"
          spellcheck="false"
        />
      </div>

      <!-- Stats -->
      <div class="flex gap-4 text-xs text-slate-600">
        <span>{{ lineCount }} líneas</span>
        <span>{{ charCount }} chars</span>
        <span>{{ wordCount }} palabras</span>
      </div>

      <div v-if="saveError" class="text-red-400 text-xs">⚠ {{ saveError }}</div>
    </div>

    <div v-else class="card text-center py-16 text-slate-500 text-sm">
      Selecciona un agente para editar su prompt.
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'

const agents = ref([])
const selected = ref(null)
const content = ref('')
const originalContent = ref('')
const loadingContent = ref(false)
const saving = ref(false)
const saved = ref(false)
const saveError = ref(null)

const dirty = computed(() => content.value !== originalContent.value)
const lineCount = computed(() => content.value.split('\n').length)
const charCount = computed(() => content.value.length)
const wordCount = computed(() => content.value.trim().split(/\s+/).filter(Boolean).length)
const editorHeight = computed(() => {
  const lines = Math.max(lineCount.value + 2, 20)
  return `${Math.min(lines * 22, 600)}px`
})

onMounted(async () => {
  try {
    const res = await fetch('/api/prompts')
    if (res.ok) agents.value = await res.json()
    if (agents.value.length) selectAgent(agents.value[0].agent)
  } catch {}
})

async function selectAgent(agent) {
  if (dirty.value && selected.value && !confirm('Tienes cambios sin guardar. ¿Cambiar de agente?')) return
  selected.value = agent
  saved.value = false
  saveError.value = null
  loadingContent.value = true
  try {
    const res = await fetch(`/api/prompts/${agent}`)
    if (!res.ok) throw new Error(`Error ${res.status}`)
    const data = await res.json()
    content.value = data.content
    originalContent.value = data.content
  } catch (e) {
    saveError.value = e.message
  } finally {
    loadingContent.value = false
  }
}

async function save() {
  if (!selected.value || !dirty.value) return
  saving.value = true
  saveError.value = null
  saved.value = false
  try {
    const res = await fetch(`/api/prompts/${selected.value}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: content.value }),
    })
    if (!res.ok) throw new Error(`Error ${res.status}`)
    originalContent.value = content.value
    saved.value = true
    setTimeout(() => { saved.value = false }, 3000)
  } catch (e) {
    saveError.value = e.message
  } finally {
    saving.value = false
  }
}

function reset() {
  if (confirm('¿Descartar cambios?')) {
    content.value = originalContent.value
  }
}

// Ctrl+S to save
function handleKeydown(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault()
    save()
  }
}
document.addEventListener('keydown', handleKeydown)
</script>
