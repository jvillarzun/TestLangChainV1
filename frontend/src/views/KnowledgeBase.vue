<template>
  <div class="max-w-5xl mx-auto px-4 py-8">
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-white mb-1">🧠 Knowledge Base</h1>
      <p class="text-slate-400 text-sm">
        Sube archivos por agente. Cada agente usa su propia colección RAG como contexto adicional al generar.
      </p>
    </div>

    <!-- Error global -->
    <div v-if="globalError" class="mb-6 bg-red-900/30 border border-red-700 text-red-300 rounded px-4 py-3 text-sm">
      {{ globalError }}
    </div>

    <!-- Grid de agentes -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div
        v-for="agent in agents"
        :key="agent.agent"
        class="bg-slate-800 border border-slate-700 rounded-lg p-5"
      >
        <!-- Header del agente -->
        <div class="flex items-center justify-between mb-4">
          <div class="flex items-center gap-2">
            <span class="text-lg">{{ agentIcon(agent.agent) }}</span>
            <div>
              <h2 class="text-white font-semibold text-sm uppercase tracking-wider">{{ agent.agent }}</h2>
              <p class="text-slate-500 text-xs">{{ agent.chunks }} chunks · {{ agent.documents.length }} archivos</p>
            </div>
          </div>
          <!-- Badge si tiene docs -->
          <span
            v-if="agent.documents.length"
            class="bg-emerald-900/50 text-emerald-400 text-xs px-2 py-0.5 rounded-full border border-emerald-800"
          >
            activo
          </span>
          <span v-else class="bg-slate-700 text-slate-500 text-xs px-2 py-0.5 rounded-full">sin docs</span>
        </div>

        <!-- Lista de documentos -->
        <div v-if="agent.documents.length" class="mb-3 space-y-1">
          <div
            v-for="doc in agent.documents"
            :key="doc.doc_id"
            class="flex items-center justify-between bg-slate-900/60 rounded px-3 py-1.5 text-xs"
          >
            <span class="text-slate-300 truncate max-w-[180px]" :title="doc.filename">📄 {{ doc.filename }}</span>
            <button
              @click="deleteDoc(agent.agent, doc.doc_id)"
              :disabled="deleting[doc.doc_id]"
              class="text-slate-500 hover:text-red-400 transition-colors ml-2 disabled:opacity-40"
              title="Eliminar"
            >
              ✕
            </button>
          </div>
        </div>

        <!-- Upload area -->
        <div
          class="border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors"
          :class="dragOver[agent.agent]
            ? 'border-blue-500 bg-blue-900/20'
            : 'border-slate-600 hover:border-slate-500'"
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

          <div v-if="uploading[agent.agent]" class="text-blue-400 text-xs">
            <span class="animate-pulse">⏳ Subiendo...</span>
          </div>
          <div v-else-if="uploadSuccess[agent.agent]" class="text-emerald-400 text-xs">
            ✅ {{ uploadSuccess[agent.agent] }}
          </div>
          <div v-else class="text-slate-500 text-xs">
            <span class="text-slate-400">↑ Subir archivo</span>
            <br />
            <span class="text-slate-600">txt · md · pdf · py · kt · swift · java</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Loading inicial -->
    <div v-if="loading && !agents.length" class="text-center text-slate-500 py-12">
      <span class="animate-pulse">Cargando knowledge base...</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'

const agents = ref([])
const loading = ref(true)
const globalError = ref('')
const fileInputs = reactive({})
const uploading = reactive({})
const uploadSuccess = reactive({})
const dragOver = reactive({})
const deleting = reactive({})

const AGENT_ICONS = {
  prd: '📋', ux: '🎨', arch: '🏗️', dev: '💻', qa: '🧪', infra: '☁️', sec: '🔒',
}
const agentIcon = (a) => AGENT_ICONS[a] || '🤖'

async function fetchAgents() {
  try {
    const res = await fetch('/api/rag/agents')
    const data = await res.json()
    agents.value = data.agents || []
  } catch (e) {
    globalError.value = 'No se pudo conectar con la API de RAG.'
  } finally {
    loading.value = false
  }
}

function triggerUpload(agent) {
  fileInputs[agent]?.click()
}

async function uploadFile(agent, file) {
  uploading[agent] = true
  delete uploadSuccess[agent]

  const form = new FormData()
  form.append('file', file)

  try {
    const res = await fetch(`/api/rag/upload/${agent}`, { method: 'POST', body: form })
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

function onFileSelected(agent, event) {
  const file = event.target.files?.[0]
  if (file) uploadFile(agent, file)
  event.target.value = ''
}

function onDrop(agent, event) {
  dragOver[agent] = false
  const file = event.dataTransfer.files?.[0]
  if (file) uploadFile(agent, file)
}

async function deleteDoc(agent, docId) {
  deleting[docId] = true
  try {
    await fetch(`/api/rag/docs/${agent}/${docId}`, { method: 'DELETE' })
    await fetchAgents()
  } catch (e) {
    globalError.value = `Error eliminando documento: ${e.message}`
    setTimeout(() => (globalError.value = ''), 5000)
  } finally {
    delete deleting[docId]
  }
}

onMounted(fetchAgents)
</script>
