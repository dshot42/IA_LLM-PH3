<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { api } from '../services/api'
import { getSocket } from '../services/socket'

import { onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const stepCode = computed(() => route.params.code) 


// ============================
// STATE
// ============================

const anomalies = ref<any[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(25)
const loading = ref(false)

let sock: any = null
onMounted(async () => {
  await loadAnomalies()
  sock = getSocket()
  sock.on('plc_event', loadAnomalies)
})

// ============================
// API
// ============================

function loadStep() {

}


async function loadAnomalies() {
  console.log(stepCode.value)
  if (!stepCode.value) return


  loading.value = true
  try {
    const res = await api.get(
      `/api/anomalies/steps/${stepCode.value}`,
      {
        params: {
          page: page.value,
          page_size: pageSize.value,
        }
      }
    )

    anomalies.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

// ============================
// WATCH step change
// ============================


// ============================
// PAGINATION
// ============================

const totalPages = computed(() =>
  Math.max(Math.ceil(total.value / pageSize.value), 1)
)
</script>
<template>
  <div class="bg-white rounded shadow p-4 space-y-3">

    <!-- HEADER -->
    <div class="flex justify-between items-end">
      <div>
        <h3 class="font-semibold text-lg">
          Anomalies — Step {{ stepCode }}
        </h3>

      </div>

      <div class="flex gap-2 items-center">
        <select v-model="pageSize" @change="page=1;loadAnomalies()">
          <option :value="10">10</option>
          <option :value="25">25</option>
          <option :value="50">50</option>
        </select>

        <button
          class="btn"
          :disabled="page<=1"
          @click="page--;loadAnomalies()"
        >
          Prev
        </button>

        <button
          class="btn"
          :disabled="page>=totalPages"
          @click="page++;loadAnomalies()"
        >
          Next
        </button>
      </div>
    </div>

    <!-- TABLE -->
    <div class="tableWrap">
      <table class="table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Cycle</th>
            <th>Score</th>
            <th>Sévérité</th>
            <th>Raisons</th>
            <th>Dépassement (s)</th>
          </tr>
        </thead>

        <tbody>
          <tr
            v-for="a in anomalies"
            :key="a.id"
            class="row"
          >
            <td class="mono">
              {{ new Date(a.ts).toLocaleString() }}
            </td>
            <td>{{ a.cycle }}</td>
            <td class="mono">
              {{ Number(a.anomaly_score).toFixed(2) }}
            </td>
            <td>
              <span
                class="status"
                :class="`sev-${a.severity?.toLowerCase()}`"
              >
                {{ a.severity }}
              </span>
            </td>
            <td class="text-xs">
              {{ a.rule_reasons?.join(', ') }}
            </td>
            <td class="mono">
              {{ a.duration_overrun_s?.toFixed(1) }}
            </td>
          </tr>

          <tr v-if="!anomalies.length && !loading">
            <td colspan="6" class="muted text-center">
              Aucune anomalie pour ce step
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
