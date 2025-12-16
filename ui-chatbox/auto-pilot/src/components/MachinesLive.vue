<script setup lang="ts">
import type { MachineLive } from '../types'
defineProps<{ machines: MachineLive[] }>()

import machineImg from "@/assets/machines/machine_3.png"
import machineInProductionImg from "@/assets/machines/machine_in_production.png"

</script>

<template>
  <div class="cards">
    <div v-for="m in machines" :key="m.machine" class="card">
      <div :class=" m.last_message == 'STEP' ? 'machineinprod':''  ">
        <div class=" machinecontent ">
          <div class="top">
            <div class="name">{{ m.machine }}</div>
            <div class="badge" :class="m.last_message == 'STEP' ? 'inprogress' : 'na' ">{{ m.last_message == 'STEP' ? 'IN PROGRESS' : 'WAITING'  }}</div>
          </div>
          <div class="sub">{{ m.machine_name }}</div>
          <div class="sub imgMachineWrap" >
            <img :class="m.last_message == 'STEP' ? 'imgMachine prod ' : 'imgMachine'" :src="m.last_message == 'STEP' ? machineInProductionImg : machineImg"></div>

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
    </div>
  </div>
</template>

<style scoped>
.cards{display:grid;gap:10px;grid-template-columns:repeat(1,minmax(0,1fr))}
@media (min-width:780px){.cards{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (min-width:1120px){.cards{grid-template-columns:repeat(3,minmax(0,1fr))}}
.card{border:1px solid rgba(255,255,255,.10);background:rgba(0,0,0,.18);border-radius:16px;padding:5px}
.top{display:flex;align-items:center;justify-content:space-between}
.name{font-weight:800;letter-spacing:.5px}
.sub{font-size:12px;opacity:.75;margin-top:4px}
.badge{font-size:11px;padding:4px 8px;border-radius:999px;border:1px solid rgba(255,255,255,.14)}
.badge.inprogress{background:rgba(63,185,80,.18);border-color:rgba(63,185,80,.35)}
.badge.error{background:rgba(248,81,73,.18);border-color:rgba(248,81,73,.35)}
.badge.info, .badge.na{background:rgba(56,139,253,.16);border-color:rgba(56,139,253,.30)}
.rows{margin-top:10px;display:grid;gap:6px}
.row{display:flex;justify-content:space-between;gap:10px;font-size:12px;opacity:.95}
.row span{opacity:.7}
.row b{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,'Liberation Mono';font-size:12px}
.foot{margin-top:10px;display:flex;justify-content:space-between;font-size:12px;opacity:.9}
.muted{opacity:.7}


.imgMachine {
  width: 150px;
  height:auto;
  text-align: center;
  margin:auto;
  display: flex;
}

.imgMachine{
  width:150px;height:auto;margin:auto;display:block;
  transition: filter .25s ease, transform .25s ease, opacity .25s ease;
  padding: 20px;
}

.imgMachineWrap{ position:relative; width:150px; margin:auto; }

.imgMachine.prod{
  animation: prodPulse 1.4s ease-in-out infinite;
}

@keyframes prodPulse{
  0%,100%{ transform: scale(1); }
  50%{ transform: scale(1.04); }
}

.machineinprod {
  margin:0px;
    padding: 2px; /* épaisseur de la bordure */
    border-radius: 10px;
     background: linear-gradient(
        90deg,
        #858585,
        #06002a,
        #080038,
        #858585
    );
    background-size: 200% 200%;
    animation: gradient-move 3s linear infinite;
  }

.machinecontent {
  background: #0b0b14;           /* couleur du fond interne */
  border-radius: 9px;            /* rayon = radius - padding */
  padding: 10px;                  /* espace interne */
}
@keyframes gradient-move { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
</style>
