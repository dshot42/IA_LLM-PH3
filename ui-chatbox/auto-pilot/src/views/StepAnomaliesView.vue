<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { api } from '../services/api'
import { getSocket } from '../services/socket'
import StepDetails from './StepDetailsView.vue'
import { useRouter } from 'vue-router'

const router = useRouter()
// ============================
// STATE
// ============================

const steps = ref<any[]>([])
const selectedStep = ref<any | null>(null)

const total = ref(0)
const page = ref(1)
const pageSize = ref(25)
const loading = ref(false)

// ============================
// API
// ============================

async function loadSteps() {
  loading.value = true
  try {
    const res = await api.get('/api/steps', {
      params: { page: page.value, page_size: pageSize.value }
    })
    steps.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

// ============================
// SOCKET
// ============================

let sock: any = null
onMounted(async () => {
  await loadSteps()
  sock = getSocket()
  sock.on('plc_event', loadSteps)
})

onBeforeUnmount(() => {
  sock?.off('plc_event')
})

// ============================
// PAGINATION
// ============================

const totalPages = computed(() =>
  Math.max(Math.ceil(total.value / pageSize.value), 1)
)

function selectStep(step: any) {
 router.push(`/stepDetails/${encodeURIComponent(step.step_code)}`) 
}

</script>

<template>

    <!-- TOOLBAR -->
    <div class="toolbar">
      <div class="muted">
        Total <b>{{ total }}</b> • Page <b>{{ page }}</b> / <b>{{ totalPages }}</b>
      </div>

      <div class="controls">
        <select v-model="pageSize" @change="page = 1; loadSteps()">
          <option :value="10">10</option>
          <option :value="25">25</option>
          <option :value="50">50</option>
        </select>

        <button class="btn" :disabled="page <= 1" @click="page--; loadSteps()">Prev</button>
        <button class="btn" :disabled="page >= totalPages" @click="page++; loadSteps()">Next</button>
      </div>
    </div>

    <!-- TABLE -->
    <div class="tableWrap">
      <table class="table">
        <thead>
          <tr>
            <th>Machine</th>
            <th>Step</th>
            <th>Nom</th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="s in steps"
            :key="s.id"
            class="row"
            @click="selectStep(s)"
          >
            <td>{{ s.machine_name }}</td>
            <td class="mono">{{ s.step_code }}</td>
            <td>{{ s.name }}</td>
          </tr>

          <tr v-if="!steps.length">
            <td colspan="3" class="muted text-center">
              Aucun step
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- DETAIL -->
    <StepDetails
      v-if="selectedStep"
      :step="selectedStep"
    />

</template>


<style scoped>
.toolbar{display:flex;justify-content:space-between;align-items:flex-end;gap:10px;margin-bottom:10px;flex-wrap:wrap}
.muted{opacity:.75;font-size:12px}
.controls{display:flex;gap:10px;align-items:end}
label span{display:block;font-size:11px;opacity:.7;margin-bottom:6px}
select{padding:8px 10px;border-radius:12px;border:1px solid rgba(255,255,255,.14);background:rgba(0,0,0,.22);color:#e6edf3}
.btn{padding:8px 10px;border-radius:12px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.06);color:#e6edf3;cursor:pointer}
.btn:hover{background:rgba(255,255,255,.10)}
.btn:disabled{opacity:.4;cursor:not-allowed}
.tableWrap{overflow:auto;border-radius:14px;border:1px solid rgba(255,255,255,.10)}
.table{width:100%;border-collapse:collapse;background:rgba(0,0,0,.14)}
th,td{padding:10px;border-bottom:1px solid rgba(255,255,255,.08);font-size:13px;text-align:left}
th{font-size:12px;opacity:.8}
.row{cursor:pointer}
.row:hover{background:rgba(255,255,255,.05)}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,'Liberation Mono'}
.status{padding:3px 8px;border-radius:999px;border:1px solid rgba(255,255,255,.14);font-size:12px}
</style>