<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <div class="app-layout">
    <!-- Header -->
    <header class="app-header">
      <h1 class="title">Supervision – Ligne d’usinage</h1>

      <nav class="nav">
        <RouterLink to="/" exact-active-class="active">
          Workflow
        </RouterLink>
        <RouterLink to="/about" exact-active-class="active">
          À propos
        </RouterLink>
      </nav>
    </header>

    <!-- Main content -->
    <main class="app-content">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  min-height: 100vh;
  background: #020617;
  color: #e5e7eb;
  display: flex;
  flex-direction: column;
}

/* HEADER */
.app-header {
  background: #020617;
  border-bottom: 1px solid #1f2937;
  padding: 16px 24px;
}

.title {
  font-size: 1.4rem;
  font-weight: 600;
  margin-bottom: 8px;
  color: #e5e7eb;
}

/* NAVIGATION */
.nav {
  display: flex;
  gap: 16px;
}

.nav a {
  color: #9ca3af;
  text-decoration: none;
  font-size: 0.9rem;
  padding-bottom: 4px;
  border-bottom: 2px solid transparent;
  transition: all 0.2s ease;
}

.nav a:hover {
  color: #e5e7eb;
}

.nav a.active {
  color: #60a5fa;
  border-bottom: 2px solid #60a5fa;
}

/* CONTENT */
.app-content {
  flex: 1;
  padding: 24px;
  overflow: auto;
}
</style>
