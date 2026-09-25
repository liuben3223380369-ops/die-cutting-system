<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api, type Material } from '../api/client'
import DataTable from '../components/DataTable.vue'
import StatusBadge from '../components/StatusBadge.vue'

interface MatSup {
  id: number
  material_id: number
  supplier_id: number
  is_default: boolean
  lead_time_days?: number
}

const rows = ref<Material[]>([])
const suppliers = ref<Array<{ id: number; code: string; name: string }>>([])
const matSups = ref<MatSup[]>([])
const loading = ref(true)
const error = ref('')
const msg = ref('')
const saving = ref(false)
const showForm = ref(false)
const showBind = ref(false)

const form = ref({
  code: '',
  name: '',
  spec: '',
  material_type: 'RAW',
  base_unit: 'PCS',
  is_batch_managed: false,
})

const bindForm = ref({
  material_id: 0,
  supplier_id: 0,
  is_default: true,
  lead_time_days: 7,
})

const columns = [
  { key: 'code', label: '编码' },
  { key: 'name', label: '名称' },
  { key: 'spec', label: '规格' },
  { key: 'material_type', label: '类型' },
  { key: 'base_unit', label: '单位' },
  { key: 'is_active', label: '状态' },
]

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [mats, sups, ms] = await Promise.all([
      api.get<Material[]>('/master/materials'),
      api.get<Array<{ id: number; code: string; name: string }>>('/master/suppliers'),
      api.get<MatSup[]>('/master/material-suppliers').catch(() => []),
    ])
    rows.value = mats
    suppliers.value = sups
    matSups.value = ms || []
    if (mats.length && !bindForm.value.material_id) bindForm.value.material_id = mats[0].id
    if (sups.length && !bindForm.value.supplier_id) bindForm.value.supplier_id = sups[0].id
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function supplierName(id: number) {
  return suppliers.value.find(s => s.id === id)?.name || `#${id}`
}
function materialCode(id: number) {
  return rows.value.find(m => m.id === id)?.code || `#${id}`
}

async function submit() {
  saving.value = true
  error.value = ''
  try {
    await api.post('/master/materials', form.value)
    showForm.value = false
    form.value = { code: '', name: '', spec: '', material_type: 'RAW', base_unit: 'PCS', is_batch_managed: false }
    msg.value = '物料已保存'
    await load()
  } catch (e: any) {
    error.value = e.message
  } finally {
    saving.value = false
  }
}

async function bindSupplier() {
  try {
    await api.post('/master/material-suppliers', bindForm.value)
    showBind.value = false
    msg.value = '默认供应商已绑定（MRP 拆 PO 将使用）'
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
      <h2 class="page-title">物料主数据</h2>
      <div>
        <button class="btn" @click="showBind = !showBind">绑定默认供应商</button>
        <button class="btn primary" @click="showForm = !showForm">
          {{ showForm ? '取消' : '+ 新增物料' }}
        </button>
      </div>
    </div>

    <div v-if="error" class="error-box">{{ error }}</div>
    <div v-if="msg" class="ok-box">{{ msg }}</div>

    <div v-if="showForm" class="card form-card">
      <div class="form-grid">
        <label>编码 <input v-model="form.code" placeholder="M001" /></label>
        <label>名称 <input v-model="form.name" placeholder="PET膜" /></label>
        <label>规格 <input v-model="form.spec" /></label>
        <label>类型
          <select v-model="form.material_type">
            <option value="RAW">原料</option>
            <option value="SEMI">半成品</option>
            <option value="FG">成品</option>
            <option value="CONSUMABLE">辅料</option>
          </select>
        </label>
        <label>单位 <input v-model="form.base_unit" /></label>
        <label class="check">
          <input type="checkbox" v-model="form.is_batch_managed" /> 批次管理
        </label>
      </div>
      <button class="btn primary" :disabled="saving" @click="submit">保存</button>
    </div>

    <div v-if="showBind" class="card form-card">
      <h3>物料 ↔ 默认供应商</h3>
      <p class="tip">MRP「按默认供应商拆 PO」时使用此处关系；无绑定则落到兜底供应商。</p>
      <div class="form-grid">
        <label>物料
          <select v-model.number="bindForm.material_id">
            <option v-for="m in rows" :key="m.id" :value="m.id">{{ m.code }} {{ m.name }}</option>
          </select>
        </label>
        <label>供应商
          <select v-model.number="bindForm.supplier_id">
            <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.code }} {{ s.name }}</option>
          </select>
        </label>
        <label>交期(天) <input type="number" v-model.number="bindForm.lead_time_days" min="0" /></label>
        <label class="check">
          <input type="checkbox" v-model="bindForm.is_default" /> 设为默认
        </label>
      </div>
      <button class="btn primary" @click="bindSupplier">保存绑定</button>
    </div>

    <div class="card">
      <h3>物料列表</h3>
      <DataTable :columns="columns" :rows="rows as any" :loading="loading">
        <template #is_active="{ row }">
          <StatusBadge :status="row.is_active ? 'ok' : 'CANCELLED'" />
        </template>
      </DataTable>
    </div>

    <div class="card">
      <h3>物料默认供应商</h3>
      <DataTable
        :columns="[
          { key: 'material', label: '物料' },
          { key: 'supplier', label: '供应商' },
          { key: 'is_default', label: '默认' },
          { key: 'lead_time_days', label: '交期天' },
        ]"
        :rows="matSups.map(m => ({
          ...m,
          material: materialCode(m.material_id),
          supplier: supplierName(m.supplier_id),
          is_default: m.is_default ? '是' : '否',
        })) as any"
        :loading="loading"
      />
    </div>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.5rem; }
.page-title { margin: 0; font-size: 1.25rem; color: #1e3a5f; }
.card {
  background: #fff;
  border-radius: 10px;
  padding: 1rem;
  box-shadow: 0 1px 3px rgba(0,0,0,.06);
  margin-bottom: 1rem;
}
.card h3 { margin: 0 0 0.75rem; font-size: 0.95rem; color: #64748b; }
.form-card { margin-bottom: 1rem; }
.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1rem;
}
label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.8rem; color: #64748b; }
label.check { flex-direction: row; align-items: center; gap: 0.5rem; margin-top: 1.2rem; }
input, select {
  padding: 0.45rem 0.6rem;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 0.875rem;
}
.btn {
  padding: 0.45rem 1rem;
  border: none;
  border-radius: 6px;
  font-size: 0.875rem;
  cursor: pointer;
  background: #e2e8f0;
  color: #334155;
  margin-right: 0.35rem;
}
.btn.primary { background: #1e3a5f; color: #fff; }
.btn:disabled { opacity: 0.6; }
.error-box {
  background: #fef2f2; color: #b91c1c;
  padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem;
}
.ok-box {
  background: #ecfdf5; color: #065f46;
  padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem;
}
.tip { font-size: 0.8rem; color: #94a3b8; margin: 0 0 0.75rem; }
</style>
