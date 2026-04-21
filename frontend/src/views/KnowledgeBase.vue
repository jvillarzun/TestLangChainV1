<template>
  <div class="max-w-6xl mx-auto px-4 py-8">

    <!-- Header -->
    <div class="mb-8 flex items-end justify-between">
      <div>
        <h1 class="text-2xl font-bold text-white mb-1">🧠 Knowledge Base</h1>
        <p class="text-slate-400 text-sm">RAG por agente · prueba, compara modelos y previsualiza artefactos HTML</p>
      </div>
      <div class="text-xs text-slate-500 bg-slate-800 border border-slate-700 rounded px-3 py-1.5">
        {{ totalChunks }} chunks · {{ totalDocs }} docs
      </div>
    </div>

    <!-- Error global -->
    <Transition name="fade">
      <div v-if="globalError" class="mb-5 bg-red-900/30 border border-red-700 text-red-300 rounded px-4 py-3 text-sm flex items-center justify-between">
        <span>{{ globalError }}</span>
        <button @click="globalError=''" class="text-red-400 hover:text-red-200 ml-4">✕</button>
      </div>
    </Transition>

    <!-- Grid de agentes -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div
        v-for="agent in agents"
        :key="agent.agent"
        class="bg-slate-800 border border-slate-700 rounded-xl overflow-hidden transition-all duration-200"
        :class="activeTest === agent.agent ? 'border-violet-700/60 shadow-lg shadow-violet-900/20' : ''"
      >
        <!-- Card header -->
        <div class="flex items-center justify-between p-5 pb-3">
          <div class="flex items-center gap-3">
            <div class="text-2xl">{{ agentIcon(agent.agent) }}</div>
            <div>
              <h2 class="text-white font-semibold text-sm uppercase tracking-wider leading-none mb-1">{{ agent.agent }}</h2>
              <p class="text-slate-500 text-xs">{{ agent.chunks }} chunks · {{ agent.documents.length }} docs</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span v-if="agent.documents.length" class="bg-emerald-900/50 text-emerald-400 text-xs px-2 py-0.5 rounded-full border border-emerald-800">activo</span>
            <span v-else class="bg-slate-700 text-slate-500 text-xs px-2 py-0.5 rounded-full">sin docs</span>
            <button
              @click="toggleTest(agent.agent)"
              :class="[
                'text-xs px-3 py-1 rounded-lg border transition-all duration-150',
                activeTest === agent.agent
                  ? 'bg-violet-600 border-violet-500 text-white shadow-md shadow-violet-900/40'
                  : 'border-slate-600 text-slate-400 hover:border-violet-600 hover:text-violet-300'
              ]"
            >🧪 Probar</button>
          </div>
        </div>

        <!-- Documentos -->
        <TransitionGroup name="list" tag="div" class="px-5 space-y-1 mb-2">
          <div
            v-for="doc in agent.documents"
            :key="doc.doc_id"
            class="flex items-center justify-between bg-slate-900/60 rounded-lg px-3 py-1.5 text-xs"
          >
            <span class="text-slate-300 truncate max-w-[220px]" :title="doc.filename">📄 {{ doc.filename }}</span>
            <button
              @click="deleteDoc(agent.agent, doc.doc_id)"
              :disabled="deleting[doc.doc_id]"
              class="text-slate-500 hover:text-red-400 transition-colors ml-2 disabled:opacity-30 text-sm"
            >✕</button>
          </div>
        </TransitionGroup>

        <!-- Upload -->
        <div class="px-5 pb-4">
          <div
            class="border-2 border-dashed rounded-xl p-3 text-center cursor-pointer transition-all duration-200"
            :class="dragOver[agent.agent]
              ? 'border-violet-500 bg-violet-900/20 scale-[1.02]'
              : 'border-slate-600 hover:border-slate-500'"
            @click="triggerUpload(agent.agent)"
            @dragover.prevent="dragOver[agent.agent] = true"
            @dragleave="dragOver[agent.agent] = false"
            @drop.prevent="onDrop(agent.agent, $event)"
          >
            <input :ref="el => fileInputs[agent.agent] = el" type="file" class="hidden"
              accept=".txt,.md,.py,.kt,.swift,.java,.pdf,.ts,.js"
              @change="onFileSelected(agent.agent, $event)" />
            <Transition name="fade" mode="out-in">
              <div v-if="uploading[agent.agent]" key="loading" class="text-violet-400 text-xs animate-pulse py-0.5">⏳ Subiendo...</div>
              <div v-else-if="uploadSuccess[agent.agent]" key="ok" class="text-emerald-400 text-xs py-0.5">✅ {{ uploadSuccess[agent.agent] }}</div>
              <div v-else key="idle" class="text-slate-500 text-xs py-0.5">
                <span class="text-slate-400">↑ Subir archivo</span>
                <span class="text-slate-600"> · txt md pdf py kt swift java</span>
              </div>
            </Transition>
          </div>
        </div>

        <!-- Panel de prueba -->
        <Transition name="slide-down">
          <div v-if="activeTest === agent.agent" class="border-t border-slate-700/80 bg-slate-900/40">
            <div class="p-5 space-y-4">

              <!-- Cabecera panel -->
              <div class="flex items-center justify-between">
                <span class="text-violet-300 text-xs font-semibold uppercase tracking-wider">🧪 Sandbox — {{ agent.agent }}</span>
                <!-- Toggle A/B -->
                <button
                  @click="toggleAB(agent.agent)"
                  :class="[
                    'text-xs px-2.5 py-1 rounded border transition-colors',
                    testInputs[agent.agent]?.abMode
                      ? 'bg-amber-900/40 border-amber-600 text-amber-300'
                      : 'border-slate-600 text-slate-400 hover:border-amber-600 hover:text-amber-300'
                  ]"
                >⚖️ A/B</button>
              </div>

              <!-- Prompt -->
              <div>
                <label class="text-slate-400 text-xs mb-1.5 block">Prompt</label>
                <textarea
                  v-model="testInputs[agent.agent].prompt"
                  rows="3"
                  placeholder="Ej: Genera el onboarding de una app Android con Kotlin Compose..."
                  class="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-violet-500 resize-none transition-colors"
                />
              </div>

              <!-- Model selectors -->
              <div class="flex gap-3">
                <div class="flex-1">
                  <label class="text-slate-500 text-xs mb-1 block">Modelo {{ testInputs[agent.agent]?.abMode ? 'A' : '' }}</label>
                  <select
                    v-model="testInputs[agent.agent].modelA"
                    class="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-violet-500 transition-colors"
                  >
                    <option v-for="m in models" :key="m.id" :value="m.id">{{ m.label }}</option>
                  </select>
                </div>
                <Transition name="fade">
                  <div v-if="testInputs[agent.agent]?.abMode" class="flex-1">
                    <label class="text-slate-500 text-xs mb-1 block">Modelo B</label>
                    <select
                      v-model="testInputs[agent.agent].modelB"
                      class="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500 border-amber-700/50 transition-colors"
                    >
                      <option v-for="m in models" :key="m.id" :value="m.id">{{ m.label }}</option>
                    </select>
                  </div>
                </Transition>
              </div>

              <!-- Acciones -->
              <div class="flex gap-2">
                <button
                  @click="runQuery(agent.agent)"
                  :disabled="isLoading(agent.agent) || !testInputs[agent.agent]?.prompt"
                  class="flex-1 text-xs py-2 rounded-lg border border-slate-600 text-slate-300 hover:border-violet-500 hover:text-violet-300 transition-colors disabled:opacity-30"
                >🔍 Ver RAG</button>
                <button
                  @click="runAgent(agent.agent, 'A')"
                  :disabled="isLoading(agent.agent) || !testInputs[agent.agent]?.prompt"
                  class="flex-1 text-xs py-2 rounded-lg bg-violet-700 hover:bg-violet-600 text-white transition-colors disabled:opacity-30"
                >
                  <span v-if="testState[agent.agent]?.loadingA" class="animate-pulse">⏳</span>
                  <span v-else>▶ Ejecutar</span>
                </button>
                <button
                  v-if="testInputs[agent.agent]?.abMode"
                  @click="runAgent(agent.agent, 'B')"
                  :disabled="isLoading(agent.agent) || !testInputs[agent.agent]?.prompt"
                  class="flex-1 text-xs py-2 rounded-lg bg-amber-700 hover:bg-amber-600 text-white transition-colors disabled:opacity-30"
                >
                  <span v-if="testState[agent.agent]?.loadingB" class="animate-pulse">⏳ B</span>
                  <span v-else>▶ B</span>
                </button>
                <button
                  @click="clearOutput(agent.agent)"
                  class="text-xs px-3 py-2 rounded-lg border border-slate-700 text-slate-500 hover:text-red-400 hover:border-red-800 transition-colors"
                  title="Limpiar"
                >🗑</button>
              </div>

              <!-- RAG chunks -->
              <Transition name="fade">
                <div v-if="testState[agent.agent]?.ragChunks?.length" class="space-y-2">
                  <p class="text-slate-400 text-xs font-semibold">📚 Contexto RAG ({{ testState[agent.agent].ragChunks.length }} chunks recuperados)</p>
                  <div
                    v-for="(chunk, i) in testState[agent.agent].ragChunks"
                    :key="i"
                    class="bg-slate-800/80 border border-slate-700 rounded-lg p-3 text-xs space-y-1"
                  >
                    <div class="flex justify-between text-slate-500">
                      <span class="truncate max-w-[200px]">📄 {{ chunk.filename }} · chunk {{ chunk.chunk }}</span>
                      <span :class="chunk.score > 0.3 ? 'text-emerald-400' : chunk.score > 0 ? 'text-yellow-400' : 'text-slate-500'">
                        score {{ chunk.score }}
                      </span>
                    </div>
                    <p class="text-slate-300 line-clamp-3 whitespace-pre-wrap">{{ chunk.text }}</p>
                  </div>
                </div>
                <div v-else-if="testState[agent.agent]?.ragQueried" class="text-slate-500 text-xs bg-slate-800/50 rounded-lg p-3 border border-slate-700">
                  Sin contexto RAG para esta query — sube archivos primero.
                </div>
              </Transition>

              <!-- Outputs -->
              <div :class="testInputs[agent.agent]?.abMode && testState[agent.agent]?.outputB ? 'grid grid-cols-2 gap-3' : ''">
                <!-- Output A -->
                <Transition name="fade">
                  <AgentOutput
                    v-if="testState[agent.agent]?.outputA"
                    :output="testState[agent.agent].outputA"
                    :model="testState[agent.agent].modelA"
                    :rag-used="testState[agent.agent].ragUsed"
                    :rag-chars="testState[agent.agent].ragChars"
                    :label="testInputs[agent.agent]?.abMode ? 'A' : ''"
                    :agent="agent.agent"
                    slot-name="A"
                    @download="downloadOutput(agent.agent, 'A')"
                  />
                </Transition>
                <!-- Output B -->
                <Transition name="fade">
                  <AgentOutput
                    v-if="testState[agent.agent]?.outputB"
                    :output="testState[agent.agent].outputB"
                    :model="testState[agent.agent].modelB"
                    :rag-used="testState[agent.agent].ragUsed"
                    :rag-chars="testState[agent.agent].ragChars"
                    label="B"
                    :agent="agent.agent"
                    slot-name="B"
                    variant="amber"
                    @download="downloadOutput(agent.agent, 'B')"
                  />
                </Transition>
              </div>

              <!-- Error -->
              <Transition name="fade">
                <div v-if="testState[agent.agent]?.error" class="text-red-400 text-xs bg-red-900/20 border border-red-800 rounded-lg p-3">
                  {{ testState[agent.agent].error }}
                </div>
              </Transition>

            </div>
          </div>
        </Transition>
      </div>
    </div>

    <!-- Skeleton loader -->
    <div v-if="loading && !agents.length" class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <div v-for="i in 7" :key="i" class="bg-slate-800 border border-slate-700 rounded-xl p-5 animate-pulse">
        <div class="flex items-center gap-3 mb-4">
          <div class="w-8 h-8 bg-slate-700 rounded-full"></div>
          <div class="space-y-2">
            <div class="w-16 h-3 bg-slate-700 rounded"></div>
            <div class="w-24 h-2 bg-slate-700 rounded"></div>
          </div>
        </div>
        <div class="h-10 bg-slate-700 rounded-xl"></div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, reactive, computed, defineComponent, h } from 'vue'

