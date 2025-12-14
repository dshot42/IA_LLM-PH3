<script setup lang="ts">
import type { MachineLive } from '../types'
defineProps<{ machines: MachineLive[] }>()
</script>

<template>
  <div class="cards">
    <div v-for="m in machines" :key="m.machine" class="card">
      <div class="top">
        <div class="name">{{ m.machine }}</div>
        <div class="badge" :class="(m.last_level || 'NA').toLowerCase()">{{ m.last_level || '—' }}</div>
      </div>
      <div class="sub">{{ m.machine_name }}</div>

      <div class="rows">
        <div class="row"><span>Part</span><b>{{ m.last_part_id || '—' }}</b></div>
        <div class="row"><span>Step</span><b>{{ m.last_step_id || '—' }}</b></div>
        <div class="row"><span>Name</span><b>{{ m.last_step_name || '—' }}</b></div>
        <div class="row"><span>Cycle</span><b>{{ m.last_cycle ?? '—' }}</b></div>
        <div class="row"><span>Last ts</span><b>{{ m.last_ts ? new Date(m.last_ts).toLocaleString() : '—' }}</b></div>
      </div>

      <div class="foot"><span class="muted">Nominal</span><b>{{ m.nominal_duration_s }}s</b></div>
    </div>
  </div>
</template>

<style scoped>
.cards{display:grid;gap:10px;grid-template-columns:repeat(1,minmax(0,1fr))}
@media (min-width:780px){.cards{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (min-width:1120px){.cards{grid-template-columns:repeat(3,minmax(0,1fr))}}
.card{border:1px solid rgba(255,255,255,.10);background:rgba(0,0,0,.18);border-radius:16px;padding:12px}
.top{display:flex;align-items:center;justify-content:space-between}
.name{font-weight:800;letter-spacing:.5px}
.sub{font-size:12px;opacity:.75;margin-top:4px}
.badge{font-size:11px;padding:4px 8px;border-radius:999px;border:1px solid rgba(255,255,255,.14)}
.badge.ok{background:rgba(63,185,80,.18);border-color:rgba(63,185,80,.35)}
.badge.error{background:rgba(248,81,73,.18);border-color:rgba(248,81,73,.35)}
.badge.info{background:rgba(56,139,253,.16);border-color:rgba(56,139,253,.30)}
.badge.na{opacity:.6}
.rows{margin-top:10px;display:grid;gap:6px}
.row{display:flex;justify-content:space-between;gap:10px;font-size:12px;opacity:.95}
.row span{opacity:.7}
.row b{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,'Liberation Mono';font-size:12px}
.foot{margin-top:10px;display:flex;justify-content:space-between;font-size:12px;opacity:.9}
.muted{opacity:.7}
</style>
