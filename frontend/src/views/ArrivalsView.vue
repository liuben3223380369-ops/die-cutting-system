<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { api, type PurchaseOrder, type Warehouse } from '../api/client'
import DataTable from '../components/DataTable.vue'
import StatusBadge from '../components/StatusBadge.vue'

interface ArrivalLine {
  id: number
  material_id: number
  qty: number
  batch_no: string
  qc_status: string
  qty_passed: number
  qty_failed: number
}
interface Arrival {
  id: number
  doc_no: string
  status: string
  order_id: number
  arrival_date: string
  warehouse_id: number
  lines: ArrivalLine[]
}

const arrivals = ref<Arrival[]>([])
const orders = ref<PurchaseOrder[]>([])
const warehouses = ref<Warehouse[]>([])
const loading = ref(true)
const error = ref('')
const msg = ref('')
const iqcRecords = ref<any[]>([])

const showArrival = ref(false)
const arrivalForm = ref({
  order_id: 0,
  arrival_date: new Date().toISOString().slice(0, 10),
  warehouse_id: 0,
  order_line_id: 0,
  material_id: 0,
  qty: 0,
  batch_no: '',
})

const showIqc = ref(false)
const iqcForm = ref({
  arrival_line_id: 0,
  qty_inspected: 0,
  qty_passed: 0,
  qty_failed: 0,
  target_warehouse_id: 0,
  hold_warehouse_id: 0 as number | null,
  inspect_date: new Date().toISOString().slice(0, 10),
})

const selectedPoLines = computed(() => {
  const po = orders.value.find(o => o.id === arrivalForm.value.order_id)
  if (!po?.lines) return []
  return po.lines
    .map(l => ({
      ...l,
      remain: Number(l.qty) - Number(l.qty_received || 0),
    }))
    .filter(l => l.remain > 0)
})

const pendingIqcCount = computed(() =>
  arrivals.value.reduce(
    (n, a) => n + (a.lines || []).filter(l => l.qc_status === 'PENDING').length,
    0
  )
)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [arr, ords, whs, iqcs] = await Promise.all([
      api.get<Arrival[]>('/purchase/arrivals'),
      api.get<PurchaseOrder[]>('/purchase/orders'),
      api.get<Warehouse[]>('/master/warehouses'),
      api.get<any[]>('/purchase/iqc').catch(() => []),
    ])
    arrivals.value = arr
    orders.value = ords.filter(o => ['CONFIRMED', 'PARTIAL'].includes(o.status))
    warehouses.value = whs
    iqcRecords.value = iqcs || []
    if (whs.length) {
      arrivalForm.value.warehouse_id = whs[0].id
      iqcForm.value.target_warehouse_id = whs[0].id
    }
    if (orders.value.length && !arrivalForm.value.order_id) {
      arrivalForm.value.order_id = orders.value[0].id
      onOrderChange()
    }
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function onOrderChange() {
  const lines = selectedPoLines.value
  if (lines.length) {
    selectLine(lines[0].id)
  } else {
    arrivalForm.value.order_line_id = 0
    arrivalForm.value.material_id = 0
    arrivalForm.value.qty = 0
  }
}

function selectLine(lineId: number) {
  const line = selectedPoLines.value.find(l => l.id === lineId)
  if (!line) return
  arrivalForm.value.order_line_id = line.id
  arrivalForm.value.material_id = line.material_id
  arrivalForm.value.qty = line.remain
  if (!arrivalForm.value.batch_no) {
    const d = new Date().toISOString().slice(0, 10).replace(/-/g, '')
    arrivalForm.value.batch_no = `B${d}-${line.material_id}`
  }
}

