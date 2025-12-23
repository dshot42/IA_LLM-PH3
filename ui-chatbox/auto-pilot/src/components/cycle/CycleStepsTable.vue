<script setup>
const props = defineProps({ steps: Array })
</script>

<template>
  <table border="1" width="100%">
    <thead>
      <tr>
        <th>Machine</th>
        <th>Step</th>
        <th>Durée (s)</th>
        <th>Level</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="s in steps" :key="s.ts">
        <td>{{ s.machine }}</td>
        <td>{{ s.step_id }}</td>
        <td>{{ s.duration }}</td>
        <td class="">{{ s.level }}</td>
      </tr>
    </tbody>
  </table>
</template>