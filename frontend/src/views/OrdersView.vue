<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api, type PurchaseOrder, type Material, type Supplier } from '../api/client'
import DataTable from '../components/DataTable.vue'
import StatusBadge from '../components/StatusBadge.vue'

const rows = ref<PurchaseOrder[]>([])
const materials = ref<Material[]>([])
const suppliers = ref<Supplier[]>([])
const loading = ref(true)
const error = ref('')
const showForm = ref(false)
const saving = ref(false)
const form = ref({
  supplier_id: 0,
  order_date: new Date().toISOString().slice(0, 10),
  material_id: 0,
  qty: 100,
  unit_price: 1,
})

const columns = [
  { key: 'doc_no', label: '单号' },
  { key: 'status', label: '状态' },
  { key: 'supplier_id', label: '供应商' },
  { key: 'order_date', label: '订单日' },
  { key: 'line_summary', label: '明细' },
  { key: 'actions', label: '操作' },
]

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [orders, mats, sups] = await Promise.all([
      api.get<PurchaseOrder[]>('/purchase/orders'),
      api.get<Material[]>('/master/materials'),
      api.get<Supplier[]>('/master/suppliers'),
    ])
    rows.value = orders
    materials.value = mats
    suppliers.value = sups
    if (sups.length && !form.value.supplier_id) form.value.supplier_id = sups[0].id
    if (mats.length && !form.value.material_id) form.value.material_id = mats[0].id
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function lineSummary(po: PurchaseOrder) {
  return po.lines?.map(l => `物料${l.material_id}×${l.qty}`).join(', ') || '—'
}

async function createOrder() {
  saving.value = true
  try {
    await api.post('/purchase/orders', {
      supplier_id: form.value.supplier_id,
      order_date: form.value.order_date,
      lines: [{
        material_id: form.value.material_id,
        qty: form.value.qty,
        unit_price: form.value.unit_price,
      }],
    })
    showForm.value = false
    await load()
  } catch (e: any) {
    error.value = e.message
  } finally {
    saving.value = false
  }
}

async function confirmOrder(id: number) {
  try {
    await api.post(`/purchase/orders/${id}/confirm`)
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
      <h2 class="page-title">采购订单</h2>
      <button class="btn primary" @click="showForm = !showForm">{{ showForm ? '取消' : '+ 新建订单' }}</button>
    </div>
    <div v-if="error" class="error-box">{{ error }}</div>

    <div v-if="showForm" class="card form-card">
      <div class="form-grid">
        <label>供应商
          <select v-model.number="form.supplier_id">
            <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.code }} {{ s.name }}</option>
          </select>
        </label>
        <label>订单日 <input type="date" v-model="form.order_date" /></label>
        <label>物料
          <select v-model.number="form.material_id">
            <option v-for="m in materials" :key="m.id" :value="m.id">{{ m.code }} {{ m.name }}</option>
          </select>
        </label>
        <label>数量 <input type="number" v-model.number="form.qty" min="1" /></label>
        <label>单价 <input type="number" v-model.number="form.unit_price" step="0.01" /></label>
      </div>
      <button class="btn primary" :disabled="saving" @click="createOrder">创建</button>
    </div>

    <div class="card">
      <DataTable
        :columns="columns"
        :rows="rows.map(r => ({ ...r, line_summary: lineSummary(r), actions: r.id })) as any"
        :loading="loading"
      >
        <template #status="{ row }">
          <StatusBadge :status="String(row.status)" />
        </template>
        <template #actions="{ row }">
          <button
            v-if="row.status === 'DRAFT'"
            class="btn sm"
            @click="confirmOrder(Number(row.id))"
          >确认</button>
          <span v-else class="muted">—</span>
        </template>
      </DataTable>
    </div>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.page-title { margin: 0; font-size: 1.25rem; color: #1e3a5f; }
.card { background: #fff; border-radius: 10px; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,.06); margin-bottom: 1rem; }
.form-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 0.75rem; margin-bottom: 1rem; }
label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.8rem; color: #64748b; }
input, select { padding: 0.45rem 0.6rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.875rem; }
.btn { padding: 0.45rem 1rem; border: none; border-radius: 6px; font-size: 0.875rem; cursor: pointer; background: #e2e8f0; }
.btn.primary { background: #1e3a5f; color: #fff; }
.btn.sm { padding: 0.25rem 0.6rem; font-size: 0.75rem; background: #dcfce7; color: #15803d; }
.muted { color: #cbd5e1; }
.error-box { background: #fef2f2; color: #b91c1c; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
</style>
