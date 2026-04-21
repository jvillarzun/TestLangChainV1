<template>
  <div class="max-w-5xl mx-auto px-4 py-8">
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-white mb-1">🧠 Knowledge Base</h1>
      <p class="text-slate-400 text-sm">
        Sube archivos por agente. Cada agente usa su propia colección RAG como contexto adicional al generar.
      </p>
    </div>

    <div v-if="globalError" class="mb-6 bg-red-900/30 border border-red-700 text-red-300 rounded px-4 py-3 text-sm">
      {{ globalError }}
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div
        v-for="agent in agents"
        :key="agent.agent"
        class="bg-slate-800 border border-slate-700 rounded-lg overflow-hidden"
      >
        <!-- Header -->
        <div class="flex items-center justify-between p-5 pb-4">
          <div class="flex items-center gap-2">
            <span class="text-lg">{{ agentIcon(agent.agent) }}</span>
            <div>
              <h2 class="text-white font-semibold text-sm uppercase tracking-wider">{{ agent.agent }}</h2>
              <p class="text-slate-500 text-xs">{{ agent.chunks }} chunks · {{ agent.documents.length }} archivos</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span
              v-if="agent.documents.length"
              class="bg-emerald-900/50 text-emerald-400 text-xs px-2 py-0.5 rounded-full border border-emerald-800"
            >activo</span>
            <span v-else class="bg-slate-700 text-slate-500 text-xs px-2 py-0.5 rounded-full">sin docs</span>
            <!-- Toggle test panel -->
            <button
              @click="toggleTest(agent.agent)"
              :class="[
                'text-xs px-2.5 py-1 rounded border transition-colors',
                activeTest === agent.agent
                  ? 'bg-violet-900/50 border-violet-600 text-violet-300'
                  : 'border-slate-600 text-slate-400 hover:border-slate-500 hover:text-white'
              ]"
            >
              🧪 Probar
            </button>
          </div>
        </div>

        <!-- Documentos -->
        <div v-if="agent.documents.length" class="px-5 pb-3 space-y-1">
          <div
            v-for="doc in agent.documents"
            :key="doc.doc_id"
            class="flex items-center justify-between bg-slate-900/60 rounded px-3 py-1.5 text-xs"
          >
            <span class="text-slate-300 truncate max-w-[200px]" :title="doc.filename">📄 {{ doc.filename }}</span>
            <button
              @click="deleteDoc(agent.agent, doc.doc_id)"
              :disabled="deleting[doc.doc_id]"
              class="text-slate-500 hover:text-red-400 transition-colors ml-2 disabled:opacity-40"
            >✕</button>
          </div>
        </div>

        <!-- Upload area -->
        <div class="px-5 pb-4">
          <div
            class="border-2 border-dashed rounded-lg p-3 text-center cursor-pointer transition-colors"
            :class="dragOver[agent.agent] ? 'border-blue-500 bg-blue-900/20' : 'border-slate-600 hover:border-slate-500'"
            @click="triggerUpload(agent.agent)"
            @dragover.prevent="dragOver[agent.agent] = true"
            @dragleave="dragOver[agent.agent] = false"
            @drop.prevent="onDrop(agent.agent, $event)"
          >
            <input
              :ref="el => fileInputs[agent.agent] = el"
              type="file"
              class="hidden"
              accept=".txt,.md,.py,.kt,.swift,.java,.pdf,.ts,.js"
              @change="onFileSelected(agent.agent, $event)"
            />
            <div v-if="uploading[agent.agent]" class="text-blue-400 text-xs animate-pulse">⏳ Subiendo...</div>
            <div v-else-if="uploadSuccess[agent.agent]" class="text-emerald-400 text-xs">✅ {{ uploadSuccess[agent.agent] }}</div>
            <div v-else class="text-slate-500 text-xs">
              <span class="text-slate-400">↑ Subir archivo</span>
              <span class="text-slate-600"> · txt md pdf py kt swift java</span>
            </div>
          </div>
        </div>

        <!-- Panel de prueba (colapsable) -->
        <div v-if="activeTest === agent.agent" class="border-t border-slate-700 bg-slate-900/50 p-5 space-y-4">
          <p class="text-violet-300 text-xs font-semibold uppercase tracking-wider">🧪 Modo prueba — {{ agent.agent }}</p>

          <!-- Prompt input -->
          <div>
            <label class="text-slate-400 text-xs mb-1 block">Prompt / descripción del challenge</label>
            <textarea
              v-model="testInputs[agent.agent].prompt"
              rows="3"
              placeholder="Ej: Necesito una app Android con Compose para pagos móviles..."
              class="w-full bg-slate-800 border border-slate-600 rounded px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-violet-500 resize-none"
            />
          </div>

          <!-- Botones -->
          <div class="flex gap-2">
            <button
              @click="runQuery(agent.agent)"
              :disabled="testState[agent.agent]?.loading || !testInputs[agent.agent].prompt"
              class="flex-1 text-xs py-2 rounded border border-slate-600 text-slate-300 hover:border-violet-500 hover:text-violet-300 transition-colors disabled:opacity-40"
            >
              🔍 Ver contexto RAG
            </button>
            <button
              @click="runAgent(agent.agent)"
              :disabled="testState[agent.agent]?.loading || !testInputs[agent.agent].prompt"
              class="flex-1 text-xs py-2 rounded bg-violet-700 hover:bg-violet-600 text-white transition-colors disabled:opacity-40"
            >
              {{ testState[agent.agent]?.loading ? '⏳ Ejecutando...' : '▶ Ejecutar agente' }}
            </button>
          </div>

          <!-- RAG context result -->
          <div v-if="testState[agent.agent]?.ragChunks?.length" class="space-y-2">
            <p class="text-slate-400 text-xs font-semibold">Contexto RAG recuperado ({{ testState[agent.agent].ragChunks.length }} chunks):</p>
            <div
              v-for="(chunk, i) in testState[agent.agent].ragChunks"
              :key="i"
              class="bg-slate-800 rounded p-3 text-xs space-y-1"
            >
              <div class="flex justify-between text-slate-500">
                <span>📄 {{ chunk.filename }} · chunk {{ chunk.chunk }}</span>
                <span class="text-emerald-400">score {{ chunk.score }}</span>
              </div>
              <p class="text-slate-300 whitespace-pre-wrap line-clamp-4">{{ chunk.text }}</p>
            </div>
          </div>

          <div v-else-if="testState[agent.agent]?.ragQueried && !testState[agent.agent]?.ragChunks?.length"
            class="text-slate-500 text-xs bg-slate-800 rounded p-3"
          >
            Sin contexto RAG para esta query — sube archivos primero.
          </div>

          <!-- Agent output -->
          <div v-if="testState[agent.agent]?.output" class="space-y-2">
            <div class="flex items-center justify-between">
              <p class="text-slate-400 text-xs font-semibold">Output del agente:</p>
              <div class="flex items-center gap-2 text-xs">
                <span v-if="testState[agent.agent].ragUsed" class="text-emerald-400">📚 RAG activo ({{ testState[agent.agent].ragChars }} chars)</span>
                <span v-else class="text-slate-500">Sin RAG</span>
                <span class="text-slate-600">· {{ testState[agent.agent].model }}</span>
              </div>
            </div>
            <pre class="bg-slate-800 rounded p-4 text-xs text-slate-300 whitespace-pre-wrap overflow-auto max-h-96">{{ testState[agent.agent].output }}</pre>
          </div>

          <!-- Error -->
          <div v-if="testState[agent.agent]?.error" class="text-red-400 text-xs bg-red-900/20 border border-red-800 rounded p-3">
            {{ testState[agent.agent].error }}
          </div>
        </div>
      </div>
    </div>

    <div v-if="loading && !agents.length" class="text-center text-slate-500 py-12 animate-pulse">
      Cargando knowledge base...
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'

