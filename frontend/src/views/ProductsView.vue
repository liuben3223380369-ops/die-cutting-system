<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api/client'
import DataTable from '../components/DataTable.vue'
import StatusBadge from '../components/StatusBadge.vue'

interface Product {
  id: number
  code: string
  name: string
  customer_part_no?: string
  is_active: boolean
}
interface ProductVersion {
  id: number
  product_id: number
  version_code: string
  status: string
  drawing_no?: string
  released_at?: string
}

const products = ref<Product[]>([])
const versions = ref<ProductVersion[]>([])
const loading = ref(true)
const error = ref('')
const msg = ref('')

const showProduct = ref(false)
const showVersion = ref(false)
const productForm = ref({ code: '', name: '', customer_part_no: '' })
const versionForm = ref({ product_id: 0, version_code: 'V1', drawing_no: '' })

// BOM / Route 简易
const showBom = ref(false)
const bomVersionId = ref(0)
const bomMaterialId = ref(0)
const bomQty = ref(1)
const materials = ref<Array<{ id: number; code: string; name: string }>>([])

const showRoute = ref(false)
const routeVersionId = ref(0)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [ps, vs, mats] = await Promise.all([
      api.get<Product[]>('/engineering/products'),
      api.get<ProductVersion[]>('/engineering/versions'),
      api.get<Array<{ id: number; code: string; name: string }>>('/master/materials'),
    ])
    products.value = ps
    versions.value = vs
    materials.value = mats
    if (ps.length && !versionForm.value.product_id) versionForm.value.product_id = ps[0].id
    if (mats.length) bomMaterialId.value = mats[0].id
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function createProduct() {
  try {
    await api.post('/engineering/products', productForm.value)
    showProduct.value = false
    productForm.value = { code: '', name: '', customer_part_no: '' }
    msg.value = '产品已创建'
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

async function createVersion() {
  try {
    await api.post('/engineering/versions', versionForm.value)
    showVersion.value = false
    msg.value = '版本已创建（草稿）'
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

async function releaseVersion(id: number) {
  try {
    await api.post(`/engineering/versions/${id}/release`)
    msg.value = '版本已发布（冻结）'
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

function openBom(versionId: number) {
  bomVersionId.value = versionId
  showBom.value = true
}

async function saveBom() {
  try {
    await api.post('/engineering/bom', {
      product_version_id: bomVersionId.value,
      lines: [{ material_id: bomMaterialId.value, qty_per: bomQty.value, scrap_rate: 0.05 }],
    })
    showBom.value = false
    msg.value = 'BOM 已保存'
  } catch (e: any) {
    error.value = e.message
  }
}

function openRoute(versionId: number) {
  routeVersionId.value = versionId
  showRoute.value = true
}

async function saveRoute() {
  try {
    await api.post('/engineering/routes', {
      product_version_id: routeVersionId.value,
      steps: [
        { seq: 10, step_code: 'SLIT', step_name: '分条', step_type: 'SLITTING' },
        { seq: 20, step_code: 'LAM', step_name: '贴合', step_type: 'LAMINATING' },
        { seq: 30, step_code: 'DIE', step_name: '模切', step_type: 'DIE_CUTTING' },
        { seq: 40, step_code: 'WASTE', step_name: '排废', step_type: 'WASTE' },
      ],
    })
    showRoute.value = false
    msg.value = '工艺路线已保存（分条→贴合→模切→排废）'
  } catch (e: any) {
    error.value = e.message
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <h2 class="page-title">产品 / 版本 / BOM / 工艺</h2>
      <div>
        <button class="btn primary" @click="showProduct = !showProduct">+ 产品</button>
        <button class="btn" @click="showVersion = !showVersion">+ 版本</button>
      </div>
    </div>
    <div v-if="error" class="error-box">{{ error }}</div>
    <div v-if="msg" class="ok-box">{{ msg }}</div>

    <div v-if="showProduct" class="card form-card">
      <div class="form-grid">
        <label>编码 <input v-model="productForm.code" /></label>
        <label>名称 <input v-model="productForm.name" /></label>
        <label>客户料号 <input v-model="productForm.customer_part_no" /></label>
      </div>
      <button class="btn primary" @click="createProduct">保存产品</button>
    </div>

    <div v-if="showVersion" class="card form-card">
      <div class="form-grid">
        <label>产品
          <select v-model.number="versionForm.product_id">
            <option v-for="p in products" :key="p.id" :value="p.id">{{ p.code }} {{ p.name }}</option>
          </select>
        </label>
        <label>版本号 <input v-model="versionForm.version_code" /></label>
        <label>图纸号 <input v-model="versionForm.drawing_no" /></label>
      </div>
      <button class="btn primary" @click="createVersion">创建版本</button>
    </div>

    <div v-if="showBom" class="card form-card">
      <h3>维护 BOM（版本 {{ bomVersionId }}）</h3>
      <div class="form-grid">
        <label>材料
          <select v-model.number="bomMaterialId">
            <option v-for="m in materials" :key="m.id" :value="m.id">{{ m.code }} {{ m.name }}</option>
          </select>
        </label>
        <label>单位用量 <input type="number" v-model.number="bomQty" step="0.001" /></label>
      </div>
      <button class="btn primary" @click="saveBom">保存 BOM</button>
      <button class="btn" @click="showBom = false">取消</button>
    </div>

    <div v-if="showRoute" class="card form-card">
      <h3>维护工艺（版本 {{ routeVersionId }}）</h3>
      <p class="tip">将写入标准模切工序：分条 → 贴合 → 模切 → 排废</p>
      <button class="btn primary" @click="saveRoute">保存工艺路线</button>
      <button class="btn" @click="showRoute = false">取消</button>
    </div>

    <div class="card">
      <h3>产品列表</h3>
      <DataTable
        :columns="[
          { key: 'code', label: '编码' },
          { key: 'name', label: '名称' },
          { key: 'customer_part_no', label: '客户料号' },
        ]"
        :rows="products as any"
        :loading="loading"
      />
    </div>

    <div class="card">
      <h3>版本列表</h3>
      <DataTable
        :columns="[
          { key: 'id', label: 'ID' },
          { key: 'product_id', label: '产品' },
          { key: 'version_code', label: '版本' },
          { key: 'status', label: '状态' },
          { key: 'drawing_no', label: '图纸' },
          { key: 'actions', label: '操作' },
        ]"
        :rows="versions.map(v => ({ ...v, actions: v.id })) as any"
        :loading="loading"
      >
        <template #status="{ row }">
          <StatusBadge :status="String(row.status)" />
        </template>
        <template #actions="{ row }">
          <template v-if="row.status === 'DRAFT'">
            <button class="btn sm" @click="openBom(Number(row.id))">BOM</button>
            <button class="btn sm" @click="openRoute(Number(row.id))">工艺</button>
            <button class="btn sm green" @click="releaseVersion(Number(row.id))">发布</button>
          </template>
          <span v-else class="muted">已冻结</span>
        </template>
      </DataTable>
    </div>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.5rem; }
.page-title { margin: 0; font-size: 1.25rem; color: #1e3a5f; }
.card { background: #fff; border-radius: 10px; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,.06); margin-bottom: 1rem; }
.card h3 { margin: 0 0 0.75rem; font-size: 0.95rem; color: #64748b; }
.form-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 0.75rem; margin-bottom: 1rem; }
label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.8rem; color: #64748b; }
input, select { padding: 0.45rem 0.6rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.875rem; }
.btn { padding: 0.45rem 1rem; border: none; border-radius: 6px; font-size: 0.875rem; cursor: pointer; background: #e2e8f0; margin-right: 0.35rem; }
.btn.primary { background: #1e3a5f; color: #fff; }
.btn.sm { padding: 0.25rem 0.5rem; font-size: 0.75rem; background: #dbeafe; color: #1d4ed8; }
.btn.sm.green { background: #dcfce7; color: #15803d; }
.error-box { background: #fef2f2; color: #b91c1c; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
.ok-box { background: #ecfdf5; color: #065f46; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
.tip { font-size: 0.85rem; color: #64748b; margin: 0 0 0.75rem; }
.muted { color: #94a3b8; font-size: 0.8rem; }
</style>
