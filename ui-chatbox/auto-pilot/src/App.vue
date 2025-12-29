<script setup lang="ts">
import { RouterView, useRouter } from 'vue-router'
import { auth } from './services/auth'
import Navbar from "@/components/Navbar.vue"
const router = useRouter()

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
<div class="shell">
  <!-- TOP BAR -->
  <header class="topbar">
    <div class="">
      <div>
          <!-- NAVBAR -->
          <Navbar v-if="auth.isAuthenticated()" />
      </div>
    </div>

    <div class="actions">
      <span v-if="auth.isAuthenticated()" class="pill">Connected</span>
      <button v-if="auth.isAuthenticated()" class="btn" @click="logout">
        Logout
      </button>
    </div>
  </header>

  <!-- MAIN CONTENT -->
  <main class="content">
    <RouterView />
  </main>
</div>

</template>

<style scoped>
.shell{width: 100vw;min-height:100vh;background:#303848;color:#e6edf3;font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial}
.topbar{position:sticky;top:0;z-index:10;display:flex;align-items:center;justify-content:space-between;padding:14px 18px;background:rgba(11,15,23,.85);backdrop-filter:blur(10px);border-bottom:1px solid rgba(255,255,255,.08)}
.brand{display:flex;gap:10px;align-items:center}
.dot{width:12px;height:12px;border-radius:999px;background:#3fb950;box-shadow:0 0 0 6px rgba(63,185,80,.12)}
.title{font-weight:700;letter-spacing:.4px}
.subtitle{font-size:12px;opacity:.7;margin-top:-2px}
.actions{display:flex;gap:10px;align-items:center}
.pill{font-size:12px;padding:4px 10px;border:1px solid rgba(255,255,255,.14);border-radius:999px;opacity:.9}
.btn{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);color:#e6edf3;padding:8px 10px;border-radius:10px;cursor:pointer}
.btn:hover{background:rgba(255,255,255,.10)}
.content{padding:18px;max-width:90vw;margin:0 auto}

</style>
