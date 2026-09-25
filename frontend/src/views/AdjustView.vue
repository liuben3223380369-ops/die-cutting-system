<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api/client'
import DataTable from '../components/DataTable.vue'
import StatusBadge from '../components/StatusBadge.vue'

const materials = ref<Array<{ id: number; code: string; name: string }>>([])
const warehouses = ref<Array<{ id: number; code: string; name: string }>>([])
const balances = ref<any[]>([])
const error = ref('')
const msg = ref('')
const loading = ref(true)
const tab = ref<'adjust' | 'transfer'>('adjust')

const adj = ref({
  material_id: 0,
  warehouse_id: 0,
  qty_delta: 0,
  batch_no: '',
  reason_code: 'COUNT',
  remark: '',
})

const tr = ref({
  material_id: 0,
  from_warehouse_id: 0,
  to_warehouse_id: 0,
  qty: 1,
  batch_no: '',
  remark: '',
  source_id: '',
})

async function load() {
  loading.value = true
  try {
    const [mats, whs, bals] = await Promise.all([
      api.get<any[]>('/master/materials'),
      api.get<any[]>('/master/warehouses'),
      api.get<any[]>('/inventory/balances'),
    ])
    materials.value = mats
    warehouses.value = whs
    balances.value = bals
    if (mats.length) {
      adj.value.material_id = mats[0].id
      tr.value.material_id = mats[0].id
    }
    if (whs.length) {
      adj.value.warehouse_id = whs[0].id
      tr.value.from_warehouse_id = whs[0].id
      tr.value.to_warehouse_id = whs[whs.length > 1 ? 1 : 0].id
    }
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function doAdjust() {
  if (adj.value.qty_delta === 0) {
    error.value = '调整数量不能为0（正数盘盈，负数盘亏）'
    return
  }
  try {
    const ledger = await api.post<any>('/inventory/adjust', adj.value)
    msg.value = `调整成功：流水 #${ledger.id}，数量 ${adj.value.qty_delta > 0 ? '+' : ''}${adj.value.qty_delta}`
    error.value = ''
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

async function doTransfer() {
  if (tr.value.from_warehouse_id === tr.value.to_warehouse_id) {
    error.value = '调出仓与调入仓不能相同'
    return
  }
  if (tr.value.qty <= 0) {
    error.value = '转移数量必须大于0'
    return
  }
  try {
    const source_id = tr.value.source_id || `TR${Date.now()}`
    await api.post('/inventory/transfer', {
      source_id,
      material_id: tr.value.material_id,
      from_warehouse_id: tr.value.from_warehouse_id,
      to_warehouse_id: tr.value.to_warehouse_id,
      qty: tr.value.qty,
      batch_no: tr.value.batch_no || '',
      remark: tr.value.remark || '仓库调拨',
    })
    msg.value = `调拨成功 ${tr.value.qty} → 目标仓`
    error.value = ''
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
      <h2 class="page-title">盘点调整 / 调拨</h2>
      <div class="tabs">
        <button class="tab" :class="{ active: tab === 'adjust' }" @click="tab = 'adjust'">盘点调整</button>
        <button class="tab" :class="{ active: tab === 'transfer' }" @click="tab = 'transfer'">仓库调拨</button>
      </div>
    </div>
    <div v-if="error" class="error-box">{{ error }}</div>
    <div v-if="msg" class="ok-box">{{ msg }}</div>

    <div v-if="tab === 'adjust'" class="card">
      <h3>盘点调整</h3>
      <p class="tip">数量填<strong>正数</strong>为盘盈入库，<strong>负数</strong>为盘亏出库（不可导致负库存）。</p>
      <div class="form-grid">
        <label>物料
          <select v-model.number="adj.material_id">
            <option v-for="m in materials" :key="m.id" :value="m.id">{{ m.code }} {{ m.name }}</option>
          </select>
        </label>
        <label>仓库
          <select v-model.number="adj.warehouse_id">
            <option v-for="w in warehouses" :key="w.id" :value="w.id">{{ w.code }} {{ w.name }}</option>
          </select>
        </label>
        <label>调整数量 <input type="number" v-model.number="adj.qty_delta" step="1" /></label>
        <label>批次 <input v-model="adj.batch_no" /></label>
        <label>原因
          <select v-model="adj.reason_code">
            <option value="COUNT">盘点</option>
            <option value="DAMAGE">损耗</option>
            <option value="FOUND">找到</option>
            <option value="OTHER">其他</option>
          </select>
        </label>
        <label>备注 <input v-model="adj.remark" /></label>
      </div>
      <button class="btn primary" @click="doAdjust">提交调整</button>
    </div>

    <div v-if="tab === 'transfer'" class="card">
      <h3>仓库调拨</h3>
      <div class="form-grid">
        <label>物料
          <select v-model.number="tr.material_id">
            <option v-for="m in materials" :key="m.id" :value="m.id">{{ m.code }} {{ m.name }}</option>
          </select>
        </label>
        <label>调出仓
          <select v-model.number="tr.from_warehouse_id">
            <option v-for="w in warehouses" :key="w.id" :value="w.id">{{ w.code }}</option>
          </select>
        </label>
        <label>调入仓
          <select v-model.number="tr.to_warehouse_id">
            <option v-for="w in warehouses" :key="w.id" :value="w.id">{{ w.code }}</option>
          </select>
        </label>
        <label>数量 <input type="number" v-model.number="tr.qty" min="0.001" step="1" /></label>
        <label>批次 <input v-model="tr.batch_no" /></label>
        <label>备注 <input v-model="tr.remark" /></label>
      </div>
      <button class="btn primary" @click="doTransfer">提交调拨</button>
    </div>

    <div class="card">
      <h3>当前库存余额</h3>
      <DataTable
        :columns="[
          { key: 'material_id', label: '物料' },
          { key: 'warehouse_id', label: '仓库' },
          { key: 'batch_no', label: '批次' },
          { key: 'qty', label: '数量' },
          { key: 'available_qty', label: '可用' },
        ]"
        :rows="balances as any"
        :loading="loading"
      />
    </div>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.5rem; }
.page-title { margin: 0; font-size: 1.25rem; color: #1e3a5f; }
.tabs { display: flex; gap: 0.35rem; }
.tab { padding: 0.4rem 0.9rem; border: 1px solid #e2e8f0; border-radius: 6px; background: #f8fafc; cursor: pointer; font-size: 0.85rem; }
.tab.active { background: #1e3a5f; color: #fff; border-color: #1e3a5f; }
.card { background: #fff; border-radius: 10px; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,.06); margin-bottom: 1rem; }
.card h3 { margin: 0 0 0.5rem; font-size: 0.95rem; color: #64748b; }
.tip { font-size: 0.8rem; color: #94a3b8; margin: 0 0 0.75rem; }
.form-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 0.75rem; margin-bottom: 1rem; }
label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.8rem; color: #64748b; }
input, select { padding: 0.45rem 0.6rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.875rem; }
.btn { padding: 0.45rem 1rem; border: none; border-radius: 6px; font-size: 0.875rem; cursor: pointer; background: #e2e8f0; }
.btn.primary { background: #1e3a5f; color: #fff; }
.error-box { background: #fef2f2; color: #b91c1c; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
.ok-box { background: #ecfdf5; color: #065f46; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
</style>
