
<script setup>
const workflow = {
  lineName: "Ligne 5 machines – Usinage complet",
  cycleTime: 90,
  machines: [
    { id: "M1", name: "Chargement & Préparation", duration: 8, image: "/src/assets/machines/m1.svg", description: "Convoyeur, alignement, serrage" },
    { id: "M2", name: "Usinage Ébauche", duration: 28, image: "/src/assets/machines/m2.svg", description: "Passes rough, contrôle broche" },
    { id: "M3", name: "Usinage Finition", duration: 18, image: "/src/assets/machines/m3.svg", description: "Finition, état de surface" },
    { id: "M4", name: "Perçage & Taraudage", duration: 18, image: "/src/assets/machines/m4.svg", description: "Perçage, taraudage" },
    { id: "M5", name: "Contrôle & Déchargement", duration: 12, image: "/src/assets/machines/m5.svg", description: "Vision, mesure, déchargement" }
  ]
}
</script>

<template>
  <div class="workflow-container">
    <h1>{{ workflow.lineName }}</h1>
    <p class="cycle">Cycle nominal : <strong>{{ workflow.cycleTime }} s</strong></p>
    <div class="workflow">
      <div v-for="m in workflow.machines" :key="m.id" class="machine-card">
        <img :src="m.image" :alt="m.id" />
        <h2>{{ m.id }}</h2>
        <h3>{{ m.name }}</h3>
        <p class="desc">{{ m.description }}</p>
        <div class="duration">⏱ {{ m.duration }} s</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.workflow-container { padding: 24px; color: #e5e7eb; }
.workflow { display: flex; gap: 20px; overflow-x: auto; }
.machine-card { min-width: 240px; background: #111827; border-radius: 14px; padding: 16px; text-align: center; }
.machine-card img { width: 100%; height: 140px; object-fit: cover; border-radius: 10px; }
h2 { color: #60a5fa; }
.desc { color: #9ca3af; font-size: 0.85rem; }
.duration { color: #34d399; font-weight: bold; }
</style>
