<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
const rows = ref<any[]>([])
const errMsg = ref('')
async function load() { rows.value = await api('/halls') }
async function setMinDist(r: any, delta: number) {
  errMsg.value = ''
  const v = r.min_manhattan + delta
  if (v < 1) return
  try {
    await api(`/halls/${r.id}`, { method: 'PUT', body: JSON.stringify({ min_manhattan: v }) })
    await load()
  } catch (e: any) { errMsg.value = e?.message || '更新失败' }
}
onMounted(load)
</script>
<template>
  <h1>考室</h1>
  <p class="sub">考室网格与最小曼哈顿间距 · 调整最小间距后需重新排座</p>
  <span v-if="errMsg" class="hs-err">{{ errMsg }}</span>
  <div class="card">
    <table>
      <thead><tr><th>编码</th><th>名称</th><th>行</th><th>列</th><th>最小间距</th></tr></thead>
      <tbody>
        <tr v-for="r in rows" :key="r.id ?? JSON.stringify(r)">
          <td>{{ r.code }}</td><td>{{ r.name }}</td><td>{{ r.rows }}</td><td>{{ r.cols }}</td>
          <td>
            <button class="btn" style="padding:0.1rem 0.5rem" @click="setMinDist(r, -1)">−</button>
            <strong style="margin:0 0.5rem">{{ r.min_manhattan }}</strong>
            <button class="btn" style="padding:0.1rem 0.5rem" @click="setMinDist(r, 1)">＋</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