async function createArrival() {
  if (!arrivalForm.value.order_id || !arrivalForm.value.order_line_id) {
    error.value = '请选择采购订单及明细行'
    return
  }
  if (arrivalForm.value.qty <= 0) {
    error.value = '到货数量必须大于0'
    return
  }
  try {
    await api.post('/purchase/arrivals', {
      order_id: arrivalForm.value.order_id,
      arrival_date: arrivalForm.value.arrival_date,
      warehouse_id: arrivalForm.value.warehouse_id,
      lines: [{
        order_line_id: arrivalForm.value.order_line_id,
        material_id: arrivalForm.value.material_id,
        qty: arrivalForm.value.qty,
        batch_no: arrivalForm.value.batch_no || '',
      }],
    })
    showArrival.value = false
    msg.value = '到货登记成功，请做 IQC'
    arrivalForm.value.batch_no = ''
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

function openIqc(lineId: number, qty: number) {
  iqcForm.value.arrival_line_id = lineId
  iqcForm.value.qty_inspected = qty
  iqcForm.value.qty_passed = qty
  iqcForm.value.qty_failed = 0
  showIqc.value = true
}

function syncIqcQty() {
  const ins = Number(iqcForm.value.qty_inspected) || 0
  const fail = Number(iqcForm.value.qty_failed) || 0
  iqcForm.value.qty_passed = Math.max(0, ins - fail)
}

async function submitIqc() {
  try {
    const result =
      iqcForm.value.qty_failed === 0
        ? 'PASSED'
        : iqcForm.value.qty_passed === 0
          ? 'FAILED'
          : 'PARTIAL'
    await api.post('/purchase/iqc', {
      arrival_line_id: iqcForm.value.arrival_line_id,
      result,
      qty_inspected: iqcForm.value.qty_inspected,
      qty_passed: iqcForm.value.qty_passed,
      qty_failed: iqcForm.value.qty_failed,
      inspect_date: iqcForm.value.inspect_date,
      target_warehouse_id: iqcForm.value.target_warehouse_id,
      hold_warehouse_id: iqcForm.value.hold_warehouse_id || null,
    })
    showIqc.value = false
    msg.value = 'IQC 完成：合格数量已入库' + (iqcForm.value.qty_failed ? '，不合格已登记' : '')
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

function lineInfo(a: Arrival) {
  return a.lines
    ?.map(l => `行${l.id} 物料${l.material_id}×${l.qty} QC=${l.qc_status}`)
    .join('；') || '—'
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <h2 class="page-title">到货 / IQC</h2>
      <div class="toolbar-right">
        <span v-if="pendingIqcCount" class="badge">待 IQC {{ pendingIqcCount }}</span>
        <button class="btn primary" @click="showArrival = !showArrival">
          {{ showArrival ? '取消' : '+ 到货登记' }}
        </button>
      </div>
    </div>
    <div v-if="error" class="error-box">{{ error }}</div>
    <div v-if="msg" class="ok-box">{{ msg }}</div>

    <div v-if="!orders.length && !loading" class="card tip-card">
      <p>暂无「已确认/部分到货」的采购订单。请先在采购订单中确认，或从 MRP 生成 PO。</p>
    </div>

    <div v-if="showArrival" class="card form-card">
      <h3>到货登记</h3>
      <div class="form-grid">
        <label>采购订单
          <select v-model.number="arrivalForm.order_id" @change="onOrderChange">
            <option :value="0">请选择</option>
            <option v-for="o in orders" :key="o.id" :value="o.id">
              {{ o.doc_no }} ({{ o.status }})
            </option>
          </select>
        </label>
        <label>订单明细行
          <select
            v-model.number="arrivalForm.order_line_id"
            @change="selectLine(arrivalForm.order_line_id)"
          >
            <option :value="0">请选择</option>
            <option v-for="l in selectedPoLines" :key="l.id" :value="l.id">
              行{{ l.id }} 物料{{ l.material_id }} 剩余{{ l.remain }}
            </option>
          </select>
        </label>
        <label>到货日 <input type="date" v-model="arrivalForm.arrival_date" /></label>
        <label>仓库
          <select v-model.number="arrivalForm.warehouse_id">
            <option v-for="w in warehouses" :key="w.id" :value="w.id">{{ w.code }} {{ w.name }}</option>
          </select>
        </label>
        <label>数量 <input type="number" v-model.number="arrivalForm.qty" min="0.001" step="1" /></label>
        <label>批次号 <input v-model="arrivalForm.batch_no" placeholder="自动生成可改" /></label>
      </div>
      <button class="btn primary" @click="createArrival">提交到货</button>
    </div>

    <div v-if="showIqc" class="card form-card">
      <h3>IQC 检验（行 {{ iqcForm.arrival_line_id }}）</h3>
      <div class="form-grid">
        <label>检验数 <input type="number" v-model.number="iqcForm.qty_inspected" @change="syncIqcQty" /></label>
        <label>不合格 <input type="number" v-model.number="iqcForm.qty_failed" @change="syncIqcQty" /></label>
        <label>合格 <input type="number" v-model.number="iqcForm.qty_passed" /></label>
        <label>检验日 <input type="date" v-model="iqcForm.inspect_date" /></label>
        <label>合格入库仓
          <select v-model.number="iqcForm.target_warehouse_id">
            <option v-for="w in warehouses" :key="w.id" :value="w.id">{{ w.code }} {{ w.name }}</option>
          </select>
        </label>
        <label>隔离仓（不合格可选）
          <select v-model.number="iqcForm.hold_warehouse_id">
            <option :value="0">不隔离</option>
            <option v-for="w in warehouses" :key="w.id" :value="w.id">{{ w.code }} {{ w.name }}</option>
          </select>
        </label>
      </div>
      <button class="btn primary" @click="submitIqc">提交 IQC 并入库</button>
      <button class="btn" @click="showIqc = false">取消</button>
    </div>

    <div class="card">
      <h3 class="sec-title">到货单</h3>
      <DataTable
        :columns="[
          { key: 'doc_no', label: '到货单号' },
          { key: 'status', label: '状态' },
          { key: 'order_id', label: '订单' },
          { key: 'arrival_date', label: '到货日' },
          { key: 'line_info', label: '明细/QC' },
          { key: 'actions', label: '操作' },
        ]"
        :rows="arrivals.map(a => ({
          ...a,
          line_info: lineInfo(a),
          actions: a.id,
        })) as any"
        :loading="loading"
      >
        <template #status="{ row }">
          <StatusBadge :status="String(row.status)" />
        </template>
        <template #actions="{ row }">
          <template v-for="line in (arrivals.find(a => a.id === row.id)?.lines || [])" :key="line.id">
            <button
              v-if="line.qc_status === 'PENDING'"
              class="btn sm"
              @click="openIqc(line.id, Number(line.qty))"
            >IQC #{{ line.id }}</button>
            <span v-else class="muted">#{{ line.id }} {{ line.qc_status }}</span>
          </template>
        </template>
      </DataTable>
    </div>

    <div class="card">
      <h3 class="sec-title">IQC 记录</h3>
      <DataTable
        :columns="[
          { key: 'doc_no', label: '检验单号' },
          { key: 'result', label: '结果' },
          { key: 'material_id', label: '物料' },
          { key: 'qty_passed', label: '合格' },
          { key: 'qty_failed', label: '不合格' },
          { key: 'inspect_date', label: '日期' },
        ]"
        :rows="iqcRecords as any"
        :loading="loading"
      >
        <template #result="{ row }">
          <StatusBadge :status="String(row.result)" />
        </template>
      </DataTable>
    </div>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.5rem; }
