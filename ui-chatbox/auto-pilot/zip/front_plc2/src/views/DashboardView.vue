<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { api } from '../services/api'
import { getSocket } from '../services/socket'
import type { MachineLive, PartListItem } from '../types'
import MachinesLive from '../components/MachinesLive.vue'
import PartsTable from '../components/PartsTable.vue'

const machines = ref<MachineLive[]>([])
const parts = ref<PartListItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(25)
const loading = ref(false)
const oee = ref<any>(null)

async function loadParts() {
  loading.value = true
  try {
    const res = await api.get('/api/parts', { params: { page: page.value, page_size: pageSize.value } })
    parts.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

async function loadMachinesSnapshot() {
  const res = await api.get('/api/machines/live')
  machines.value = res.data
}

async function loadOEE() {
  const res = await api.get('/api/oee', { params: { line_nominal_s: 90 } })
  oee.value = res.data
}

let sock: any = null
onMounted(async () => {
  await Promise.all([loadParts(), loadMachinesSnapshot(), loadOEE()])

  sock = getSocket()
  sock.on('machines_live', (rows: MachineLive[]) => { machines.value = rows })
  sock.on('plc_event', () => {
    loadParts()
    loadOEE()
  })
})

onBeforeUnmount(() => {
  if (sock) {
    sock.off('machines_live')
    sock.off('plc_event')
  }
})
</script>

<template>
  <div class="grid">
    <section class="panel">
      <div class="panelHead">
        <h2>Machines – Live</h2>
        <p class="muted">Mis à jour via WebSocket (Socket.IO)</p>
      </div>
      <MachinesLive :machines="machines" />
    </section>

    <section class="panel">
      <div class="panelHead">
        <h2>OEE (estimation)</h2>
        <p class="muted">Fenêtre: dernière heure</p>
      </div>

      <div v-if="oee" class="oee">
        <div class="kpi">
          <div class="k">OEE</div>
          <div class="v">{{ oee.oee === null ? '—' : (oee.oee * 100).toFixed(1) + '%' }}</div>
        </div>
        <div class="kpi">
          <div class="k">Availability</div>
          <div class="v">{{ (oee.availability * 100).toFixed(1) + '%' }}</div>
        </div>
        <div class="kpi">
          <div class="k">Performance</div>
          <div class="v">{{ (oee.performance * 100).toFixed(1) + '%' }}</div>
        </div>
        <div class="kpi">
          <div class="k">Quality</div>
          <div class="v">{{ oee.quality === null ? '—' : (oee.quality * 100).toFixed(1) + '%' }}</div>
        </div>

        <div class="mini">
          <div>Cycles: <b>{{ oee.total_cycles }}</b></div>
          <div>Good: <b>{{ oee.good_parts }}</b></div>
          <div>Bad: <b>{{ oee.bad_parts }}</b></div>
          <div>Downtime(s): <b>{{ Number(oee.downtime_s).toFixed(1) }}</b></div>
        </div>
      </div>
    </section>

    <section class="panel span2">
      <div class="panelHead">
        <h2>Pièces</h2>
        <p class="muted">Clique une pièce pour voir son parcours complet (temps réel)</p>
      </div>
      <PartsTable
        :items="parts"
        :total="total"
        :page="page"
        :pageSize="pageSize"
        :loading="loading"
        @update:page="page = $event; loadParts()"
        @update:pageSize="pageSize = $event; page=1; loadParts()"
      />
    </section>
  </div>
</template>

<style scoped>
.grid{display:grid;gap:14px;grid-template-columns:1fr}
@media (min-width:980px){.grid{grid-template-columns:1.2fr .8fr}.span2{grid-column:1 / span 2}}
.panel{border:1px solid rgba(255,255,255,.10);background:rgba(255,255,255,.04);border-radius:16px;padding:14px}
.panelHead{display:flex;align-items:baseline;justify-content:space-between;gap:10px;margin-bottom:12px}
h2{margin:0;font-size:16px}
.muted{margin:0;font-size:12px;opacity:.7}
.oee{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.kpi{border:1px solid rgba(255,255,255,.10);background:rgba(0,0,0,.18);border-radius:14px;padding:10px}
.k{font-size:12px;opacity:.75}
.v{font-size:18px;font-weight:700;margin-top:2px}
.mini{grid-column:1 / span 2;display:flex;gap:14px;flex-wrap:wrap;font-size:12px;opacity:.9}
</style>
