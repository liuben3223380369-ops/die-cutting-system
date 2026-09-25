<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { api, type Warehouse } from '../api/client'
import DataTable from '../components/DataTable.vue'
import StatusBadge from '../components/StatusBadge.vue'

interface Location {
  id: number
  warehouse_id: number
  code: string
  name?: string
  is_active: boolean
}

const rows = ref<Warehouse[]>([])
const locations = ref<Location[]>([])
const balances = ref<any[]>([])
const loading = ref(true)
const error = ref('')
const msg = ref('')
const showForm = ref(false)
const showLoc = ref(false)
const form = ref({ code: '', name: '', warehouse_type: 'NORMAL' })
const locForm = ref({ warehouse_id: 0, code: '', name: '' })
const saving = ref(false)
const selectedWh = ref(0)

const typeLabel: Record<string, string> = {
  NORMAL: '普通',
  WIP: '在制',
  QC: '质检',
  SCRAP: '报废',
}

const filteredLocs = computed(() =>
  selectedWh.value
    ? locations.value.filter(l => l.warehouse_id === selectedWh.value)
    : locations.value
)

const stockByWh = computed(() => {
  const map: Record<number, number> = {}
  for (const b of balances.value) {
    const id = b.warehouse_id
    map[id] = (map[id] || 0) + Number(b.qty || 0)
  }
  return map
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [whs, locs, bals] = await Promise.all([
      api.get<Warehouse[]>('/master/warehouses'),
      api.get<Location[]>('/master/locations').catch(() => []),
      api.get<any[]>('/inventory/balances').catch(() => []),
    ])
    rows.value = whs
    locations.value = locs || []
    balances.value = bals || []
    if (whs.length && !locForm.value.warehouse_id) {
      locForm.value.warehouse_id = whs[0].id
      selectedWh.value = whs[0].id
    }
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function submit() {
  saving.value = true
  try {
    await api.post('/master/warehouses', form.value)
    showForm.value = false
    form.value = { code: '', name: '', warehouse_type: 'NORMAL' }
    msg.value = '仓库已保存'
    await load()
  } catch (e: any) {
    error.value = e.message
  } finally {
    saving.value = false
  }
}

async function submitLoc() {
  try {
    await api.post('/master/locations', locForm.value)
    showLoc.value = false
    locForm.value = { warehouse_id: locForm.value.warehouse_id, code: '', name: '' }
    msg.value = '库位已保存'
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
      <h2 class="page-title">仓库 / 库位</h2>
      <div>
        <button class="btn" @click="showLoc = !showLoc">+ 库位</button>
        <button class="btn primary" @click="showForm = !showForm">{{ showForm ? '取消' : '+ 仓库' }}</button>
      </div>
    </div>
    <div v-if="error" class="error-box">{{ error }}</div>
    <div v-if="msg" class="ok-box">{{ msg }}</div>

    <div class="summary">
      <div v-for="w in rows" :key="w.id" class="s-card" :class="{ active: selectedWh === w.id }" @click="selectedWh = w.id">
        <span class="code">{{ w.code }}</span>
        <strong>{{ typeLabel[w.warehouse_type] || w.warehouse_type }}</strong>
        <em>库存 Σ {{ (stockByWh[w.id] || 0).toFixed(1) }}</em>
      </div>
    </div>

    <div v-if="showForm" class="card form-card">
      <h3>新增仓库</h3>
      <div class="form-grid">
        <label>编码 <input v-model="form.code" placeholder="WH-RM" /></label>
        <label>名称 <input v-model="form.name" /></label>
        <label>类型
          <select v-model="form.warehouse_type">
            <option value="NORMAL">普通</option>
            <option value="WIP">在制 WIP</option>
            <option value="QC">质检 QC</option>
            <option value="SCRAP">报废 SCRAP</option>
          </select>
        </label>
      </div>
      <button class="btn primary" :disabled="saving" @click="submit">保存</button>
    </div>

    <div v-if="showLoc" class="card form-card">
      <h3>新增库位</h3>
      <div class="form-grid">
        <label>所属仓库
          <select v-model.number="locForm.warehouse_id">
            <option v-for="w in rows" :key="w.id" :value="w.id">{{ w.code }} {{ w.name }}</option>
          </select>
        </label>
        <label>库位编码 <input v-model="locForm.code" placeholder="A-01" /></label>
        <label>名称 <input v-model="locForm.name" /></label>
      </div>
      <button class="btn primary" @click="submitLoc">保存库位</button>
    </div>

    <div class="card">
      <h3>仓库列表</h3>
      <DataTable
        :columns="[
          { key: 'code', label: '编码' },
          { key: 'name', label: '名称' },
          { key: 'warehouse_type', label: '类型' },
          { key: 'stock', label: '库存合计' },
          { key: 'is_active', label: '启用' },
        ]"
        :rows="rows.map(r => ({
          ...r,
          warehouse_type: typeLabel[r.warehouse_type] || r.warehouse_type,
          stock: (stockByWh[r.id] || 0).toFixed(2),
        })) as any"
        :loading="loading"
      >
        <template #is_active="{ row }">
          <StatusBadge :status="row.is_active ? 'ok' : 'CANCELLED'" />
        </template>
      </DataTable>
    </div>

    <div class="card">
      <div class="toolbar-inner">
        <h3>库位</h3>
        <select v-model.number="selectedWh" class="filter">
          <option :value="0">全部仓库</option>
          <option v-for="w in rows" :key="w.id" :value="w.id">{{ w.code }}</option>
        </select>
      </div>
      <DataTable
        :columns="[
          { key: 'warehouse_id', label: '仓库' },
          { key: 'code', label: '库位' },
          { key: 'name', label: '名称' },
          { key: 'is_active', label: '启用' },
        ]"
        :rows="filteredLocs as any"
        :loading="loading"
      />
    </div>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.5rem; }
.toolbar-inner { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; }
.page-title { margin: 0; font-size: 1.25rem; color: #1e3a5f; }
.summary { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 0.6rem; margin-bottom: 1rem; }
.s-card { background: #fff; border-radius: 10px; padding: 0.75rem; box-shadow: 0 1px 3px rgba(0,0,0,.06); cursor: pointer; border: 2px solid transparent; }
.s-card.active { border-color: #3b82f6; background: #eff6ff; }
.s-card .code { display: block; font-size: 0.75rem; color: #64748b; }
.s-card strong { display: block; font-size: 0.9rem; color: #1e3a5f; }
.s-card em { display: block; font-style: normal; font-size: 0.8rem; color: #15803d; margin-top: 0.25rem; }
.card { background: #fff; border-radius: 10px; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,.06); margin-bottom: 1rem; }
.card h3 { margin: 0 0 0.75rem; font-size: 0.95rem; color: #64748b; }
.form-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 0.75rem; margin-bottom: 1rem; }
label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.8rem; color: #64748b; }
input, select, .filter { padding: 0.45rem 0.6rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.875rem; }
.btn { padding: 0.45rem 1rem; border: none; border-radius: 6px; font-size: 0.875rem; cursor: pointer; background: #e2e8f0; margin-right: 0.35rem; }
.btn.primary { background: #1e3a5f; color: #fff; }
.error-box { background: #fef2f2; color: #b91c1c; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
.ok-box { background: #ecfdf5; color: #065f46; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
</style>
