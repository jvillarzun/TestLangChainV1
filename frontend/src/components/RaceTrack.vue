<template>
  <div class="select-none">
    <!-- Track header -->
    <div class="flex items-center justify-between mb-2 px-1">
      <div class="flex gap-3 text-xs text-slate-400">
        <span v-for="s in legend" :key="s.label" class="flex items-center gap-1">
          <span class="w-2 h-2 rounded-full inline-block" :style="{ background: s.color }"></span>
          {{ s.label }}
        </span>
      </div>
      <div v-if="challengeName" class="text-xs text-slate-400 font-semibold uppercase tracking-widest">
        {{ challengeName }}
      </div>
    </div>

    <!-- SVG Track -->
    <div class="relative overflow-hidden rounded-xl bg-slate-900 border border-slate-700 p-4">
      <svg :viewBox="`0 0 ${SVG_W} ${SVG_H}`" class="w-full" :style="`height: ${svgDisplayH}px`">
        <!-- Asphalt surface -->
        <rect :x="TRACK_X" :y="TRACK_Y" :width="TRACK_W" :height="TRACK_H" rx="6" fill="#1e293b"/>

        <!-- Track kerb top -->
        <g v-for="i in kerbCount" :key="`kt${i}`">
          <rect
            :x="TRACK_X + (i - 1) * KERB_W" :y="TRACK_Y" :width="KERB_W / 2" height="5"
            :fill="i % 2 === 0 ? '#dc2626' : '#e2e8f0'"
          />
        </g>
        <!-- Track kerb bottom -->
        <g v-for="i in kerbCount" :key="`kb${i}`">
          <rect
            :x="TRACK_X + (i - 1) * KERB_W" :y="TRACK_Y + TRACK_H - 5" :width="KERB_W / 2" height="5"
            :fill="i % 2 === 0 ? '#dc2626' : '#e2e8f0'"
          />
        </g>

        <!-- Center lane dashes -->
        <g v-for="i in dashCount" :key="`d${i}`">
          <rect
            :x="TRACK_X + (i - 1) * (DASH_W + DASH_GAP)" :y="TRACK_Y + TRACK_H / 2 - 1"
            :width="DASH_W" height="2" fill="#334155" rx="1"
          />
        </g>

        <!-- Progress fill -->
        <rect
          :x="TRACK_X" :y="TRACK_Y + 5" :width="progressFill" :height="TRACK_H - 10"
          fill="rgba(16,185,129,0.15)" rx="4"
          style="transition: width 0.9s cubic-bezier(0.4, 0, 0.2, 1)"
        />

        <!-- START label -->
        <text :x="TRACK_X - 6" :y="TRACK_Y + TRACK_H / 2 + 4"
          text-anchor="end" fill="#64748b" font-size="9" font-family="monospace" font-weight="600">
          START
        </text>
        <!-- DONE label -->
        <text :x="TRACK_X + TRACK_W + 6" :y="TRACK_Y + TRACK_H / 2 + 4"
          text-anchor="start" fill="#64748b" font-size="9" font-family="monospace" font-weight="600">
          DONE
        </text>

        <!-- Checkpoints -->
        <g v-for="(cp, i) in checkpoints" :key="cp.phase">
          <!-- Vertical sector line -->
          <line
            :x1="cp.x" :y1="TRACK_Y - 20" :x2="cp.x" :y2="TRACK_Y + TRACK_H + 20"
            :stroke="cp.color" stroke-width="1" stroke-opacity="0.4"
            :stroke-dasharray="cp.status === 'pending' ? '4,3' : 'none'"
          />
          <!-- Phase label above track -->
          <text
            :x="cp.x" :y="TRACK_Y - 24"
            text-anchor="middle" font-size="10" font-family="monospace" font-weight="700"
            :fill="cp.color" letter-spacing="1"
          >{{ cp.label }}</text>
          <!-- Marker circle on top edge -->
          <circle
            :cx="cp.x" :cy="TRACK_Y - 12" r="6"
            :fill="cp.color"
            :fill-opacity="cp.status === 'pending' ? 0.2 : 1"
            :stroke="cp.color" stroke-width="1.5"
          />
          <!-- Inner dot -->
          <circle
            v-if="cp.status !== 'pending'"
            :cx="cp.x" :cy="TRACK_Y - 12" r="2.5" fill="white" fill-opacity="0.9"
          />
          <!-- HITL flag icon -->
          <text v-if="cp.status === 'hitl'"
            :x="cp.x" :y="TRACK_Y + TRACK_H + 30"
            text-anchor="middle" font-size="13">⏸</text>
          <!-- Sector number below -->
          <text
            :x="cp.x" :y="TRACK_Y + TRACK_H + 18"
            text-anchor="middle" font-size="8" fill="#475569" font-family="monospace">
            S{{ i + 1 }}
          </text>
        </g>

        <!-- F1 Car -->
        <g :transform="`translate(${carX - 28}, ${carY})`" class="car-position">
          <!-- Shadow -->
          <ellipse cx="28" cy="22" rx="24" ry="6" fill="rgba(0,0,0,0.4)"/>
          <!-- Rear wing -->
          <rect x="1" y="5" width="5" height="14" rx="1.5" fill="#991b1b"/>
          <rect x="0" y="3" width="7" height="3" rx="1" fill="#dc2626"/>
          <rect x="0" y="18" width="7" height="3" rx="1" fill="#dc2626"/>
          <!-- Main body -->
          <path d="M6,12 Q9,4 18,4 L40,4 Q50,4 53,12 Q50,20 40,20 L18,20 Q9,20 6,12 Z" fill="#dc2626"/>
          <!-- Body highlight -->
          <path d="M18,5 L40,5 Q48,5 51,12 L40,7 L18,7 Z" fill="rgba(255,255,255,0.12)"/>
          <!-- Cockpit -->
          <ellipse cx="30" cy="12" rx="9" ry="5.5" fill="#111827"/>
          <ellipse cx="30" cy="11" rx="6" ry="3" fill="#1e3a5f"/>
          <!-- Helmet -->
          <ellipse cx="28" cy="11" rx="3.5" ry="3" fill="#f59e0b"/>
          <ellipse cx="28" cy="10.5" rx="2" ry="1.5" fill="rgba(255,255,255,0.3)"/>
          <!-- Front nose -->
          <path d="M53,10 L59,12 L53,14 Z" fill="#b91c1c"/>
          <!-- Front wing -->
          <rect x="52" y="7" width="5" height="10" rx="1" fill="#dc2626"/>
          <!-- Wheels -->
          <ellipse cx="16" cy="3.5" rx="5" ry="3.5" fill="#111"/>
          <ellipse cx="16" cy="20.5" rx="5" ry="3.5" fill="#111"/>
          <ellipse cx="42" cy="3.5" rx="5" ry="3.5" fill="#111"/>
          <ellipse cx="42" cy="20.5" rx="5" ry="3.5" fill="#111"/>
          <!-- Wheel rims -->
          <ellipse cx="16" cy="3.5" rx="2.5" ry="2" fill="#374151"/>
          <ellipse cx="16" cy="20.5" rx="2.5" ry="2" fill="#374151"/>
          <ellipse cx="42" cy="3.5" rx="2.5" ry="2" fill="#374151"/>
          <ellipse cx="42" cy="20.5" rx="2.5" ry="2" fill="#374151"/>
          <!-- Number -->
          <text x="31" y="14" text-anchor="middle" font-size="7" fill="white" font-weight="bold" font-family="monospace">26</text>
        </g>
      </svg>
    </div>

    <!-- Phase detail cards -->
    <div class="grid grid-cols-7 gap-2 mt-3">
      <div
        v-for="cp in checkpoints" :key="cp.phase"
        class="rounded-lg p-2 border text-center transition-all duration-300"
        :class="cardClass(cp.status)"
      >
        <div class="text-xs font-bold tracking-wider" :style="{ color: cp.color }">{{ cp.label }}</div>
        <div class="text-xs mt-1" :class="statusTextClass(cp.status)">{{ statusLabel(cp.status) }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  phaseStatuses: { type: Object, default: () => ({}) },
  currentPhase:  { type: String, default: 'init' },
  challengeName: { type: String, default: '' },
})

