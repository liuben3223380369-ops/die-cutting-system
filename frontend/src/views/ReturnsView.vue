<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api/client'
import DataTable from '../components/DataTable.vue'
import StatusBadge from '../components/StatusBadge.vue'

interface Ret {
  id: number
  doc_no: string
  status: string
  supplier_id: number
  order_id?: number
  return_date: string
  warehouse_id: number
  reason_code?: string
  lines: Array<{ id: number; material_id: number; qty: number; batch_no: string }>
}

const rows = ref<Ret[]>([])
const suppliers = ref<Array<{ id: number; code: string; name: string }>>([])
const warehouses = ref<Array<{ id: number; code: string; name: string }>>([])
const materials = ref<Array<{ id: number; code: string; name: string }>>([])
const loading = ref(true)
const error = ref('')
const msg = ref('')
const showForm = ref(false)

const form = ref({
  supplier_id: 0,
  order_id: 0 as number | null,
  return_date: new Date().toISOString().slice(0, 10),
  warehouse_id: 0,
  reason_code: 'QC_FAIL',
  remark: '',
  material_id: 0,
  qty: 1,
  batch_no: '',
})
const orders = ref<Array<{ id: number; doc_no: string; supplier_id: number }>>([])

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [rets, sups, whs, mats, ords] = await Promise.all([
      api.get<Ret[]>('/purchase/returns'),
      api.get<Array<{ id: number; code: string; name: string }>>('/master/suppliers'),
      api.get<Array<{ id: number; code: string; name: string }>>('/master/warehouses'),
      api.get<Array<{ id: number; code: string; name: string }>>('/master/materials'),
      api.get<Array<{ id: number; doc_no: string; supplier_id: number }>>('/purchase/orders').catch(() => []),
    ])
    rows.value = rets
    suppliers.value = sups
    warehouses.value = whs
    materials.value = mats
    orders.value = ords || []
    if (sups.length) form.value.supplier_id = sups[0].id
    if (whs.length) form.value.warehouse_id = whs[0].id
    if (mats.length) form.value.material_id = mats[0].id
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function create() {
  if (form.value.qty <= 0) {
    error.value = '数量必须大于0'
    return
  }
  try {
    await api.post('/purchase/returns', {
      supplier_id: form.value.supplier_id,
      order_id: form.value.order_id || null,
      return_date: form.value.return_date,
      warehouse_id: form.value.warehouse_id,
      reason_code: form.value.reason_code || null,
      remark: form.value.remark || null,
      lines: [{
        material_id: form.value.material_id,
        qty: form.value.qty,
        batch_no: form.value.batch_no || '',
        unit: 'PCS',
      }],
    })
    showForm.value = false
    msg.value = '退货单已创建（草稿），确认后将从仓库出库'
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

async function confirm(id: number) {
  try {
    await api.post(`/purchase/returns/${id}/confirm`)
    msg.value = '退货已确认，库存已出库（PURCHASE_RETURN）'
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

function lineInfo(r: Ret) {
  return (r.lines || []).map(l => `物料${l.material_id}×${l.qty}`).join('；') || '—'
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <h2 class="page-title">采购退货</h2>
      <button class="btn primary" @click="showForm = !showForm">{{ showForm ? '取消' : '+ 新建退货' }}</button>
    </div>
    <div v-if="error" class="error-box">{{ error }}</div>
    <div v-if="msg" class="ok-box">{{ msg }}</div>

    <div v-if="showForm" class="card form-card">
      <h3>退货登记</h3>
      <p class="tip">确认后从指定仓库出库（source=PURCHASE_RETURN）。不合格品退供应商时使用。</p>
      <div class="form-grid">
        <label>供应商
          <select v-model.number="form.supplier_id">
            <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.code }} {{ s.name }}</option>
          </select>
        </label>
        <label>关联PO（可选）
          <select v-model.number="form.order_id">
            <option :value="0">不关联</option>
            <option v-for="o in orders" :key="o.id" :value="o.id">{{ o.doc_no }}</option>
          </select>
        </label>
        <label>退货日 <input type="date" v-model="form.return_date" /></label>
        <label>出库仓
          <select v-model.number="form.warehouse_id">
            <option v-for="w in warehouses" :key="w.id" :value="w.id">{{ w.code }} {{ w.name }}</option>
          </select>
        </label>
        <label>原因码
          <select v-model="form.reason_code">
            <option value="QC_FAIL">质检不合格</option>
            <option value="WRONG_ITEM">错料</option>
            <option value="DAMAGE">破损</option>
            <option value="OTHER">其他</option>
          </select>
        </label>
        <label>物料
          <select v-model.number="form.material_id">
            <option v-for="m in materials" :key="m.id" :value="m.id">{{ m.code }} {{ m.name }}</option>
          </select>
        </label>
        <label>数量 <input type="number" v-model.number="form.qty" min="0.001" step="1" /></label>
        <label>批次 <input v-model="form.batch_no" placeholder="可选" /></label>
        <label>备注 <input v-model="form.remark" /></label>
      </div>
      <button class="btn primary" @click="create">保存草稿</button>
    </div>

    <div class="card">
      <DataTable
        :columns="[
          { key: 'doc_no', label: '单号' },
          { key: 'status', label: '状态' },
          { key: 'supplier_id', label: '供应商' },
          { key: 'return_date', label: '退货日' },
          { key: 'line_info', label: '明细' },
          { key: 'actions', label: '操作' },
        ]"
        :rows="rows.map(r => ({ ...r, line_info: lineInfo(r), actions: r.id })) as any"
        :loading="loading"
      >
        <template #status="{ row }">
          <StatusBadge :status="String(row.status)" />
        </template>
        <template #actions="{ row }">
          <button v-if="row.status === 'DRAFT'" class="btn sm green" @click="confirm(Number(row.id))">确认出库</button>
          <span v-else class="muted">已处理</span>
        </template>
      </DataTable>
    </div>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.page-title { margin: 0; font-size: 1.25rem; color: #1e3a5f; }
.card { background: #fff; border-radius: 10px; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,.06); margin-bottom: 1rem; }
.form-card h3 { margin: 0 0 0.5rem; font-size: 0.95rem; color: #64748b; }
.tip { font-size: 0.8rem; color: #94a3b8; margin: 0 0 0.75rem; }
.form-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 0.75rem; margin-bottom: 1rem; }
label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.8rem; color: #64748b; }
input, select { padding: 0.45rem 0.6rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.875rem; }
.btn { padding: 0.45rem 1rem; border: none; border-radius: 6px; font-size: 0.875rem; cursor: pointer; background: #e2e8f0; margin-right: 0.35rem; }
.btn.primary { background: #1e3a5f; color: #fff; }
.btn.sm { padding: 0.25rem 0.5rem; font-size: 0.75rem; background: #dbeafe; color: #1d4ed8; }
.btn.sm.green { background: #dcfce7; color: #15803d; }
.error-box { background: #fef2f2; color: #b91c1c; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
.ok-box { background: #ecfdf5; color: #065f46; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
.muted { color: #94a3b8; font-size: 0.8rem; }
</style>
