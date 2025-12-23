<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { api } from '../services/api'
import { getSocket } from '../services/socket'
import type { MachineLive, PartListItem } from '../types'
import MachinesLive from '../components/MachinesLive.vue'
import PartsTable from '../components/PartsTable.vue'

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

let sock: any = null
onMounted(async () => {
  await Promise.all([loadParts()])

  sock = getSocket()
  sock.on('plc_event', () => {
    loadParts()
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