.toolbar-right { display: flex; align-items: center; gap: 0.5rem; }
.page-title { margin: 0; font-size: 1.25rem; color: #1e3a5f; }
.sec-title { margin: 0 0 0.75rem; font-size: 0.95rem; color: #64748b; }
.badge { background: #fef3c7; color: #b45309; padding: 0.25rem 0.6rem; border-radius: 999px; font-size: 0.8rem; font-weight: 600; }
.card { background: #fff; border-radius: 10px; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,.06); margin-bottom: 1rem; }
.tip-card p { margin: 0; font-size: 0.9rem; color: #64748b; }
.form-card h3 { margin: 0 0 0.75rem; font-size: 0.95rem; color: #64748b; }
.form-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 0.75rem; margin-bottom: 1rem; }
label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.8rem; color: #64748b; }
input, select { padding: 0.45rem 0.6rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.875rem; }
.btn { padding: 0.45rem 1rem; border: none; border-radius: 6px; font-size: 0.875rem; cursor: pointer; background: #e2e8f0; margin-right: 0.5rem; }
.btn.primary { background: #1e3a5f; color: #fff; }
.btn.sm { padding: 0.25rem 0.5rem; font-size: 0.75rem; background: #dbeafe; color: #1d4ed8; }
.error-box { background: #fef2f2; color: #b91c1c; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
.ok-box { background: #ecfdf5; color: #065f46; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
.muted { color: #94a3b8; font-size: 0.75rem; margin-right: 0.35rem; }
</style>