// ── Sub-componente AgentOutput (inline) ───────────────────────────────────────
const AgentOutput = defineComponent({
  name: 'AgentOutput',
  props: {
    output:   String,
    model:    String,
    ragUsed:  Boolean,
    ragChars: Number,
    label:    { type: String, default: '' },
    agent:    String,
    slotName: String,
    variant:  { type: String, default: 'violet' },
  },
  emits: ['download'],
  setup(props, { emit }) {
    const activeTab = ref('preview')

    const isHtml = computed(() => {
      const o = props.output || ''
      return o.includes('<!DOCTYPE html') || o.includes('<html') || o.includes('```html')
    })

    const htmlContent = computed(() => {
      if (!isHtml.value) return ''
      const o = props.output || ''
      // Extract from code block if present
      const match = o.match(/```html\n?([\s\S]*?)```/)
      return match ? match[1] : o
    })

    const blobUrl = computed(() => {
      if (!htmlContent.value) return ''
      return URL.createObjectURL(new Blob([htmlContent.value], { type: 'text/html' }))
    })

    const artifactType = computed(() => isHtml.value ? 'html' : 'md')

    const borderColor = computed(() =>
      props.variant === 'amber' ? 'border-amber-700/40' : 'border-violet-700/30'
    )
    const labelColor = computed(() =>
      props.variant === 'amber' ? 'text-amber-400' : 'text-violet-400'
    )

    return () => {
      const label = props.label ? h('span', { class: `text-xs font-bold px-1.5 py-0.5 rounded ${props.variant === 'amber' ? 'bg-amber-900/40 text-amber-300' : 'bg-violet-900/40 text-violet-300'}` }, props.label) : null

      const meta = h('div', { class: 'flex items-center gap-2 flex-wrap' }, [
        label,
        props.ragUsed
          ? h('span', { class: 'text-emerald-400 text-xs' }, `📚 RAG (${props.ragChars}ch)`)
          : h('span', { class: 'text-slate-600 text-xs' }, 'Sin RAG'),
        h('span', { class: 'text-slate-600 text-xs' }, `· ${props.model}`),
        h('span', { class: 'text-slate-600 text-xs' }, `· ${artifactType.value.toUpperCase()}`),
      ])

      const downloadBtn = h('button', {
        onClick: () => emit('download'),
        class: 'text-xs text-slate-500 hover:text-white border border-slate-600 hover:border-slate-400 rounded px-2 py-0.5 transition-colors',
      }, '↓ Descargar')

      let content
      if (isHtml.value) {
        const tabs = h('div', { class: 'flex gap-1 mb-2' }, [
          h('button', {
            onClick: () => activeTab.value = 'preview',
            class: `text-xs px-3 py-1 rounded-t border-b-2 transition-colors ${activeTab.value === 'preview' ? 'border-violet-500 text-violet-300' : 'border-transparent text-slate-500 hover:text-slate-300'}`,
          }, '👁 Preview'),
          h('button', {
            onClick: () => activeTab.value = 'code',
            class: `text-xs px-3 py-1 rounded-t border-b-2 transition-colors ${activeTab.value === 'code' ? 'border-violet-500 text-violet-300' : 'border-transparent text-slate-500 hover:text-slate-300'}`,
          }, '📝 Código'),
        ])

        const preview = activeTab.value === 'preview'
          ? h('iframe', {
              src: blobUrl.value,
              class: 'w-full h-80 rounded-lg border border-slate-700 bg-white',
              sandbox: 'allow-scripts',
            })
          : h('pre', {
              class: 'bg-slate-900 rounded-lg p-3 text-xs text-slate-300 overflow-auto max-h-80 whitespace-pre-wrap',
            }, props.output)

        content = h('div', {}, [tabs, preview])
      } else {
        content = h('pre', {
          class: 'bg-slate-900 rounded-lg p-4 text-xs text-slate-300 overflow-auto max-h-96 whitespace-pre-wrap',
        }, props.output)
      }

      return h('div', { class: `border ${borderColor.value} rounded-xl p-4 space-y-3 bg-slate-800/30` }, [
        h('div', { class: 'flex items-center justify-between gap-2' }, [meta, downloadBtn]),
        content,
      ])
    }
  }
})

