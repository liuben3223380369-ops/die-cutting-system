<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api/client'
import DataTable from '../components/DataTable.vue'
import StatusBadge from '../components/StatusBadge.vue'

interface SO {
  id: number
  doc_no: string
  status: string
  customer_id: number
  order_date: string
  lines: Array<{ id: number; product_id: number; qty: number; product_version_id?: number }>
}
interface MrpReq {
  material_id: number
  level: number
  gross_qty: number
  on_hand_qty: number
  on_order_qty: number
  net_qty: number
  suggestion_type: string
  suggestion_qty: number
}
interface MrpRun {
  id: number
  run_no: string
  status: string
  sales_order_id?: number
  requirements: MrpReq[]
}

const orders = ref<SO[]>([])
const products = ref<Array<{ id: number; code: string; name: string }>>([])
const customers = ref<Array<{ id: number; code: string; name: string }>>([])
const lastRun = ref<MrpRun | null>(null)
const loading = ref(true)
const error = ref('')
const msg = ref('')

const showForm = ref(false)
const form = ref({
  customer_id: 0,
  order_date: new Date().toISOString().slice(0, 10),
  product_id: 0,
  qty: 100,
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [sos, prods, whs, sups] = await Promise.all([
      api.get<SO[]>('/planning/sales-orders'),
      api.get<Array<{ id: number; code: string; name: string }>>('/engineering/products'),
      api.get<Array<{ id: number; code: string; name: string }>>('/master/warehouses').catch(() => []),
      api.get<Array<{ id: number; code: string; name: string }>>('/master/suppliers').catch(() => []),
    ])
    orders.value = sos
    products.value = prods
    warehouses.value = whs || []
    suppliers.value = (sups as any) || []
    if (warehouses.value.length) {
      woWarehouseId.value = warehouses.value[0].id
      woFgWarehouseId.value = warehouses.value[warehouses.value.length > 1 ? 1 : 0].id
    }
    if (suppliers.value.length) supplierId.value = suppliers.value[0].id
    // 客户可能为空，用 id=1 占位；实际应有 master/customers
    try {
      customers.value = await api.get('/master/customers' as any)
    } catch {
      customers.value = [{ id: 1, code: 'C001', name: '默认客户' }]
    }
    if (products.value.length) form.value.product_id = products.value[0].id
    if (customers.value.length) form.value.customer_id = customers.value[0].id
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function createSO() {
  try {
    await api.post('/planning/sales-orders', {
      customer_id: form.value.customer_id || 1,
      order_date: form.value.order_date,
      lines: [{ product_id: form.value.product_id, qty: form.value.qty }],
    })
    showForm.value = false
    msg.value = '销售订单已创建'
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

async function confirmSO(id: number) {
  try {
    await api.post(`/planning/sales-orders/${id}/confirm`)
    msg.value = '订单已确认'
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

const warehouses = ref<Array<{ id: number; code: string; name: string }>>([])
const suppliers = ref<Array<{ id: number; code: string; name: string }>>([])
const supplierId = ref(0)
const autoConfirmPo = ref(false)
const splitBySupplier = ref(true)
const woWarehouseId = ref(0)
const woFgWarehouseId = ref(0)
const woWipWarehouseId = ref(0)

async function createPOFromMrp() {
  if (!lastRun.value?.id) {
    error.value = '请先跑 MRP'
    return
  }
  if (!splitBySupplier.value && !supplierId.value) {
    error.value = '未拆分时请选择供应商'
    return
  }
  try {
    const created = await api.post<any[]>('/planning/mrp/create-purchase-orders', {
      run_id: lastRun.value.id,
      supplier_id: supplierId.value || null,
      auto_confirm: autoConfirmPo.value,
      split_by_default_supplier: splitBySupplier.value,
    })
    msg.value = `已生成采购订单：` + (created || []).map((p: any) => p.doc_no + '(' + p.status + ')').join(', ')
  } catch (e: any) {
    error.value = e.message
  }
}

async function createWOFromMrp() {
  if (!lastRun.value?.id) {
    error.value = '请先跑 MRP'
    return
  }
  try {
    const created = await api.post<any[]>('/planning/mrp/create-work-orders', {
      run_id: lastRun.value.id,
      warehouse_id: woWarehouseId.value || null,
      fg_warehouse_id: woFgWarehouseId.value || null,
      wip_warehouse_id: woWipWarehouseId.value || null,
    })
    msg.value = `已生成 ${created?.length || 0} 张工单：` + (created || []).map((w: any) => w.doc_no).join(', ')
  } catch (e: any) {
    error.value = e.message
  }
}

async function runMrp(orderId?: number) {
  try {
    lastRun.value = await api.post<MrpRun>('/planning/mrp/run', {
      sales_order_id: orderId || null,
      remark: orderId ? `针对订单 ${orderId}` : '全部确认订单',
    })
    msg.value = `MRP 完成：${lastRun.value?.run_no}，共 ${lastRun.value?.requirements?.length || 0} 条需求`
  } catch (e: any) {
    error.value = e.message
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <h2 class="page-title">销售订单 / MRP</h2>
      <div>
        <button class="btn primary" @click="showForm = !showForm">+ 销售订单</button>
        <button class="btn" @click="runMrp()">跑全部 MRP</button>
      </div>
    </div>
    <div v-if="error" class="error-box">{{ error }}</div>
    <div v-if="msg" class="ok-box">{{ msg }}</div>

    <div v-if="showForm" class="card form-card">
      <div class="form-grid">
        <label>客户ID <input type="number" v-model.number="form.customer_id" /></label>
        <label>订单日 <input type="date" v-model="form.order_date" /></label>
        <label>产品
          <select v-model.number="form.product_id">
            <option v-for="p in products" :key="p.id" :value="p.id">{{ p.code }} {{ p.name }}</option>
          </select>
        </label>
        <label>数量 <input type="number" v-model.number="form.qty" min="1" /></label>
      </div>
      <button class="btn primary" @click="createSO">创建</button>
    </div>

    <div class="card">
      <h3>销售订单</h3>
      <DataTable
        :columns="[
          { key: 'doc_no', label: '单号' },
          { key: 'status', label: '状态' },
          { key: 'customer_id', label: '客户' },
          { key: 'order_date', label: '订单日' },
          { key: 'lines_info', label: '明细' },
          { key: 'actions', label: '操作' },
        ]"
        :rows="orders.map(o => ({
          ...o,
          lines_info: o.lines?.map(l => `产品${l.product_id}×${l.qty}`).join(', '),
          actions: o.id,
        })) as any"
        :loading="loading"
      >
        <template #status="{ row }">
          <StatusBadge :status="String(row.status)" />
        </template>
        <template #actions="{ row }">
          <button v-if="row.status === 'DRAFT'" class="btn sm" @click="confirmSO(Number(row.id))">确认</button>
          <button
            v-if="row.status === 'CONFIRMED' || row.status === 'PARTIAL'"
            class="btn sm green"
            @click="runMrp(Number(row.id))"
          >跑 MRP</button>
        </template>
      </DataTable>
    </div>

    <div v-if="lastRun" class="card">
      <h3>MRP 结果 · {{ lastRun.run_no }} <StatusBadge :status="lastRun.status" /></h3>
      <DataTable
        :columns="[
          { key: 'level', label: '层级' },
          { key: 'material_id', label: '物料' },
          { key: 'gross_qty', label: '毛需求' },
          { key: 'on_hand_qty', label: '库存' },
          { key: 'on_order_qty', label: '在途' },
          { key: 'net_qty', label: '净需求' },
          { key: 'suggestion_type', label: '建议' },
          { key: 'suggestion_qty', label: '建议量' },
        ]"
        :rows="(lastRun.requirements || []) as any"
      >
        <template #suggestion_type="{ row }">
          <span :class="row.suggestion_type === 'PURCHASE' ? 'buy' : row.suggestion_type === 'PRODUCE' ? 'make' : 'muted'">
            {{ row.suggestion_type }}
          </span>
        </template>
      </DataTable>
      <p class="tip">净需求 = 毛需求 − (库存 − 预留) − 在途采购。原料建议 PURCHASE，半成品/成品建议 PRODUCE。</p>
      <div class="form-grid" style="margin-top:0.75rem">
        <label>领料仓
          <select v-model.number="woWarehouseId">
            <option :value="0">不指定</option>
            <option v-for="w in warehouses" :key="w.id" :value="w.id">{{ w.code }}</option>
          </select>
        </label>
        <label>成品仓
          <select v-model.number="woFgWarehouseId">
            <option :value="0">不指定</option>
            <option v-for="w in warehouses" :key="w.id" :value="w.id">{{ w.code }}</option>
          </select>
        </label>
        <label>WIP仓（可选）
          <select v-model.number="woWipWarehouseId">
            <option :value="0">不使用</option>
            <option v-for="w in warehouses" :key="w.id" :value="w.id">{{ w.code }}</option>
          </select>
        </label>
      </div>
      <button class="btn primary" @click="createWOFromMrp">按 PRODUCE 建议生成工单</button>
      <div class="form-grid" style="margin-top:0.75rem">
        <label>供应商
          <select v-model.number="supplierId">
            <option :value="0">请选择</option>
            <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.code }} {{ s.name }}</option>
          </select>
        </label>
        <label class="check"><input type="checkbox" v-model="autoConfirmPo" /> 生成后自动确认 PO</label>
        <label class="check"><input type="checkbox" v-model="splitBySupplier" /> 按物料默认供应商拆分 PO</label>
      </div>
      <p class="tip">拆分时无默认供应商的物料会落到所选「兜底供应商」。</p>
      <button class="btn" @click="createPOFromMrp">按 PURCHASE 建议生成采购订单</button>
    </div>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.5rem; }
.page-title { margin: 0; font-size: 1.25rem; color: #1e3a5f; }
.card { background: #fff; border-radius: 10px; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,.06); margin-bottom: 1rem; }
.card h3 { margin: 0 0 0.75rem; font-size: 0.95rem; color: #64748b; }
.form-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 0.75rem; margin-bottom: 1rem; }
label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.8rem; color: #64748b; }
input, select { padding: 0.45rem 0.6rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.875rem; }
.btn { padding: 0.45rem 1rem; border: none; border-radius: 6px; font-size: 0.875rem; cursor: pointer; background: #e2e8f0; margin-right: 0.35rem; }
.btn.primary { background: #1e3a5f; color: #fff; }
.btn.sm { padding: 0.25rem 0.5rem; font-size: 0.75rem; background: #dbeafe; color: #1d4ed8; }
.btn.sm.green { background: #dcfce7; color: #15803d; }
.error-box { background: #fef2f2; color: #b91c1c; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
.ok-box { background: #ecfdf5; color: #065f46; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
.buy { color: #c2410c; font-weight: 600; }
.make { color: #1d4ed8; font-weight: 600; }
.muted { color: #94a3b8; }
.tip { margin-top: 0.75rem; font-size: 0.8rem; color: #94a3b8; }
</style>
