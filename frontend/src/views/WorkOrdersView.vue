<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { api } from '../api/client'
import DataTable from '../components/DataTable.vue'
import StatusBadge from '../components/StatusBadge.vue'

interface WOMat {
  id: number
  material_id: number
  qty_required: number
  qty_issued: number
  qty_returned?: number
}
interface WOOp {
  id: number
  seq: number
  step_name: string
  step_type: string
  status: string
  qty_good: number
  qty_reject?: number
  qty_scrap?: number
}
interface WO {
  id: number
  doc_no: string
  status: string
  product_id: number
  product_version_id: number
  plan_qty: number
  completed_qty: number
  scrap_qty?: number
  warehouse_id?: number
  fg_warehouse_id?: number
  progress_pct?: number
  materials: WOMat[]
  operations: WOOp[]
}

const rows = ref<WO[]>([])
const products = ref<Array<{ id: number; code: string; name: string }>>([])
const versions = ref<Array<{ id: number; product_id: number; version_code: string; status: string }>>([])
const warehouses = ref<Array<{ id: number; code: string; name: string }>>([])
const loading = ref(true)
const error = ref('')
const msg = ref('')
const selected = ref<WO | null>(null)
const reportQty = ref(0)

const showForm = ref(false)
const form = ref({
  product_id: 0,
  product_version_id: 0,
  plan_qty: 100,
  warehouse_id: 0,
  fg_warehouse_id: 0,
  wip_warehouse_id: 0,
})

const progressOf = (wo: WO) =>
  wo.progress_pct ?? (wo.plan_qty > 0 ? Math.min(100, (Number(wo.completed_qty) / Number(wo.plan_qty)) * 100) : 0)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [wos, prods, vers, whs] = await Promise.all([
      api.get<WO[]>('/production/work-orders'),
      api.get<Array<{ id: number; code: string; name: string }>>('/engineering/products'),
      api.get<Array<{ id: number; product_id: number; version_code: string; status: string }>>('/engineering/versions'),
      api.get<Array<{ id: number; code: string; name: string }>>('/master/warehouses'),
    ])
    rows.value = wos
    products.value = prods
    versions.value = vers.filter(v => v.status === 'RELEASED')
    warehouses.value = whs
    if (prods.length) form.value.product_id = prods[0].id
    const fv = versions.value.filter(v => v.product_id === form.value.product_id)
    if (fv.length) form.value.product_version_id = fv[0].id
    if (whs.length) {
      form.value.warehouse_id = whs[0].id
      form.value.fg_warehouse_id = whs[whs.length > 1 ? 1 : 0].id
    }
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function filteredVersions() {
  return versions.value.filter(v => v.product_id === form.value.product_id)
}