// ── Estado principal ──────────────────────────────────────────────────────────
const agents       = ref([])
const models       = ref([])
const loading      = ref(true)
const globalError  = ref('')
const fileInputs   = reactive({})
const uploading    = reactive({})
const uploadSuccess = reactive({})
const dragOver     = reactive({})
const deleting     = reactive({})
const activeTest   = ref(null)
const testInputs   = reactive({})
const testState    = reactive({})

const defaultModelId = computed(() => models.value.find(m => m.default)?.id || models.value[0]?.id || 'llama-3.3-70b-versatile')

const totalChunks = computed(() => agents.value.reduce((s, a) => s + a.chunks, 0))
const totalDocs   = computed(() => agents.value.reduce((s, a) => s + a.documents.length, 0))

const AGENT_ICONS = { prd:'📋', ux:'🎨', arch:'🏗️', dev:'💻', qa:'🧪', infra:'☁️', sec:'🔒' }
const agentIcon   = (a) => AGENT_ICONS[a] || '🤖'

function isLoading(agent) {
  return testState[agent]?.loadingA || testState[agent]?.loadingB
}

// ── Init ──────────────────────────────────────────────────────────────────────
async function fetchAll() {
  const [agentsRes, modelsRes] = await Promise.all([
    fetch('/api/rag/agents').catch(() => null),
    fetch('/api/rag/models').catch(() => null),
  ])
  if (agentsRes?.ok) {
    const d = await agentsRes.json()
    agents.value = d.agents || []
  } else {
    globalError.value = 'No se pudo conectar con la API de RAG.'
  }
  if (modelsRes?.ok) {
    const d = await modelsRes.json()
    models.value = d.models || []
  }
  loading.value = false
}

