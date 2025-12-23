<script setup>
import { onMounted } from 'vue'
import { Timeline } from 'vis-timeline/standalone'

const props = defineProps({ steps: Array })

onMounted(() => {
  const items = props.steps.map((s, i) => ({
    id: i,
    content: `${s.machine} / ${s.step_id}`,
    start: s.ts,
    end: new Date(new Date(s.ts).getTime() + s.duration * 1000)
  }))

  new Timeline(document.getElementById('timeline'), items)
})
</script>

<template>
  <div id="timeline" style="height:300px"></div>
</template>