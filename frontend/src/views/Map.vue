<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
const data = ref<any>(null)
const candidates = ref<any[]>([])
const violKeys = ref<Set<string>>(new Set())
const errMsg = ref('')
async function refreshViol() {
  try {
    const v = await api('/seating/violations?hall_id=1')
    const keys = new Set<string>()
    for (const x of v.violations || []) {
      if (x.a_id != null) keys.add(String(x.a_id))
      if (x.b_id != null) keys.add(String(x.b_id))
    }
    violKeys.value = keys
  } catch { violKeys.value = new Set() }
}
async function run() {
  errMsg.value = ''
  try {
    data.value = await api('/seating/run?hall_id=1', { method: 'POST' })
    await refreshViol()
  } catch (e: any) {
    // 锁位在新约束下不合法：整场失败且不增方案
    let msg = e?.message || '排座失败'
    try {
      const d = JSON.parse(msg)?.detail
      if (d?.msg) msg = `${d.msg}（${(d.violations || []).map((v: any) => v.detail).join('；')}）`
    } catch { /* keep raw */ }
    errMsg.value = msg
  }
}
async function toggleLock(cell: any) {
  if (cell.empty) return
  errMsg.value = ''
  const cid = cell.candidate_id ?? cell.id
  try {
    data.value = await api('/seating/lock', {
      method: 'POST',
      body: JSON.stringify({ hall_id: 1, candidate_id: cid, locked: !cell.locked }),
    })
  } catch (e: any) { errMsg.value = e?.message || '锁定失败' }
}
onMounted(async () => {
  candidates.value = await api('/candidates')
  await run()
})
const gridStyle = computed(() => data.value ? ({ gridTemplateColumns: `repeat(${data.value.cols}, 72px)` }) : {})
const cells = computed(() => {
  if (!data.value) return []
  const map = new Map<string, any>()
  for (const a of data.value.assignments || []) map.set(a.row + ',' + a.col, a)
  const out: any[] = []
  for (let r = 0; r < data.value.rows; r++) {
    for (let c = 0; c < data.value.cols; c++) {
      out.push(map.get(r + ',' + c) || { empty: true, row: r, col: c })
    }
  }
  return out
})
function isViol(cell: any) {
  if (cell.empty) return false
  const id = cell.candidate_id ?? cell.id
  return id != null && violKeys.value.has(String(id))
}
function paperClass(pid: number) {
  return pid % 2 === 0 ? 'b' : 'a'
}
</script>
<template>
  <h1>考场课桌网格</h1>
  <p class="sub">课桌网格为主视图 · 左侧考生名册夹板 · 违规课桌高亮 · 点击已入座课桌锁定/解锁</p>
  <button class="btn" @click="run">重新排座</button>
  <span v-if="errMsg" class="hs-err">{{ errMsg }}</span>
  <div class="hs-classroom" style="margin-top:0.85rem">
    <aside class="hs-clipboard">
      <h2>考生名册</h2>
      <div v-for="c in candidates" :key="c.id" class="hs-roster-row">
        <div>
          <div>{{ c.name }}</div>
          <div class="hs-ticket">{{ c.ticket_no }}</div>
        </div>
        <div>卷{{ c.paper_id }}</div>
      </div>
    </aside>
    <div class="hs-desk-stage" v-if="data">
      <div class="hs-grid-board" :style="gridStyle">
        <div
          v-for="(cell,i) in cells" :key="i"
          class="hs-desk"
          :class="{ empty: cell.empty, 'hs-viol': isViol(cell), locked: !cell.empty && cell.locked }"
          @click="toggleLock(cell)"
        >
          <template v-if="!cell.empty">
            <span class="hs-paper-tag" :class="paperClass(cell.paper_id)">卷{{ cell.paper_id }}</span>
            <span v-if="cell.locked" class="hs-lock-tag">🔒</span>
            <div>{{ cell.name }}</div>
          </template>
          <template v-else>·</template>
        </div>
      </div>
    </div>
  </div>
</template>
