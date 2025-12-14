<script setup lang="ts">
import type { PartDetail } from '../types'
defineProps<{ data: PartDetail }>()
</script>

<template>
  <div class="grid">
    <section class="panel">
      <h3>Machines (nominal vs réel)</h3>
      <div class="machines">
        <div v-for="m in data.machines" :key="m.machine" class="mcard">
          <div class="top">
            <div class="name">{{ m.machine }}</div>
            <div class="badge" :class="m.status.toLowerCase()">{{ m.status }}</div>
          </div>
          <div class="rows">
            <div class="row"><span>Cycle</span><b>{{ m.cycle }}</b></div>
            <div class="row"><span>Nominal</span><b>{{ m.nominal_duration_s }}s</b></div>
            <div class="row"><span>Real</span><b>{{ Number(m.real_cycle_time_s).toFixed(2) }}s</b></div>
            <div class="row"><span>Δ</span><b>{{ Number(m.delta_s).toFixed(2) }}s</b></div>
          </div>
        </div>
      </div>
    </section>

    <section class="panel">
      <h3>Steps (timeline)</h3>
      <div class="timeline">
        <div v-for="s in data.steps" :key="s.start_time + s.step_id" class="evt">
          <div class="left">
            <div class="mono">{{ s.machine }}</div>
            <div class="sub mono">{{ s.step_id }}</div>
          </div>
          <div class="mid">
            <div class="name">{{ s.step_name }}</div>
            <div class="sub">{{ new Date(s.start_time).toLocaleTimeString() }} → {{ new Date(s.end_time).toLocaleTimeString() }}</div>
          </div>
          <div class="right mono">{{ Number(s.real_duration_s).toFixed(2) }}s</div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.grid{display:grid;gap:14px;grid-template-columns:1fr}
@media (min-width:980px){.grid{grid-template-columns:1fr 1fr}}
.panel{border:1px solid rgba(255,255,255,.10);background:rgba(0,0,0,.18);border-radius:16px;padding:12px}
h3{margin:0 0 10px;font-size:14px;opacity:.9}
.machines{display:grid;gap:10px;grid-template-columns:repeat(1,minmax(0,1fr))}
@media (min-width:580px){.machines{grid-template-columns:repeat(2,minmax(0,1fr))}}
.mcard{border:1px solid rgba(255,255,255,.10);background:rgba(255,255,255,.03);border-radius:14px;padding:10px}
.top{display:flex;justify-content:space-between;align-items:center}
.name{font-weight:800;letter-spacing:.3px}
.badge{font-size:11px;padding:4px 8px;border-radius:999px;border:1px solid rgba(255,255,255,.14)}
.badge.ok{background:rgba(63,185,80,.18);border-color:rgba(63,185,80,.35)}
.badge.warning{background:rgba(210,153,34,.18);border-color:rgba(210,153,34,.35)}
.badge.drift{background:rgba(248,81,73,.18);border-color:rgba(248,81,73,.35)}
.rows{margin-top:8px;display:grid;gap:6px}
.row{display:flex;justify-content:space-between;gap:10px;font-size:12px}
.row span{opacity:.7}
.timeline{display:grid;gap:8px}
.evt{display:grid;grid-template-columns:80px 1fr 80px;gap:10px;border:1px solid rgba(255,255,255,.10);background:rgba(255,255,255,.03);border-radius:14px;padding:10px}
.left .sub,.mid .sub{font-size:11px;opacity:.7;margin-top:4px}
.mid .name{font-size:13px;font-weight:700}
.right{text-align:right;font-weight:800}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,'Liberation Mono';font-size:12px}
</style>
