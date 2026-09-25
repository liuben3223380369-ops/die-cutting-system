<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api/client'
import { useRouter } from '../router'
import StatusBadge from '../components/StatusBadge.vue'

interface Card {
  id: number
  doc_no: string
  status: string
  product_id: number
  plan_qty: string
  completed_qty: string
  progress_pct: number
  material_issue_pct: number
  current_step?: { seq: number; step_name: string; status: string }
  ops_done: number
  ops_total: number
}

const summary = ref<Record<string, number>>({})
const cards = ref<Card[]>([])
const filter = ref('')
const loading = ref(true)
const error = ref('')
const { push } = useRouter()

async function load() {
  loading.value = true
  error.value = ''
  try {
    const q = filter.value ? `?status=${filter.value}` : ''
    const data = await api.get<{ summary: any; cards: Card[] }>(`/production/board${q}`)
    summary.value = data.summary || {}
    cards.value = data.cards || []
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function openWO(id: number) {
  sessionStorage.setItem('open_wo_id', String(id))
  push('workOrders')
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <h2 class="page-title">生产看板</h2>
      <div class="filters">
        <select v-model="filter" @change="load">
          <option value="">在制（默认）</option>
          <option value="DRAFT">草稿</option>
          <option value="RELEASED">已下达</option>
          <option value="IN_PROGRESS">生产中</option>
          <option value="COMPLETED">已完工</option>
        </select>
        <button class="btn" @click="load">刷新</button>
      </div>
    </div>
    <div v-if="error" class="error-box">{{ error }}</div>

    <div class="summary">
      <div class="s-card"><span>草稿</span><b>{{ summary.draft ?? 0 }}</b></div>
      <div class="s-card"><span>已下达</span><b>{{ summary.released ?? 0 }}</b></div>
      <div class="s-card highlight"><span>生产中</span><b>{{ summary.in_progress ?? 0 }}</b></div>
      <div class="s-card"><span>已完工</span><b>{{ summary.completed ?? 0 }}</b></div>
      <div class="s-card"><span>本页卡片</span><b>{{ summary.active_cards ?? 0 }}</b></div>
    </div>

    <div v-if="loading" class="muted">加载中...</div>
    <div v-else class="board">
      <div v-for="c in cards" :key="c.id" class="wo-card clickable" @click="openWO(c.id)">
        <div class="wo-head">
          <strong>{{ c.doc_no }}</strong>
          <StatusBadge :status="c.status" />
        </div>
        <div class="wo-meta">产品 #{{ c.product_id }} · 计划 {{ c.plan_qty }} · 完工 {{ c.completed_qty }}</div>
        <div class="bar-row">
          <span>产出</span>
          <div class="bar"><i :style="{ width: c.progress_pct + '%' }"></i></div>
          <em>{{ c.progress_pct }}%</em>
        </div>
        <div class="bar-row">
          <span>领料</span>
          <div class="bar mat"><i :style="{ width: c.material_issue_pct + '%' }"></i></div>
          <em>{{ c.material_issue_pct }}%</em>
        </div>
        <div class="step" v-if="c.current_step">
          当前工序：{{ c.current_step.seq }} {{ c.current_step.step_name }}
          <StatusBadge :status="c.current_step.status" />
        </div>
        <div class="ops">工序 {{ c.ops_done }}/{{ c.ops_total }}</div>
      </div>
      <p v-if="!cards.length" class="muted">暂无工单</p>
    </div>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.5rem; }
.page-title { margin: 0; font-size: 1.25rem; color: #1e3a5f; }
.filters { display: flex; gap: 0.5rem; }
select { padding: 0.4rem 0.6rem; border: 1px solid #e2e8f0; border-radius: 6px; }
.btn { padding: 0.4rem 0.9rem; border: none; border-radius: 6px; background: #e2e8f0; cursor: pointer; }
.summary { display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 0.75rem; margin-bottom: 1rem; }
.s-card { background: #fff; border-radius: 10px; padding: 0.85rem; box-shadow: 0 1px 3px rgba(0,0,0,.06); text-align: center; }
.s-card span { display: block; font-size: 0.75rem; color: #64748b; }
.s-card b { font-size: 1.4rem; color: #1e3a5f; }
.s-card.highlight { background: #eff6ff; }
.board { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 1rem; }
.wo-card.clickable { cursor: pointer; transition: box-shadow .15s; }
.wo-card.clickable:hover { box-shadow: 0 4px 12px rgba(30,58,95,.12); }
.wo-card { background: #fff; border-radius: 10px; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,.06); border-left: 4px solid #3b82f6; }
.wo-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem; }
.wo-meta { font-size: 0.8rem; color: #64748b; margin-bottom: 0.65rem; }
.bar-row { display: grid; grid-template-columns: 36px 1fr 40px; gap: 0.35rem; align-items: center; margin-bottom: 0.35rem; font-size: 0.75rem; color: #64748b; }
.bar { height: 8px; background: #e2e8f0; border-radius: 4px; overflow: hidden; }
.bar i { display: block; height: 100%; background: linear-gradient(90deg, #3b82f6, #22c55e); }
.bar.mat i { background: linear-gradient(90deg, #f59e0b, #f97316); }
.bar-row em { font-style: normal; text-align: right; color: #1e3a5f; font-weight: 600; }
.step { font-size: 0.8rem; margin-top: 0.5rem; display: flex; gap: 0.35rem; align-items: center; flex-wrap: wrap; }
.ops { font-size: 0.75rem; color: #94a3b8; margin-top: 0.35rem; }
.error-box { background: #fef2f2; color: #b91c1c; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
.muted { color: #94a3b8; font-size: 0.875rem; }
</style>
