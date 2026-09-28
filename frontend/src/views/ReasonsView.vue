<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { api } from '../api/client'
import DataTable from '../components/DataTable.vue'

interface Reason {
  id: number
  category: string
  code: string
  name: string
  is_active: boolean
}

const rows = ref<Reason[]>([])
const loading = ref(true)
const error = ref('')
const msg = ref('')
const categoryFilter = ref('')
const showForm = ref(false)
const form = ref({ category: 'REVERSAL', code: '', name: '' })

const categories = ['REVERSAL', 'ADJUST', 'SCRAP', 'QC_FAIL', 'RETURN', 'OTHER']

const filtered = computed(() =>
  categoryFilter.value
    ? rows.value.filter(r => r.category === categoryFilter.value)
    : rows.value
)

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await api.get<Reason[]>('/master/reason-codes')
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function submit() {
  try {
    await api.post('/master/reason-codes', form.value)
    showForm.value = false
    form.value = { category: form.value.category, code: '', name: '' }
    msg.value = '原因码已保存'
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

async function seedDefaults() {
  const defaults = [
    { category: 'REVERSAL', code: 'ERROR', name: '录单错误' },
    { category: 'REVERSAL', code: 'DUPLICATE', name: '重复入账' },
    { category: 'REVERSAL', code: 'QTY_WRONG', name: '数量有误' },
    { category: 'REVERSAL', code: 'BATCH_WRONG', name: '批次有误' },
    { category: 'REVERSAL', code: 'OTHER', name: '其他' },
    { category: 'ADJUST', code: 'COUNT', name: '盘点差异' },
    { category: 'QC_FAIL', code: 'DEFECT', name: '检验不合格' },
    { category: 'RETURN', code: 'VENDOR', name: '供应商退货' },
  ]
  let n = 0
  for (const d of defaults) {
    try {
      await api.post('/master/reason-codes', d)
      n++
    } catch {
      /* already exists */
    }
  }
  msg.value = `已尝试写入默认原因码（新增约 ${n} 条）`
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <h2 class="page-title">原因码</h2>
      <div>
        <button class="btn" @click="seedDefaults">灌入默认</button>
        <button class="btn primary" @click="showForm = !showForm">{{ showForm ? '取消' : '+ 新增' }}</button>
      </div>
    </div>
    <div v-if="error" class="error-box">{{ error }}</div>
    <div v-if="msg" class="ok-box">{{ msg }}</div>

    <div v-if="showForm" class="card form-card">
      <div class="form-grid">
        <label>类别
          <select v-model="form.category">
            <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
          </select>
        </label>
        <label>编码 <input v-model="form.code" placeholder="ERROR" /></label>
        <label>名称 <input v-model="form.name" placeholder="录单错误" /></label>
      </div>
      <button class="btn primary" @click="submit">保存</button>
    </div>

    <div class="card">
      <select v-model="categoryFilter" class="filter">
        <option value="">全部类别</option>
        <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
      </select>
      <DataTable
        :columns="[
          { key: 'category', label: '类别' },
          { key: 'code', label: '编码' },
          { key: 'name', label: '名称' },
          { key: 'is_active', label: '启用' },
        ]"
        :rows="filtered as any"
        :loading="loading"
      />
    </div>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.5rem; }
.page-title { margin: 0; font-size: 1.25rem; color: #1e3a5f; }
.card { background: #fff; border-radius: 10px; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,.06); margin-bottom: 1rem; }
.form-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 0.75rem; margin-bottom: 0.75rem; }
label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.8rem; color: #64748b; }
input, select, .filter { padding: 0.45rem 0.6rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.875rem; margin-bottom: 0.75rem; }
.btn { padding: 0.45rem 1rem; border: none; border-radius: 6px; background: #e2e8f0; cursor: pointer; margin-right: 0.35rem; font-size: 0.875rem; }
.btn.primary { background: #1e3a5f; color: #fff; }
.error-box { background: #fef2f2; color: #b91c1c; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
.ok-box { background: #ecfdf5; color: #065f46; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
</style>
