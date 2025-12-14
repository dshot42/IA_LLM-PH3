<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type { PartListItem } from '../types'

const props = defineProps<{ items: PartListItem[]; total: number; page: number; pageSize: number; loading: boolean }>()
const emit = defineEmits<{ (e:'update:page', v:number):void; (e:'update:pageSize', v:number):void }>()
const router = useRouter()
const totalPages = computed(() => Math.max(Math.ceil(props.total / props.pageSize), 1))
function openPart(p: PartListItem){ router.push(`/parts/${encodeURIComponent(p.part_id)}`) }
</script>

<template>
  <div class="toolbar">
    <div class="muted">Total: <b>{{ total }}</b> • Page <b>{{ page }}</b> / <b>{{ totalPages }}</b></div>
    <div class="controls">
      <label>
        <span>Page size</span>
        <select :value="pageSize" @change="emit('update:pageSize', Number(($event.target as HTMLSelectElement).value))">
          <option :value="10">10</option><option :value="25">25</option><option :value="50">50</option><option :value="100">100</option>
        </select>
      </label>
      <button class="btn" :disabled="page<=1" @click="emit('update:page', page-1)">Prev</button>
      <button class="btn" :disabled="page>=totalPages" @click="emit('update:page', page+1)">Next</button>
    </div>
  </div>

  <div class="tableWrap">
    <table class="table">
      <thead><tr><th>Part</th><th>Status</th><th>Created</th><th>Finished</th></tr></thead>
      <tbody>
        <tr v-if="loading"><td colspan="4" class="muted">Chargement…</td></tr>
        <tr v-for="p in items" :key="p.part_id" class="row" @click="openPart(p)">
          <td class="mono">{{ p.part_id }}</td>
          <td><span class="status">{{ p.status }}</span></td>
          <td>{{ new Date(p.created_at).toLocaleString() }}</td>
          <td>{{ p.finished_at ? new Date(p.finished_at).toLocaleString() : '—' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.toolbar{display:flex;justify-content:space-between;align-items:flex-end;gap:10px;margin-bottom:10px;flex-wrap:wrap}
.muted{opacity:.75;font-size:12px}
.controls{display:flex;gap:10px;align-items:end}
label span{display:block;font-size:11px;opacity:.7;margin-bottom:6px}
select{padding:8px 10px;border-radius:12px;border:1px solid rgba(255,255,255,.14);background:rgba(0,0,0,.22);color:#e6edf3}
.btn{padding:8px 10px;border-radius:12px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.06);color:#e6edf3;cursor:pointer}
.btn:hover{background:rgba(255,255,255,.10)}
.btn:disabled{opacity:.4;cursor:not-allowed}
.tableWrap{overflow:auto;border-radius:14px;border:1px solid rgba(255,255,255,.10)}
.table{width:100%;border-collapse:collapse;background:rgba(0,0,0,.14)}
th,td{padding:10px;border-bottom:1px solid rgba(255,255,255,.08);font-size:13px;text-align:left}
th{font-size:12px;opacity:.8}
.row{cursor:pointer}
.row:hover{background:rgba(255,255,255,.05)}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,'Liberation Mono'}
.status{padding:3px 8px;border-radius:999px;border:1px solid rgba(255,255,255,.14);font-size:12px}
</style>
