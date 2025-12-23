<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getAnomalyCycle } from '../services/anomaly.api'
import CycleTimeline from '../components/cycle/CycleTimeline.vue'
import CycleStepsTable from '../components/cycle/CycleStepsTable.vue'

const route = useRoute()
const cycle = ref(null)

onMounted(async () => {
  cycle.value = await getAnomalyCycle(route.params.id)
})
</script>

<template>
  <div v-if="cycle">
    <h2>Détail anomalie #{{ route.params.id }}</h2>
    <CycleTimeline :steps="cycle.steps" />
    <CycleStepsTable :steps="cycle.steps" />
  </div>
</template>