<template>
  <nav class="bg-slate-900 border-b border-slate-700 sticky top-0 z-50">
    <div class="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
      <RouterLink to="/" class="flex items-center gap-2 text-white font-semibold tracking-wider">
        <span class="text-xl">🏁</span>
        <span class="text-race-red">MACH</span>
        <span>RACE 2026</span>
      </RouterLink>

      <div class="flex items-center gap-1">
        <RouterLink
          v-for="link in links"
          :key="link.to"
          :to="link.to"
          class="px-3 py-1.5 rounded text-sm text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          active-class="text-white bg-slate-800"
        >
          {{ link.icon }} {{ link.label }}
        </RouterLink>
      </div>

      <div class="flex items-center gap-2 text-xs text-slate-500">
        <span :class="apiOnline ? 'text-race-green' : 'text-race-red'">
          {{ apiOnline ? '● API online' : '○ API offline' }}
        </span>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const links = [
  { to: '/',        icon: '🏎️', label: 'Dashboard'   },
  { to: '/new',     icon: '🚀', label: 'Nuevo Ciclo'  },
  { to: '/prompts', icon: '✏️',  label: 'Prompts'     },
]

const apiOnline = ref(false)

onMounted(async () => {
  try {
    const res = await fetch('/api/prompts')
    apiOnline.value = res.ok
  } catch {
    apiOnline.value = false
  }
})
</script>