// ── Test panel ────────────────────────────────────────────────────────────────
function toggleTest(agent) {
  activeTest.value = activeTest.value === agent ? null : agent
  if (!testInputs[agent]) {
    testInputs[agent] = {
      prompt: '',
      modelA: defaultModelId.value,
      modelB: 'llama-3.1-8b-instant',
      abMode: false,
    }
  }
  if (!testState[agent]) testState[agent] = {}
}

function toggleAB(agent) {
  if (testInputs[agent]) testInputs[agent].abMode = !testInputs[agent].abMode
}

function clearOutput(agent) {
  testState[agent] = { ...testState[agent], outputA: null, outputB: null, ragChunks: [], ragQueried: false, error: null }
}

// ── Upload ────────────────────────────────────────────────────────────────────
function triggerUpload(agent) { fileInputs[agent]?.click() }

async function uploadFile(agent, file) {
  uploading[agent] = true
  delete uploadSuccess[agent]
  const form = new FormData()
  form.append('file', file)
  try {
    const res  = await fetch(`/api/rag/upload/${agent}`, { method: 'POST', body: form })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || 'Error al subir')
    uploadSuccess[agent] = `${file.name} (${data.chunks} chunks)`
    await fetchAll()
    setTimeout(() => delete uploadSuccess[agent], 4000)
  } catch (e) {
    globalError.value = `Error subiendo a ${agent}: ${e.message}`
    setTimeout(() => (globalError.value = ''), 6000)
  } finally {
    uploading[agent] = false
  }
}

