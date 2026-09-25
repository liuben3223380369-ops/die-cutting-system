<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { api } from '../api/client'
import DataTable from '../components/DataTable.vue'
import StatusBadge from '../components/StatusBadge.vue'

interface POLine {
  id?: number
  material_id: number
  qty: number
  qty_received?: number
  unit_price?: number
  unit?: string
}
interface PO {
  id: number
  doc_no: string
  status: string
  supplier_id: number
  order_date: string
  request_id?: number
  lines: POLine[]
}
interface PR {
  id: number
  doc_no: string
  status: string
  request_date: string
  lines: Array<{ material_id: number; qty: number; unit?: string }>
}

const orders = ref<PO[]>([])
const requests = ref<PR[]>([])
const suppliers = ref<Array<{ id: number; code: string; name: string }>>([])
const materials = ref<Array<{ id: number; code: string; name: string }>>([])
const loading = ref(true)
const error = ref('')
const msg = ref('')
const statusFilter = ref('')
const tab = ref<'orders' | 'requests'>('orders')

const showPO = ref(false)
const showPR = ref(false)
const poForm = ref({
  supplier_id: 0,
  order_date: new Date().toISOString().slice(0, 10),
  remark: '',
  lines: [{ material_id: 0, qty: 1, unit_price: 0, unit: 'PCS' }] as POLine[],
})
const prForm = ref({
  request_date: new Date().toISOString().slice(0, 10),
  requester: '',
  remark: '',
  material_id: 0,
  qty: 1,
})
const convertForm = ref({ request_id: 0, supplier_id: 0, auto_confirm: false })

const filteredOrders = computed(() =>
  statusFilter.value
    ? orders.value.filter(o => o.status === statusFilter.value)
    : orders.value
)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [pos, prs, sups, mats] = await Promise.all([
      api.get<PO[]>('/purchase/orders'),
      api.get<PR[]>('/purchase/requests').catch(() => []),
      api.get<Array<{ id: number; code: string; name: string }>>('/master/suppliers'),
      api.get<Array<{ id: number; code: string; name: string }>>('/master/materials'),
    ])
    orders.value = pos
    requests.value = prs || []
    suppliers.value = sups
    materials.value = mats
    if (sups.length) {
      poForm.value.supplier_id = sups[0].id
      convertForm.value.supplier_id = sups[0].id
    }
    if (mats.length) {
      poForm.value.lines[0].material_id = mats[0].id
      prForm.value.material_id = mats[0].id
    }
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function addPOLine() {
  const mid = materials.value[0]?.id || 0
  poForm.value.lines.push({ material_id: mid, qty: 1, unit_price: 0, unit: 'PCS' })
}
function removePOLine(i: number) {
  if (poForm.value.lines.length > 1) poForm.value.lines.splice(i, 1)
}

