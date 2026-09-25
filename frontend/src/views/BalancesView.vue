<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api, type StockBalance } from '../api/client'
import DataTable from '../components/DataTable.vue'

const rows = ref<StockBalance[]>([])
const loading = ref(true)
const error = ref('')

const columns = [
  { key: 'material_id', label: '物料ID' },
  { key: 'warehouse_id', label: '仓库ID' },
  { key: 'batch_no', label: '批次' },
  { key: 'roll_no', label: '卷号' },
  { key: 'qty', label: '余额' },
  { key: 'qty_reserved', label: '预留' },
  { key: 'qty_frozen', label: '冻结' },
  { key: 'available_qty', label: '可用' },
]

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await api.get<StockBalance[]>('/inventory/balances')
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function exportXlsx() {
  window.open('/api/v1/reports/export/balances.xlsx', '_blank')
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <h2 class="page-title">库存余额</h2>
      <button class="btn" @click="exportXlsx">导出 Excel</button>
      <button class="btn" @click="load">刷新</button>
    </div>
    <div v-if="error" class="error-box">{{ error }}</div>
    <div class="card">
      <DataTable :columns="columns" :rows="rows as any" :loading="loading" empty-text="暂无库存，请先完成采购入库" />
    </div>
    <p class="tip">余额由流水汇总产生，禁止直接修改。可用量 = 余额 − 预留 − 冻结。</p>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.page-title { margin: 0; font-size: 1.25rem; color: #1e3a5f; }
.card { background: #fff; border-radius: 10px; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,.06); }
.btn { padding: 0.45rem 1rem; border: none; border-radius: 6px; font-size: 0.875rem; cursor: pointer; background: #e2e8f0; }
.error-box { background: #fef2f2; color: #b91c1c; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
.tip { margin-top: 0.75rem; font-size: 0.8rem; color: #94a3b8; }
</style>
