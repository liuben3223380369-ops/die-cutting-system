<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '../api/client'
import DataTable from '../components/DataTable.vue'
import StatusBadge from '../components/StatusBadge.vue'

interface Period {
  id: number
  year: number
  month: number
  status: string
  locked_at?: string
  locked_by?: string
  remark?: string
}

const rows = ref<Period[]>([])
const loading = ref(true)
const error = ref('')
const msg = ref('')
const year = ref(new Date().getFullYear())
const month = ref(new Date().getMonth() + 1)

async function load() {
  loading.value = true
  error.value = ''
  try {
    rows.value = await api.get<Period[]>(`/periods?year=${year.value}`)
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function lock() {
  try {
    await api.post('/periods/lock', { year: year.value, month: month.value })
    msg.value = `${year.value}-${String(month.value).padStart(2, '0')} 已锁定`
    await load()
  } catch (e: any) {
    error.value = e.message
  }
}

async function unlock() {
  try {
    await api.post('/periods/unlock', { year: year.value, month: month.value })
    msg.value = `${year.value}-${String(month.value).padStart(2, '0')} 已解锁`
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
      <h2 class="page-title">期间结账</h2>
    </div>
    <div v-if="error" class="error-box">{{ error }}</div>
    <div v-if="msg" class="ok-box">{{ msg }}</div>

    <div class="card">
      <p class="tip">锁定后该月禁止库存出入库与冲销。解锁后可继续业务。</p>
      <div class="form-row">
        <label>年 <input type="number" v-model.number="year" min="2020" max="2100" /></label>
        <label>月
          <select v-model.number="month">
            <option v-for="m in 12" :key="m" :value="m">{{ m }} 月</option>
          </select>
        </label>
        <button class="btn primary" @click="lock">锁定</button>
        <button class="btn" @click="unlock">解锁</button>
        <button class="btn" @click="load">刷新列表</button>
      </div>
    </div>

    <div class="card">
      <h3>{{ year }} 年期间状态</h3>
      <DataTable
        :columns="[
          { key: 'year', label: '年' },
          { key: 'month', label: '月' },
          { key: 'status', label: '状态' },
          { key: 'locked_at', label: '锁定时间' },
          { key: 'locked_by', label: '操作人' },
        ]"
        :rows="rows as any"
        :loading="loading"
      >
        <template #status="{ row }">
          <StatusBadge :status="String(row.status)" />
        </template>
      </DataTable>
    </div>
  </div>
</template>

<style scoped>
.toolbar { margin-bottom: 1rem; }
.page-title { margin: 0; font-size: 1.25rem; color: #1e3a5f; }
.card { background: #fff; border-radius: 10px; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,.06); margin-bottom: 1rem; }
.card h3 { margin: 0 0 0.75rem; font-size: 0.95rem; color: #64748b; }
.form-row { display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: flex-end; }
label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.8rem; color: #64748b; }
input, select { padding: 0.45rem 0.6rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.875rem; width: 100px; }
.btn { padding: 0.45rem 1rem; border: none; border-radius: 6px; font-size: 0.875rem; cursor: pointer; background: #e2e8f0; }
.btn.primary { background: #1e3a5f; color: #fff; }
.error-box { background: #fef2f2; color: #b91c1c; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
.ok-box { background: #ecfdf5; color: #065f46; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
.tip { font-size: 0.85rem; color: #64748b; margin: 0 0 0.75rem; }
</style>
