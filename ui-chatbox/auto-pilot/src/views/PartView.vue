<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../services/api'
import { getSocket } from '../services/socket'
import type { PartDetail } from '../types'
import PartDetailView from '../components/PartDetailView.vue'

const route = useRoute()
const partId = computed(() => String(route.params.partId))
const data = ref<PartDetail | null>(null)
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    const res = await api.get(`/api/parts/${encodeURIComponent(partId.value)}`)
    data.value = res.data
  } finally {
    loading.value = false
  }
}

let sock: any = null
onMounted(async () => {
  await load()
  sock = getSocket()
  sock.on('plc_event', (evt: any) => {
    if (evt?.part_id === partId.value) load()
  })
})

onBeforeUnmount(() => {
  if (sock) sock.off('plc_event')
})
</script>

<template>
  <div class="panel">
    <div class="head">
      <div>
        <h2>Pièce</h2>
        <div class="id">{{ partId }}</div>
      </div>
      <a class="link" href="/">← retour</a>
    </div>

    <div v-if="loading" class="muted">Chargement…</div>
    <PartDetailView v-else-if="data" :data="data" />
    <div v-else class="muted">Aucune donnée pour cette pièce.</div>
  </div>
</template>

<style scoped>
.panel{border:1px solid rgba(255,255,255,.10);background:rgba(255,255,255,.04);border-radius:16px;padding:14px}
.head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:12px}
h2{margin:0;font-size:16px}
.id{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,'Liberation Mono';opacity:.9;margin-top:6px}
.link{color:#8fbfff;text-decoration:none;font-size:12px;opacity:.9}
.link:hover{text-decoration:underline}
.muted{opacity:.75;font-size:13px}
</style>