function onFileSelected(agent, e) {
  const file = e.target.files?.[0]
  if (file) uploadFile(agent, file)
  e.target.value = ''
}

function onDrop(agent, e) {
  dragOver[agent] = false
  const file = e.dataTransfer.files?.[0]
  if (file) uploadFile(agent, file)
}

async function deleteDoc(agent, docId) {
  deleting[docId] = true
  try {
    await fetch(`/api/rag/docs/${agent}/${docId}`, { method: 'DELETE' })
    await fetchAll()
  } catch (e) {
    globalError.value = `Error eliminando: ${e.message}`
  } finally {
    delete deleting[docId]
  }
}

// ── RAG query ─────────────────────────────────────────────────────────────────
async function runQuery(agent) {
  const q = testInputs[agent]?.prompt
  if (!q) return
  testState[agent] = { ...testState[agent], error: null, ragQueried: false, ragChunks: [] }
  try {
    const res  = await fetch(`/api/rag/query/${agent}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: q, n_results: 3 }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail)
    testState[agent] = { ...testState[agent], ragChunks: data.chunks, ragQueried: true }
  } catch (e) {
    testState[agent] = { ...testState[agent], error: e.message }
  }
}

// ── Agent run (A o B) ─────────────────────────────────────────────────────────
async function runAgent(agent, slot = 'A') {
  const input = testInputs[agent]
  if (!input?.prompt) return

  const loadingKey = `loading${slot}`
  const outputKey  = `output${slot}`
  const modelKey   = `model${slot}`
  const model      = slot === 'A' ? input.modelA : input.modelB

  testState[agent] = { ...testState[agent], [loadingKey]: true, error: null }

  try {
    const res  = await fetch(`/api/rag/run/${agent}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt:         input.prompt,
        challenge_name: 'Test',
        challenge_type: 'greenfield',
        n_results:      3,
        model,
      }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail)
    testState[agent] = {
      ...testState[agent],
      [outputKey]:  data.output,
      [modelKey]:   data.model,
      ragUsed:      data.rag_used,
      ragChars:     data.rag_chars,
      [loadingKey]: false,
    }
  } catch (e) {
    testState[agent] = { ...testState[agent], error: e.message, [loadingKey]: false }
  }
}