const SVG_W   = 1000
const SVG_H   = 130
const TRACK_X = 60
const TRACK_Y = 45
const TRACK_W = 880
const TRACK_H = 52
const KERB_W  = 24
const DASH_W  = 18
const DASH_GAP = 14

const kerbCount = computed(() => Math.ceil(TRACK_W / KERB_W))
const dashCount = computed(() => Math.ceil(TRACK_W / (DASH_W + DASH_GAP)))
const svgDisplayH = 160

const CHECKPOINT_PHASES = ['prd', 'ux', 'arch', 'dev', 'qa', 'infra', 'sec']
const LABELS = { prd: 'PRD', ux: 'UX', arch: 'ARQ', dev: 'DEV', qa: 'QA', infra: 'INFRA', sec: 'SEC' }

const STATUS_COLORS = {
  pending:  '#475569',
  active:   '#f59e0b',
  hitl:     '#f97316',
  approved: '#10b981',
  rejected: '#ef4444',
}

const checkpoints = computed(() =>
  CHECKPOINT_PHASES.map((phase, i) => {
    const x = TRACK_X + (TRACK_W / (CHECKPOINT_PHASES.length + 1)) * (i + 1)
    const status = props.phaseStatuses[phase] || 'pending'
    return { phase, label: LABELS[phase], x, status, color: STATUS_COLORS[status] }
  })
)

