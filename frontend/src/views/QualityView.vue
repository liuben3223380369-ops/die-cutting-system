<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api/client'
import DataTable from '../components/DataTable.vue'
import StatusBadge from '../components/StatusBadge.vue'

const inspections = ref<any[]>([])
const issues = ref<any[]>([])
const traceResult = ref<any>(null)
const costResult = ref<any>(null)
const error = ref('')
const msg = ref('')
const loading = ref(false)

const inspForm = ref({
  inspect_type: 'IPQC',
  result: 'PASSED',
  qty_inspected: 100,
  qty_passed: 100,
  qty_failed: 0,
  inspect_date: new Date().toISOString().slice(0, 10),
  work_order_id: 0,
  material_id: 0,
  batch_no: '',
})

const traceForm = ref({ material_id: 1, batch_no: '', source_type: 'PRODUCTION_IN', source_id: '' })
const costWoId = ref(1)

async function load() {
  loading.value = true
  try {
    const [ins, iss] = await Promise.all([
      api.get<any[]>('/quality/inspections'),
      api.get<any[]>('/quality/issues'),
    ])
    inspections.value = ins
    issues.value = iss
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function submitInsp() {
  try {
    const body: any = { ...inspForm.value }
    if (!body.work_order_id) delete body.work_order_id
    if (!body.material_id) delete body.material_id
    await api.post('/quality/inspections', body)
    msg.value = '检验记录已保存'
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

async function createIssue() {
  try {
    await api.post('/quality/issues', {
      issue_type: 'DEFECT',
      qty: inspForm.value.qty_failed || 1,
      material_id: inspForm.value.material_id || null,
      work_order_id: inspForm.value.work_order_id || null,
      batch_no: inspForm.value.batch_no,
      description: '前端快速登记',
    })
    msg.value = '质量异常单已创建'
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

async function dispose(id: number, disposition: string) {
  try {
    await api.post(`/quality/issues/${id}/dispose`, { disposition })
    msg.value = `已处置: ${disposition}`
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

async function forward() {
  try {
    traceResult.value = await api.post('/quality/trace/forward', {
      material_id: traceForm.value.material_id,
      batch_no: traceForm.value.batch_no,
    })
  } catch (e: any) {
    error.value = e.message
  }
}

async function reverse() {
  try {
    traceResult.value = await api.post('/quality/trace/reverse', {
      source_type: traceForm.value.source_type,
      source_id: traceForm.value.source_id,
    })
  } catch (e: any) {
    error.value = e.message
  }
}

async function calcCost() {
  try {
    costResult.value = await api.post(`/costing/work-orders/${costWoId.value}/calculate`)
    msg.value = '成本已计算'
  } catch (e: any) {
    error.value = e.message
  }
}

onMounted(load)
</script>

<template>
  <div>
    <h2 class="page-title">质量 / 追溯 / 成本</h2>
    <div v-if="error" class="error-box">{{ error }}</div>
    <div v-if="msg" class="ok-box">{{ msg }}</div>

    <div class="card">
      <h3>IPQC / FQC 检验</h3>
      <div class="form-grid">
        <label>类型
          <select v-model="inspForm.inspect_type">
            <option value="IPQC">IPQC</option>
            <option value="FQC">FQC</option>
          </select>
        </label>
        <label>结果
          <select v-model="inspForm.result">
            <option value="PASSED">合格</option>
            <option value="FAILED">不合格</option>
            <option value="PARTIAL">部分</option>
          </select>
        </label>
        <label>检验数 <input type="number" v-model.number="inspForm.qty_inspected" /></label>
        <label>合格 <input type="number" v-model.number="inspForm.qty_passed" /></label>
        <label>不合格 <input type="number" v-model.number="inspForm.qty_failed" /></label>
        <label>工单ID <input type="number" v-model.number="inspForm.work_order_id" /></label>
        <label>物料ID <input type="number" v-model.number="inspForm.material_id" /></label>
        <label>批次 <input v-model="inspForm.batch_no" /></label>
      </div>
      <button class="btn primary" @click="submitInsp">提交检验</button>
      <button class="btn" @click="createIssue">登记异常单</button>
    </div>

    <div class="card">
      <h3>检验记录</h3>
      <DataTable
        :columns="[
          { key: 'doc_no', label: '单号' },
          { key: 'inspect_type', label: '类型' },
          { key: 'result', label: '结果' },
          { key: 'qty_passed', label: '合格' },
          { key: 'qty_failed', label: '不合格' },
          { key: 'work_order_id', label: '工单' },
        ]"
        :rows="inspections"
        :loading="loading"
      >
        <template #result="{ row }">
          <StatusBadge :status="String(row.result)" />
        </template>
      </DataTable>
    </div>

    <div class="card">
      <h3>质量异常</h3>
      <DataTable
        :columns="[
          { key: 'doc_no', label: '单号' },
          { key: 'status', label: '状态' },
          { key: 'qty', label: '数量' },
          { key: 'disposition', label: '处置' },
          { key: 'actions', label: '操作' },
        ]"
        :rows="issues.map(i => ({ ...i, actions: i.id }))"
      >
        <template #status="{ row }">
          <StatusBadge :status="String(row.status)" />
        </template>
        <template #actions="{ row }">
          <template v-if="row.status === 'OPEN'">
            <button class="btn sm" @click="dispose(Number(row.id), 'REWORK')">返工</button>
            <button class="btn sm" @click="dispose(Number(row.id), 'SCRAP')">报废</button>
            <button class="btn sm" @click="dispose(Number(row.id), 'USE_AS_IS')">让步</button>
          </template>
        </template>
      </DataTable>
    </div>

    <div class="card">
      <h3>追溯</h3>
      <div class="form-grid">
        <label>物料ID <input type="number" v-model.number="traceForm.material_id" /></label>
        <label>批次 <input v-model="traceForm.batch_no" /></label>
        <label>反向来源类型 <input v-model="traceForm.source_type" placeholder="PRODUCTION_IN" /></label>
        <label>反向来源单号 <input v-model="traceForm.source_id" placeholder="WO..." /></label>
      </div>
      <button class="btn primary" @click="forward">正向追溯</button>
      <button class="btn" @click="reverse">反向追溯</button>
      <pre v-if="traceResult" class="json">{{ JSON.stringify(traceResult, null, 2) }}</pre>
    </div>

    <div class="card">
      <h3>工单成本</h3>
      <div class="form-grid">
        <label>工单ID <input type="number" v-model.number="costWoId" /></label>
      </div>
      <button class="btn primary" @click="calcCost">计算实际成本</button>
      <div v-if="costResult" class="cost-box">
        <p>材料成本：{{ costResult.material_cost }}</p>
        <p>报废成本：{{ costResult.scrap_cost }}</p>
        <p>总成本：{{ costResult.total_cost }}</p>
        <p>完工数量：{{ costResult.completed_qty }}</p>
        <p>单位成本：{{ costResult.unit_cost }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-title { margin: 0 0 1rem; font-size: 1.25rem; color: #1e3a5f; }
.card { background: #fff; border-radius: 10px; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,.06); margin-bottom: 1rem; }
.card h3 { margin: 0 0 0.75rem; font-size: 0.95rem; color: #64748b; }
.form-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 0.75rem; margin-bottom: 0.75rem; }
label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.8rem; color: #64748b; }
input, select { padding: 0.45rem 0.6rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.875rem; }
.btn { padding: 0.45rem 1rem; border: none; border-radius: 6px; font-size: 0.875rem; cursor: pointer; background: #e2e8f0; margin-right: 0.35rem; }
.btn.primary { background: #1e3a5f; color: #fff; }
.btn.sm { padding: 0.25rem 0.5rem; font-size: 0.75rem; background: #dbeafe; color: #1d4ed8; }
.error-box { background: #fef2f2; color: #b91c1c; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
.ok-box { background: #ecfdf5; color: #065f46; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
.json { background: #f8fafc; padding: 0.75rem; border-radius: 6px; font-size: 0.75rem; overflow: auto; max-height: 240px; }
.cost-box { margin-top: 0.75rem; font-size: 0.9rem; line-height: 1.6; }
</style>
