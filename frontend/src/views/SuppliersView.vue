<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api, type Supplier } from '../api/client'
import DataTable from '../components/DataTable.vue'

const rows = ref<Supplier[]>([])
const loading = ref(true)
const error = ref('')
const showForm = ref(false)
const form = ref({ code: '', name: '', contact: '', phone: '' })
const saving = ref(false)

const columns = [
  { key: 'code', label: '编码' },
  { key: 'name', label: '名称' },
  { key: 'contact', label: '联系人' },
  { key: 'phone', label: '电话' },
]

async function load() {
  loading.value = true
  try {
    rows.value = await api.get<Supplier[]>('/master/suppliers')
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function submit() {
  saving.value = true
  try {
    await api.post('/master/suppliers', form.value)
    showForm.value = false
    form.value = { code: '', name: '', contact: '', phone: '' }
    await load()
  } catch (e: any) {
    error.value = e.message
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="toolbar">
      <h2 class="page-title">供应商</h2>
      <button class="btn primary" @click="showForm = !showForm">{{ showForm ? '取消' : '+ 新增' }}</button>
    </div>
    <div v-if="error" class="error-box">{{ error }}</div>
    <div v-if="showForm" class="card form-card">
      <div class="form-grid">
        <label>编码 <input v-model="form.code" /></label>
        <label>名称 <input v-model="form.name" /></label>
        <label>联系人 <input v-model="form.contact" /></label>
        <label>电话 <input v-model="form.phone" /></label>
      </div>
      <button class="btn primary" :disabled="saving" @click="submit">保存</button>
    </div>
    <div class="card">
      <DataTable :columns="columns" :rows="rows as any" :loading="loading" />
    </div>
  </div>
</template>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.page-title { margin: 0; font-size: 1.25rem; color: #1e3a5f; }
.card { background: #fff; border-radius: 10px; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,.06); margin-bottom: 1rem; }
.form-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; margin-bottom: 1rem; }
label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.8rem; color: #64748b; }
input { padding: 0.45rem 0.6rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.875rem; }
.btn { padding: 0.45rem 1rem; border: none; border-radius: 6px; font-size: 0.875rem; cursor: pointer; background: #e2e8f0; }
.btn.primary { background: #1e3a5f; color: #fff; }
.error-box { background: #fef2f2; color: #b91c1c; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
</style>
