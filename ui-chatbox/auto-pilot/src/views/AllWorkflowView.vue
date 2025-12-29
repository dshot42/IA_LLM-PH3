<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { api } from '../services/api'
import { getSocket } from '../services/socket'
import type { MachineLive, WorkorderListItem } from '../types'
import MachinesLive from '../components/MachinesLive.vue'
import WorkordersTable from '../components/WorkordersTable.vue'

const workorders = ref<WorkorderListItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(25)
const loading = ref(false)
const oee = ref<any>(null)

async function loadWorkorders() {
  loading.value = true
  try {
    const res = await api.get('/api/workorders', { params: { page: page.value, page_size: pageSize.value } })
    workorders.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

let sock: any = null
onMounted(async () => {
  await Promise.all([loadWorkorders()])

  sock = getSocket()
  sock.on('plc_event', () => {
    loadWorkorders()
  })
})

onBeforeUnmount(() => {
  if (sock) {
    sock.off('plc_event')
  }
})
</script>

<template>  
<div>
  <section class="panel span2">
      <div class="panelHead">
        <h2>Pièces</h2>
      </div>
      <WorkordersTable
        :items="workorders"
        :total="total"
        :page="page"
        :pageSize="pageSize"
        :loading="loading"
        @update:page="page = $event; loadWorkorders()"
        @update:pageSize="pageSize = $event; page=1; loadWorkorders()"
      />
    </section>
  </div>
</template>