const agents      = ref([])
const loading     = ref(true)
const globalError = ref('')
const fileInputs  = reactive({})
const uploading   = reactive({})
const uploadSuccess = reactive({})
const dragOver    = reactive({})
const deleting    = reactive({})
const activeTest  = ref(null)

// { [agent]: { prompt: '' } }
const testInputs = reactive({})
// { [agent]: { loading, output, ragChunks, ragUsed, ragChars, model, error, ragQueried } }
const testState  = reactive({})

const AGENT_ICONS = { prd:'📋', ux:'🎨', arch:'🏗️', dev:'💻', qa:'🧪', infra:'☁️', sec:'🔒' }
const agentIcon = (a) => AGENT_ICONS[a] || '🤖'

function toggleTest(agent) {
  activeTest.value = activeTest.value === agent ? null : agent
  if (!testInputs[agent]) testInputs[agent] = { prompt: '' }
  if (!testState[agent])  testState[agent]  = {}
}

async function fetchAgents() {
  try {
    const res  = await fetch('/api/rag/agents')
    const data = await res.json()
    agents.value = data.agents || []
  } catch {
    globalError.value = 'No se pudo conectar con la API de RAG.'
  } finally {
    loading.value = false
  }
}

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
    await fetchAgents()
    setTimeout(() => delete uploadSuccess[agent], 4000)
  } catch (e) {
    globalError.value = `Error subiendo a ${agent}: ${e.message}`
    setTimeout(() => (globalError.value = ''), 5000)
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
    await fetchAgents()
  } catch (e) {
    globalError.value = `Error eliminando: ${e.message}`
    setTimeout(() => (globalError.value = ''), 5000)
  } finally {
    delete deleting[docId]
  }
}

async function runQuery(agent) {
  const q = testInputs[agent]?.prompt
  if (!q) return
  testState[agent] = { ...testState[agent], loading: true, error: null, ragQueried: false }
  try {
    const res  = await fetch(`/api/rag/query/${agent}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: q, n_results: 3 }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail)
    testState[agent] = { ...testState[agent], ragChunks: data.chunks, ragQueried: true, loading: false }
  } catch (e) {
    testState[agent] = { ...testState[agent], error: e.message, loading: false }
  }
}

async function runAgent(agent) {
  const q = testInputs[agent]?.prompt
  if (!q) return
  testState[agent] = { ...testState[agent], loading: true, error: null, output: null }
  try {
    const res  = await fetch(`/api/rag/run/${agent}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt: q, challenge_name: 'Test', challenge_type: 'greenfield', n_results: 3 }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail)
    testState[agent] = {
      ...testState[agent],
      output:    data.output,
      ragUsed:   data.rag_used,
      ragChars:  data.rag_chars,
      model:     data.model,
      loading:   false,
    }
  } catch (e) {
    testState[agent] = { ...testState[agent], error: e.message, loading: false }
  }
}

onMounted(fetchAgents)
</script>