async function createWO() {
  try {
    const body: any = { ...form.value }
    if (!body.wip_warehouse_id) delete body.wip_warehouse_id
    await api.post('/production/work-orders', body)
    showForm.value = false
    msg.value = '工单已创建（版本/BOM/工艺已锁定）'
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

async function release(id: number) {
  try {
    await api.post(`/production/work-orders/${id}/release`)
    msg.value = '工单已下达'
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

async function cancelWO(id: number) {
  try {
    await api.post(`/production/work-orders/${id}/cancel`)
    msg.value = '工单已取消'
    selected.value = null
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

async function issueAll(wo: WO) {
  try {
    const items = (wo.materials || [])
      .filter(m => Number(m.qty_required) > Number(m.qty_issued))
      .map(m => ({
        material_id: m.material_id,
        qty: Number(m.qty_required) - Number(m.qty_issued),
      }))
    if (!items.length) {
      msg.value = '无需领料'
      return
    }
    await api.post(`/production/work-orders/${wo.id}/issue`, {
      items,
      warehouse_id: wo.warehouse_id || form.value.warehouse_id,
    })
    msg.value = '领料完成'
    await load()
    await openDetail(wo.id)
  } catch (e: any) {
    error.value = e.message
  }
}

async function returnAll(wo: WO) {
  try {
    const items = (wo.materials || [])
      .map(m => {
        const net = Number(m.qty_issued) - Number(m.qty_returned || 0)
        return net > 0 ? { material_id: m.material_id, qty: net } : null
      })
      .filter(Boolean) as Array<{ material_id: number; qty: number }>
    if (!items.length) {
      msg.value = '无可退物料'
      return
    }
    await api.post(`/production/work-orders/${wo.id}/return`, {
      items,
      warehouse_id: wo.warehouse_id || form.value.warehouse_id,
    })
    msg.value = '退料完成'
    await load()
    await openDetail(wo.id)
  } catch (e: any) {
    error.value = e.message
  }
}

async function reportOp(wo: WO, opId: number) {
  try {
    const q = reportQty.value > 0 ? reportQty.value : Number(wo.plan_qty)
    await api.post(`/production/work-orders/${wo.id}/report`, {
      operation_id: opId,
      qty_good: q,
      qty_reject: 0,
      qty_scrap: 0,
    })
    msg.value = `报工成功：良品 ${q}`
    await load()
    await openDetail(wo.id)
  } catch (e: any) {
    error.value = e.message
  }
}

async function receiveFG(wo: WO) {
  try {
    const qty = Number(wo.plan_qty) - Number(wo.completed_qty)
    if (qty <= 0) {
      msg.value = '已全部入库'
      return
    }
    await api.post(`/production/work-orders/${wo.id}/receive-fg`, {
      qty,
      warehouse_id: wo.fg_warehouse_id || form.value.fg_warehouse_id,
    })
    msg.value = '成品入库成功'
    await load()
    await openDetail(wo.id)
  } catch (e: any) {
    error.value = e.message
  }
}

async function complete(id: number, force = false) {
  try {
    await api.post(`/production/work-orders/${id}/complete`, { force })
    msg.value = force ? '已强制完工' : '工单已完工'
    await load()
    selected.value = null
  } catch (e: any) {
    error.value = e.message
  }
}

async function openDetail(id: number) {
  try {
    selected.value = await api.get<WO>(`/production/work-orders/${id}`)
    if (selected.value) reportQty.value = Number(selected.value.plan_qty)
  } catch (e: any) {
    error.value = e.message
  }
}

onMounted(async () => {
  await load()
  const oid = sessionStorage.getItem('open_wo_id')
  if (oid) {
    sessionStorage.removeItem('open_wo_id')
    await openDetail(Number(oid))
  }
})
</script>

<template>
  <div>
    <div class="toolbar">
      <h2 class="page-title">生产工单</h2>
      <button class="btn primary" @click="showForm = !showForm">{{ showForm ? '取消' : '+ 新建工单' }}</button>
    </div>
    <div v-if="error" class="error-box">{{ error }}</div>
    <div v-if="msg" class="ok-box">{{ msg }}</div>

    <div v-if="showForm" class="card form-card">
      <div class="form-grid">
        <label>产品
          <select v-model.number="form.product_id">
            <option v-for="p in products" :key="p.id" :value="p.id">{{ p.code }} {{ p.name }}</option>
          </select>
        </label>
        <label>已发布版本
          <select v-model.number="form.product_version_id">
            <option v-for="v in filteredVersions()" :key="v.id" :value="v.id">{{ v.version_code }}</option>
          </select>
        </label>
        <label>计划数量 <input type="number" v-model.number="form.plan_qty" min="1" /></label>
        <label>领料仓
          <select v-model.number="form.warehouse_id">
            <option v-for="w in warehouses" :key="w.id" :value="w.id">{{ w.code }}</option>
          </select>
        </label>
        <label>成品仓
          <select v-model.number="form.fg_warehouse_id">
            <option v-for="w in warehouses" :key="w.id" :value="w.id">{{ w.code }}</option>
          </select>
        </label>
        <label>WIP仓（可选）
          <select v-model.number="form.wip_warehouse_id">
            <option :value="0">不使用</option>
            <option v-for="w in warehouses" :key="w.id" :value="w.id">{{ w.code }}</option>
          </select>
        </label>
      </div>
      <p class="tip">创建时锁定 BOM/工艺；仅已发布版本可选。报工须按工序顺序，首道前需领料。</p>
      <button class="btn primary" @click="createWO">创建工单</button>
    </div>

    <div class="card">
      <DataTable
        :columns="[
          { key: 'doc_no', label: '工单号' },
          { key: 'status', label: '状态' },
          { key: 'product_id', label: '产品' },
          { key: 'plan_qty', label: '计划' },
          { key: 'completed_qty', label: '完工' },
          { key: 'progress', label: '进度' },
          { key: 'actions', label: '操作' },
        ]"
        :rows="rows.map(r => ({ ...r, progress: progressOf(r), actions: r.id })) as any"
        :loading="loading"
      >
        <template #status="{ row }">
          <StatusBadge :status="String(row.status)" />
        </template>
        <template #progress="{ row }">
          <div class="progress">
            <div class="bar" :style="{ width: progressOf(row as any) + '%' }"></div>
            <span>{{ progressOf(row as any).toFixed(0) }}%</span>
          </div>
        </template>
        <template #actions="{ row }">
          <button class="btn sm" @click="openDetail(Number(row.id))">详情</button>
          <button v-if="row.status === 'DRAFT'" class="btn sm green" @click="release(Number(row.id))">下达</button>
          <button v-if="row.status === 'DRAFT' || row.status === 'RELEASED'" class="btn sm danger" @click="cancelWO(Number(row.id))">取消</button>
        </template>
      </DataTable>
    </div>

    <div v-if="selected" class="card detail">
      <div class="detail-head">
        <h3>{{ selected.doc_no }} <StatusBadge :status="selected.status" /></h3>
        <button class="btn" @click="selected = null">关闭</button>
      </div>
      <p class="meta">
        产品 {{ selected.product_id }} · 版本 {{ selected.product_version_id }} ·
        计划 {{ selected.plan_qty }} · 已完工 {{ selected.completed_qty }}
        <span v-if="selected.scrap_qty"> · 报废 {{ selected.scrap_qty }}</span>
      </p>
      <div class="progress large">
        <div class="bar" :style="{ width: progressOf(selected) + '%' }"></div>
        <span>{{ progressOf(selected).toFixed(1) }}%</span>
      </div>

      <h4>物料需求</h4>
      <DataTable
        :columns="[
          { key: 'material_id', label: '物料' },
          { key: 'qty_required', label: '需求' },
          { key: 'qty_issued', label: '已领' },
          { key: 'qty_returned', label: '已退' },
        ]"
        :rows="(selected.materials || []) as any"
      />
      <div class="actions-row" v-if="['RELEASED','IN_PROGRESS'].includes(selected.status)">
        <button class="btn primary" @click="issueAll(selected)">按需求领料</button>
        <button class="btn" @click="returnAll(selected)">全部退料</button>
      </div>

      <h4>工序（须按顺序报工）</h4>
      <label class="inline-qty">本次良品数 <input type="number" v-model.number="reportQty" min="0.001" step="1" /></label>
      <DataTable
        :columns="[
          { key: 'seq', label: '序号' },
          { key: 'step_name', label: '工序' },
          { key: 'step_type', label: '类型' },
          { key: 'status', label: '状态' },
          { key: 'qty_good', label: '良品' },
          { key: 'op_actions', label: '报工' },
        ]"
        :rows="(selected.operations || []).map(o => ({ ...o, op_actions: o.id })) as any"
      >
        <template #status="{ row }">
          <StatusBadge :status="String(row.status)" />
        </template>
        <template #op_actions="{ row }">
          <button
            v-if="['RELEASED','IN_PROGRESS'].includes(selected!.status) && row.status !== 'DONE'"
            class="btn sm"
            @click="reportOp(selected!, Number(row.id))"
          >报良品</button>
          <span v-else-if="row.status === 'DONE'" class="muted">已完成</span>
        </template>
      </DataTable>

      <div class="actions-row" v-if="['RELEASED','IN_PROGRESS'].includes(selected.status)">
        <button class="btn primary" @click="receiveFG(selected)">成品入库（剩余）</button>
        <button class="btn green" @click="complete(selected.id, false)">完工</button>
        <button class="btn" @click="complete(selected.id, true)">强制完工</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.page-title { margin: 0; font-size: 1.25rem; color: #1e3a5f; }
.card { background: #fff; border-radius: 10px; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,.06); margin-bottom: 1rem; }
.form-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 0.75rem; margin-bottom: 0.75rem; }
label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.8rem; color: #64748b; }
input, select { padding: 0.45rem 0.6rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.875rem; }
.btn { padding: 0.45rem 1rem; border: none; border-radius: 6px; font-size: 0.875rem; cursor: pointer; background: #e2e8f0; margin-right: 0.35rem; }
.btn.primary { background: #1e3a5f; color: #fff; }
.btn.green { background: #15803d; color: #fff; }
.btn.sm { padding: 0.25rem 0.5rem; font-size: 0.75rem; background: #dbeafe; color: #1d4ed8; }
.btn.sm.green { background: #dcfce7; color: #15803d; }
.btn.sm.danger { background: #fee2e2; color: #b91c1c; }
.error-box { background: #fef2f2; color: #b91c1c; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
.ok-box { background: #ecfdf5; color: #065f46; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
.tip { font-size: 0.8rem; color: #94a3b8; margin: 0 0 0.75rem; }
.detail-head { display: flex; justify-content: space-between; align-items: center; }
.detail-head h3 { margin: 0; font-size: 1.05rem; }
.meta { font-size: 0.85rem; color: #64748b; margin: 0.5rem 0 0.75rem; }
h4 { margin: 1rem 0 0.5rem; font-size: 0.9rem; color: #475569; }
.actions-row { margin-top: 0.75rem; }
.progress {
  position: relative;
  height: 18px;
  background: #e2e8f0;
  border-radius: 9px;
  overflow: hidden;
  min-width: 80px;
  font-size: 0.7rem;
  color: #1e3a5f;
  display: flex;
  align-items: center;
  justify-content: center;
}
.progress.large { height: 22px; margin-bottom: 0.5rem; font-size: 0.8rem; }
.progress .bar {
  position: absolute;
  left: 0; top: 0; bottom: 0;
  background: linear-gradient(90deg, #3b82f6, #22c55e);
  border-radius: 9px;
  z-index: 0;
}
.progress span { position: relative; z-index: 1; font-weight: 600; }
.muted { color: #94a3b8; font-size: 0.8rem; }
.inline-qty { display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; color: #64748b; margin: 0.5rem 0; }
.inline-qty input { width: 100px; padding: 0.35rem 0.5rem; border: 1px solid #e2e8f0; border-radius: 6px; }
</style>