async function createPO() {
  try {
    await api.post('/purchase/orders', {
      supplier_id: poForm.value.supplier_id,
      order_date: poForm.value.order_date,
      remark: poForm.value.remark || null,
      lines: poForm.value.lines.map(l => ({
        material_id: l.material_id,
        qty: l.qty,
        unit: l.unit || 'PCS',
        unit_price: l.unit_price || null,
      })),
    })
    showPO.value = false
    msg.value = '采购订单已创建（草稿）'
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

async function confirmPO(id: number) {
  try {
    await api.post(`/purchase/orders/${id}/confirm`)
    msg.value = '订单已确认'
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

async function createPR() {
  try {
    await api.post('/purchase/requests', {
      request_date: prForm.value.request_date,
      requester: prForm.value.requester || null,
      remark: prForm.value.remark || null,
      lines: [{
        material_id: prForm.value.material_id,
        qty: prForm.value.qty,
        unit: 'PCS',
      }],
    })
    showPR.value = false
    msg.value = '采购申请已创建'
    tab.value = 'requests'
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

async function submitPR(id: number) {
  try {
    await api.post(`/purchase/requests/${id}/submit`)
    msg.value = '申请已提交'
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

async function convertPR(pr: PR) {
  convertForm.value.request_id = pr.id
  try {
    const po = await api.post<any>('/purchase/orders/from-request', {
      request_id: pr.id,
      supplier_id: convertForm.value.supplier_id,
      auto_confirm: convertForm.value.auto_confirm,
    })
    msg.value = `已转采购订单 ${po?.doc_no || ''}（${po?.status || ''}）`
    tab.value = 'orders'
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

function lineInfo(o: PO) {
  return (o.lines || [])
    .map(l => `物料${l.material_id}×${l.qty}${l.qty_received != null ? `(已收${l.qty_received})` : ''}`)
    .join('；') || '—'
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <h2 class="page-title">采购订单 / 申请</h2>
      <div>
        <button class="btn" @click="showPR = !showPR">+ 采购申请</button>
        <button class="btn primary" @click="showPO = !showPO">{{ showPO ? '取消' : '+ 采购订单' }}</button>
      </div>
    </div>
    <div v-if="error" class="error-box">{{ error }}</div>
    <div v-if="msg" class="ok-box">{{ msg }}</div>

    <div class="tabs">
      <button class="tab" :class="{ active: tab === 'orders' }" @click="tab = 'orders'">采购订单</button>
      <button class="tab" :class="{ active: tab === 'requests' }" @click="tab = 'requests'">采购申请</button>
    </div>

    <div v-if="showPO" class="card form-card">
      <h3>新建采购订单</h3>
      <div class="form-grid">
        <label>供应商
          <select v-model.number="poForm.supplier_id">
            <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.code }} {{ s.name }}</option>
          </select>
        </label>
        <label>订单日 <input type="date" v-model="poForm.order_date" /></label>
        <label>备注 <input v-model="poForm.remark" /></label>
      </div>
      <h4>明细行</h4>
      <div v-for="(line, i) in poForm.lines" :key="i" class="line-row">
        <select v-model.number="line.material_id">
          <option v-for="m in materials" :key="m.id" :value="m.id">{{ m.code }} {{ m.name }}</option>
        </select>
        <input type="number" v-model.number="line.qty" min="0.001" step="1" placeholder="数量" />
        <input type="number" v-model.number="line.unit_price" min="0" step="0.01" placeholder="单价" />
        <button class="btn sm" @click="removePOLine(i)">删</button>
      </div>
      <button class="btn" @click="addPOLine">+ 行</button>
      <button class="btn primary" @click="createPO">保存草稿</button>
    </div>

    <div v-if="showPR" class="card form-card">
      <h3>新建采购申请</h3>
      <div class="form-grid">
        <label>申请日 <input type="date" v-model="prForm.request_date" /></label>
        <label>申请人 <input v-model="prForm.requester" /></label>
        <label>物料
          <select v-model.number="prForm.material_id">
            <option v-for="m in materials" :key="m.id" :value="m.id">{{ m.code }} {{ m.name }}</option>
          </select>
        </label>
        <label>数量 <input type="number" v-model.number="prForm.qty" min="0.001" /></label>
      </div>
      <button class="btn primary" @click="createPR">保存申请</button>
    </div>

    <div v-if="tab === 'orders'" class="card">
      <div class="toolbar-inner">
        <select v-model="statusFilter">
          <option value="">全部状态</option>
          <option value="DRAFT">草稿</option>
          <option value="CONFIRMED">已确认</option>
          <option value="PARTIAL">部分到货</option>
          <option value="CLOSED">关闭</option>
        </select>
      </div>
      <DataTable
        :columns="[
          { key: 'doc_no', label: '单号' },
          { key: 'status', label: '状态' },
          { key: 'supplier_id', label: '供应商' },
          { key: 'order_date', label: '日期' },
          { key: 'line_info', label: '明细' },
          { key: 'actions', label: '操作' },
        ]"
        :rows="filteredOrders.map(o => ({ ...o, line_info: lineInfo(o), actions: o.id })) as any"
        :loading="loading"
      >
        <template #status="{ row }">
          <StatusBadge :status="String(row.status)" />
        </template>
        <template #actions="{ row }">
          <button v-if="row.status === 'DRAFT'" class="btn sm green" @click="confirmPO(Number(row.id))">确认</button>
          <span v-else class="muted">—</span>
        </template>
      </DataTable>
    </div>

    <div v-if="tab === 'requests'" class="card">
      <div class="form-grid" style="margin-bottom:0.75rem">
        <label>转单默认供应商
          <select v-model.number="convertForm.supplier_id">
            <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.code }} {{ s.name }}</option>
          </select>
        </label>
        <label class="check"><input type="checkbox" v-model="convertForm.auto_confirm" /> 转单后自动确认 PO</label>
      </div>
      <DataTable
        :columns="[
          { key: 'doc_no', label: '申请号' },
          { key: 'status', label: '状态' },
          { key: 'request_date', label: '日期' },
          { key: 'actions', label: '操作' },
        ]"
        :rows="requests.map(r => ({ ...r, actions: r.id })) as any"
        :loading="loading"
      >
        <template #status="{ row }">
          <StatusBadge :status="String(row.status)" />
        </template>
        <template #actions="{ row }">
          <button
            v-if="row.status === 'DRAFT'"
            class="btn sm"
            @click="submitPR(Number(row.id))"
          >提交</button>
          <button
            v-if="['DRAFT','SUBMITTED','APPROVED'].includes(String(row.status))"
            class="btn sm green"
            @click="convertPR(requests.find(r => r.id === row.id)!)"
          >转 PO</button>
          <span v-if="row.status === 'ORDERED'" class="muted">已转单</span>
        </template>
      </DataTable>
    </div>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.5rem; }
.toolbar-inner { margin-bottom: 0.75rem; }
.page-title { margin: 0; font-size: 1.25rem; color: #1e3a5f; }
.tabs { display: flex; gap: 0.35rem; margin-bottom: 0.75rem; }
.tab { padding: 0.4rem 0.9rem; border: 1px solid #e2e8f0; border-radius: 6px; background: #f8fafc; cursor: pointer; font-size: 0.85rem; }
.tab.active { background: #1e3a5f; color: #fff; border-color: #1e3a5f; }
.card { background: #fff; border-radius: 10px; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,.06); margin-bottom: 1rem; }
.form-card h3, h4 { margin: 0 0 0.5rem; font-size: 0.95rem; color: #64748b; }
.form-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 0.75rem; margin-bottom: 0.75rem; }
.line-row { display: flex; gap: 0.5rem; margin-bottom: 0.5rem; flex-wrap: wrap; }
.line-row select, .line-row input { padding: 0.4rem 0.5rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.85rem; min-width: 100px; }
label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.8rem; color: #64748b; }
label.check { flex-direction: row; align-items: center; gap: 0.5rem; margin-top: 1.2rem; }
input, select { padding: 0.45rem 0.6rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.875rem; }
.btn { padding: 0.45rem 1rem; border: none; border-radius: 6px; font-size: 0.875rem; cursor: pointer; background: #e2e8f0; margin-right: 0.35rem; }
.btn.primary { background: #1e3a5f; color: #fff; }
.btn.sm { padding: 0.25rem 0.5rem; font-size: 0.75rem; background: #dbeafe; color: #1d4ed8; }
.btn.sm.green { background: #dcfce7; color: #15803d; }
.error-box { background: #fef2f2; color: #b91c1c; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
.ok-box { background: #ecfdf5; color: #065f46; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
.muted { color: #94a3b8; font-size: 0.8rem; }
</style>
