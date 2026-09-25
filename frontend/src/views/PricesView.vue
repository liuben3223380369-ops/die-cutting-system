<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api/client'
import DataTable from '../components/DataTable.vue'

interface PriceRow {
  id: number
  supplier_id: number
  material_id: number
  unit_price: number
  currency: string
  effective_date: string
  source_type?: string
  source_id?: string
}

const rows = ref<PriceRow[]>([])
const suppliers = ref<Array<{ id: number; code: string; name: string }>>([])
const materials = ref<Array<{ id: number; code: string; name: string }>>([])
const supplierId = ref(0)
const materialId = ref(0)
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const q = new URLSearchParams()
    if (supplierId.value) q.set('supplier_id', String(supplierId.value))
    if (materialId.value) q.set('material_id', String(materialId.value))
    const [prices, sups, mats] = await Promise.all([
      api.get<PriceRow[]>(`/purchase/price-history?${q}`),
      api.get<Array<{ id: number; code: string; name: string }>>('/master/suppliers'),
      api.get<Array<{ id: number; code: string; name: string }>>('/master/materials'),
    ])
    rows.value = prices
    suppliers.value = sups
    materials.value = mats
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function supName(id: number) {
  return suppliers.value.find(s => s.id === id)?.name || `#${id}`
}
function matCode(id: number) {
  return materials.value.find(m => m.id === id)?.code || `#${id}`
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <h2 class="page-title">采购价格历史</h2>
    </div>
    <div v-if="error" class="error-box">{{ error }}</div>
    <div class="card filters">
      <label>供应商
        <select v-model.number="supplierId" @change="load">
          <option :value="0">全部</option>
          <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.code }} {{ s.name }}</option>
        </select>
      </label>
      <label>物料
        <select v-model.number="materialId" @change="load">
          <option :value="0">全部</option>
          <option v-for="m in materials" :key="m.id" :value="m.id">{{ m.code }} {{ m.name }}</option>
        </select>
      </label>
      <button class="btn" @click="load">查询</button>
    </div>
    <div class="card">
      <DataTable
        :columns="[
          { key: 'effective_date', label: '生效日' },
          { key: 'supplier', label: '供应商' },
          { key: 'material', label: '物料' },
          { key: 'unit_price', label: '单价' },
          { key: 'currency', label: '币种' },
          { key: 'source_type', label: '来源' },
          { key: 'source_id', label: '来源单号' },
        ]"
        :rows="rows.map(r => ({
          ...r,
          supplier: supName(r.supplier_id),
          material: matCode(r.material_id),
        })) as any"
        :loading="loading"
      />
      <p class="tip">确认采购订单时会自动写入价格历史，供比价与追溯。</p>
    </div>
  </div>
</template>

<style scoped>
.toolbar { margin-bottom: 1rem; }
.page-title { margin: 0; font-size: 1.25rem; color: #1e3a5f; }
.card { background: #fff; border-radius: 10px; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,.06); margin-bottom: 1rem; }
.filters { display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: flex-end; }
label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.8rem; color: #64748b; }
select { padding: 0.45rem 0.6rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.875rem; min-width: 140px; }
.btn { padding: 0.45rem 1rem; border: none; border-radius: 6px; background: #e2e8f0; cursor: pointer; }
.error-box { background: #fef2f2; color: #b91c1c; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
.tip { font-size: 0.8rem; color: #94a3b8; margin: 0.75rem 0 0; }
</style>