const PHASE_ORDER = ['init', 'prd', 'ux', 'arch', 'dev', 'qa', 'infra', 'sec', 'done']
const CAR_X_MAP = {
  init:  TRACK_X + 20,
  prd:   checkpoints.value[0]?.x || TRACK_X + 110,
  ux:    checkpoints.value[1]?.x || TRACK_X + 220,
  arch:  checkpoints.value[2]?.x || TRACK_X + 330,
  dev:   checkpoints.value[3]?.x || TRACK_X + 440,
  qa:    checkpoints.value[4]?.x || TRACK_X + 550,
  infra: checkpoints.value[5]?.x || TRACK_X + 660,
  sec:   checkpoints.value[6]?.x || TRACK_X + 770,
  done:  TRACK_X + TRACK_W - 20,
}

const carX = computed(() => CAR_X_MAP[props.currentPhase] ?? TRACK_X + 20)
const carY = computed(() => TRACK_Y + TRACK_H / 2 - 12)

const progressFill = computed(() => {
  const idx = PHASE_ORDER.indexOf(props.currentPhase)
  if (idx <= 0) return 0
  return (idx / (PHASE_ORDER.length - 1)) * TRACK_W
})

const legend = [
  { label: 'Pendiente', color: '#475569' },
  { label: 'En curso',  color: '#f59e0b' },
  { label: 'HITL',      color: '#f97316' },
  { label: 'Aprobado',  color: '#10b981' },
  { label: 'Rechazado', color: '#ef4444' },
]

function cardClass(status) {
  return {
    pending:  'border-slate-700 bg-slate-900/50',
    active:   'border-amber-500/50 bg-amber-500/10',
    hitl:     'border-orange-500/60 bg-orange-500/10',
    approved: 'border-emerald-500/50 bg-emerald-500/10',
    rejected: 'border-red-500/50 bg-red-500/10',
  }[status] || 'border-slate-700 bg-slate-900/50'
}

function statusTextClass(status) {
  return {
    pending:  'text-slate-600',
    active:   'text-amber-400',
    hitl:     'text-orange-400',
    approved: 'text-emerald-400',
    rejected: 'text-red-400',
  }[status] || 'text-slate-600'
}

function statusLabel(status) {
  return { pending: '—', active: 'corriendo', hitl: 'esperando', approved: '✓ ok', rejected: '✗ retry' }[status] || '—'
}
</script>
