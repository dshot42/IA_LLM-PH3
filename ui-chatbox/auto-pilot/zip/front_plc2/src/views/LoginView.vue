<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../services/api'
import { auth } from '../services/auth'

const router = useRouter()
const username = ref('admin')
const password = ref('admin123')
const error = ref<string | null>(null)
const loading = ref(false)

async function submit() {
  error.value = null
  loading.value = true
  try {
    const res = await api.post('/api/auth/login', { username: username.value, password: password.value })
    auth.setToken(res.data.access_token)
    router.push('/')
  } catch (e: any) {
    error.value = e?.response?.data?.error || 'Login failed'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="card">
    <h1>Connexion</h1>
    <p class="muted">Login API (démo). Token JWT stocké en localStorage.</p>

    <div class="grid">
      <label>
        <span>Username</span>
        <input v-model="username" autocomplete="username" />
      </label>
      <label>
        <span>Password</span>
        <input v-model="password" type="password" autocomplete="current-password" />
      </label>
    </div>

    <div class="row">
      <button class="btn" :disabled="loading" @click="submit">{{ loading ? '...' : 'Login' }}</button>
      <span v-if="error" class="err">{{ error }}</span>
    </div>
  </div>
</template>

<style scoped>
.card{max-width:520px;margin:40px auto;padding:18px;border-radius:16px;border:1px solid rgba(255,255,255,.10);background:rgba(255,255,255,.04)}
h1{margin:0 0 8px;font-size:20px}
.muted{opacity:.75;margin:0 0 16px;font-size:13px}
.grid{display:grid;gap:12px}
label span{display:block;font-size:12px;opacity:.8;margin-bottom:6px}
input{width:100%;padding:10px 12px;border-radius:12px;border:1px solid rgba(255,255,255,.14);background:rgba(0,0,0,.25);color:#e6edf3}
.row{margin-top:14px;display:flex;align-items:center;gap:12px}
.btn{padding:10px 12px;border-radius:12px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.06);color:#e6edf3;cursor:pointer}
.btn:hover{background:rgba(255,255,255,.10)}
.err{font-size:12px;color:#ff7b72}
</style>
