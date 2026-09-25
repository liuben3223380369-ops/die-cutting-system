<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api, type StockLedger } from '../api/client'
import DataTable from '../components/DataTable.vue'
import StatusBadge from '../components/StatusBadge.vue'

const rows = ref<StockLedger[]>([])
const loading = ref(true)
const error = ref('')
const filterType = ref('')

const columns = [
  { key: 'id', label: 'ID', width: '60px' },
  { key: 'source_type', label: '来源类型' },
  { key: 'source_id', label: '来源单号' },
  { key: 'material_id', label: '物料' },
  { key: 'warehouse_id', label: '仓库' },
  { key: 'batch_no', label: '批次' },
  { key: 'direction', label: '方向' },
  { key: 'qty', label: '数量' },
  { key: 'is_reversed', label: '冲销' },
  { key: 'created_at', label: '时间' },
]

async function load() {
  loading.value = true
  error.value = ''
  try {
    const q = filterType.value ? `?source_type=${filterType.value}` : ''
    rows.value = await api.get<StockLedger[]>(`/inventory/ledgers${q}`)
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <h2 class="page-title">库存流水</h2>
      <div class="actions">
        <select v-model="filterType" @change="load">
          <option value="">全部类型</option>
          <option value="PURCHASE_IN">采购入库</option>
          <option value="PURCHASE_RETURN">采购退货</option>
          <option value="QC_HOLD">不合格隔离</option>
          <option value="TRANSFER">转移</option>
          <option value="REVERSAL">冲销</option>
          <option value="PRODUCTION_ISSUE">生产领料</option>
        </select>
        <button class="btn" @click="load">刷新</button>
      </div>
    </div>
    <div v-if="error" class="error-box">{{ error }}</div>
    <div class="card">
      <DataTable :columns="columns" :rows="rows as any" :loading="loading">
        <template #direction="{ row }">
          <span :class="row.direction === 'IN' ? 'in' : 'out'">{{ row.direction }}</span>
        </template>
        <template #is_reversed="{ row }">
          <StatusBadge v-if="row.is_reversed" status="FAILED" />
          <span v-else class="muted">—</span>
        </template>
        <template #created_at="{ row }">
          {{ String(row.created_at).slice(0, 19).replace('T', ' ') }}
        </template>
      </DataTable>
    </div>
    <p class="tip">流水只增不改不删；错误请使用冲销。这是库存唯一事实源。</p>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.5rem; }
.page-title { margin: 0; font-size: 1.25rem; color: #1e3a5f; }
.actions { display: flex; gap: 0.5rem; }
select { padding: 0.4rem 0.6rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.875rem; }
.card { background: #fff; border-radius: 10px; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,.06); }
.btn { padding: 0.45rem 1rem; border: none; border-radius: 6px; font-size: 0.875rem; cursor: pointer; background: #e2e8f0; }
.error-box { background: #fef2f2; color: #b91c1c; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
.in { color: #15803d; font-weight: 600; }
.out { color: #b91c1c; font-weight: 600; }
.muted { color: #cbd5e1; }
.tip { margin-top: 0.75rem; font-size: 0.8rem; color: #94a3b8; }
</style>
