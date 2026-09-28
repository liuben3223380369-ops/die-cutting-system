<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api, type StockLedger } from '../api/client'
import DataTable from '../components/DataTable.vue'
import StatusBadge from '../components/StatusBadge.vue'

const rows = ref<StockLedger[]>([])
const loading = ref(true)
const error = ref('')
const msg = ref('')
const filterType = ref('')

const showReverse = ref(false)
const reverseId = ref(0)
const reverseForm = ref({
  reason_code: 'ERROR',
  remark: '',
})

const reasonOptions = [
  { value: 'ERROR', label: '录单错误' },
  { value: 'DUPLICATE', label: '重复入账' },
  { value: 'QTY_WRONG', label: '数量有误' },
  { value: 'BATCH_WRONG', label: '批次有误' },
  { value: 'OTHER', label: '其他' },
]

const columns = [
  { key: 'id', label: 'ID', width: '60px' },
  { key: 'source_type', label: '来源类型' },
  { key: 'source_id', label: '来源单号' },
  { key: 'material_id', label: '物料' },
  { key: 'warehouse_id', label: '仓库' },
  { key: 'batch_no', label: '批次' },
  { key: 'direction', label: '方向' },
  { key: 'qty', label: '数量' },
  { key: 'is_reversed', label: '状态' },
  { key: 'actions', label: '操作' },
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

function openReverse(id: number) {
  reverseId.value = id
  reverseForm.value = { reason_code: 'ERROR', remark: '' }
  showReverse.value = true
}

async function confirmReverse() {
  try {
    const q = new URLSearchParams()
    if (reverseForm.value.reason_code) q.set('reason_code', reverseForm.value.reason_code)
    if (reverseForm.value.remark) q.set('remark', reverseForm.value.remark)
    const qs = q.toString()
    await api.post(`/inventory/ledgers/${reverseId.value}/reverse${qs ? '?' + qs : ''}`, {})
    msg.value = `流水 #${reverseId.value} 已冲销（${reverseForm.value.reason_code}）`
    showReverse.value = false
    await load()
  } catch (e: any) {
    error.value = e.message
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
          <option value="ADJUST">盘点调整</option>
          <option value="REVERSAL">冲销</option>
          <option value="PRODUCTION_ISSUE">生产领料</option>
          <option value="PRODUCTION_RETURN">生产退料</option>
          <option value="PRODUCTION_IN">生产入库</option>
        </select>
        <button class="btn" @click="load">刷新</button>
      </div>
    </div>
    <div v-if="error" class="error-box">{{ error }}</div>
    <div v-if="msg" class="ok-box">{{ msg }}</div>

    <div v-if="showReverse" class="card form-card">
      <h3>冲销流水 #{{ reverseId }}</h3>
      <p class="tip">将生成反向流水并标记原单已冲销；若导致负库存会被拦截。</p>
      <div class="form-grid">
        <label>原因码
          <select v-model="reverseForm.reason_code">
            <option v-for="r in reasonOptions" :key="r.value" :value="r.value">{{ r.label }}</option>
          </select>
        </label>
        <label>备注 <input v-model="reverseForm.remark" placeholder="可选说明" /></label>
      </div>
      <button class="btn danger" @click="confirmReverse">确认冲销</button>
      <button class="btn" @click="showReverse = false">取消</button>
    </div>

    <div class="card">
      <DataTable
        :columns="columns"
        :rows="rows.map(r => ({ ...r, actions: r.id })) as any"
        :loading="loading"
      >
        <template #direction="{ row }">
          <span :class="row.direction === 'IN' ? 'in' : 'out'">{{ row.direction }}</span>
        </template>
        <template #is_reversed="{ row }">
          <StatusBadge v-if="row.is_reversed" status="FAILED" />
          <span v-else-if="row.source_type === 'REVERSAL'" class="muted">冲销单</span>
          <span v-else class="ok-text">有效</span>
        </template>
        <template #actions="{ row }">
          <button
            v-if="!row.is_reversed && row.source_type !== 'REVERSAL'"
            class="btn sm danger"
            @click="openReverse(Number(row.id))"
          >冲销</button>
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
.actions { display: flex; gap: 0.5rem; align-items: center; }
select { padding: 0.4rem 0.6rem; border: 1px solid #e2e8f0; border-radius: 6px; }
.btn { padding: 0.45rem 1rem; border: none; border-radius: 6px; background: #e2e8f0; cursor: pointer; font-size: 0.875rem; margin-right: 0.35rem; }
.btn.danger { background: #b91c1c; color: #fff; }
.btn.sm { padding: 0.25rem 0.5rem; font-size: 0.75rem; }
.btn.sm.danger { background: #fee2e2; color: #b91c1c; }
.card { background: #fff; border-radius: 10px; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,.06); margin-bottom: 1rem; }
.form-card h3 { margin: 0 0 0.5rem; font-size: 0.95rem; color: #64748b; }
.form-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 0.75rem; margin-bottom: 0.75rem; }
label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.8rem; color: #64748b; }
input { padding: 0.45rem 0.6rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.875rem; }
.in { color: #15803d; font-weight: 600; }
.out { color: #b91c1c; font-weight: 600; }
.muted { color: #94a3b8; font-size: 0.8rem; }
.ok-text { color: #15803d; font-size: 0.8rem; }
.error-box { background: #fef2f2; color: #b91c1c; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
.ok-box { background: #ecfdf5; color: #065f46; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
.tip { font-size: 0.8rem; color: #94a3b8; margin: 0.5rem 0 0.75rem; }
</style>