// ── Download ──────────────────────────────────────────────────────────────────
function downloadOutput(agent, slot) {
  const output = testState[agent]?.[`output${slot}`]
  if (!output) return
  const isHtml = output.includes('<!DOCTYPE html') || output.includes('<html') || output.includes('```html')
  let content = output
  let ext = 'md'
  if (isHtml) {
    const match = output.match(/```html\n?([\s\S]*?)```/)
    content = match ? match[1] : output
    ext = 'html'
  }
  const blob = new Blob([content], { type: isHtml ? 'text/html' : 'text/markdown' })
  const url  = URL.createObjectURL(blob)
  const a    = document.createElement('a')
  a.href     = url
  a.download = `${agent}-output-${slot.toLowerCase()}.${ext}`
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(fetchAll)
</script>

<style scoped>
/* Slide-down para el panel de prueba */
.slide-down-enter-active {
  transition: all 0.28s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}
.slide-down-leave-active {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}
.slide-down-enter-from,
.slide-down-leave-to {
  max-height: 0;
  opacity: 0;
  transform: translateY(-4px);
}
.slide-down-enter-to,
.slide-down-leave-from {
  max-height: 2400px;
  opacity: 1;
  transform: translateY(0);
}

/* Fade general */
.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from,  .fade-leave-to      { opacity: 0; }

/* List items */
.list-enter-active { transition: all 0.25s ease; }
.list-leave-active { transition: all 0.18s ease; }
.list-enter-from   { opacity: 0; transform: translateX(-8px); }
.list-leave-to     { opacity: 0; transform: translateX(8px); }
</style>
