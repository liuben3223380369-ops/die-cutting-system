<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { api } from '../api/client'

const reportDate = ref(new Date().toISOString().slice(0, 10))
const startDate = ref(new Date().toISOString().slice(0, 10))
const endDate = ref(new Date().toISOString().slice(0, 10))
const daily = ref<any>(null)
const period = ref<any>(null)
const error = ref('')
const loading = ref(false)

const metricLabels: Record<string, string> = {
  purchase_receipt_qty: '采购入库数量',
  production_issue_qty: '生产领料数量',
  production_in_qty: '生产入库数量',
  wo_completed_qty: '工单完工数量',
  iqc_pass_rate_pct: 'IQC 合格率 %',
  open_quality_issues: '未关闭质量异常',
  stock_total_qty: '库存总量',
  po_created_count: '新建采购订单数',
}

const dailyMetrics = computed(() => {
  if (!daily.value?.metrics) return []
  return Object.entries(daily.value.metrics).map(([k, v]) => ({
    key: k,
    label: metricLabels[k] || k,
    value: v ?? '—',
  }))
})

const periodMetrics = computed(() => {
  if (!period.value?.metrics) return []
  return Object.entries(period.value.metrics).map(([k, v]) => ({
    key: k,
    label: metricLabels[k] || k,
    value: v ?? '—',
  }))
})

async function loadDaily() {
  loading.value = true
  error.value = ''
  try {
    daily.value = await api.get(`/reports/daily?report_date=${reportDate.value}`)
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function loadPeriod() {
  loading.value = true
  error.value = ''
  try {
    period.value = await api.get(
      `/reports/period?start_date=${startDate.value}&end_date=${endDate.value}`
    )
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function exportDaily() {
  window.open(`/api/v1/reports/export/daily.xlsx?report_date=${reportDate.value}`, '_blank')
}

function exportLedgers() {
  const q = new URLSearchParams()
  if (startDate.value) q.set('start_date', startDate.value)
  if (endDate.value) q.set('end_date', endDate.value)
  window.open(`/api/v1/reports/export/ledgers.xlsx?${q}`, '_blank')
}

function exportWorkOrders() {
  window.open('/api/v1/reports/export/work-orders.xlsx', '_blank')
}

function exportBalances() {
  window.open('/api/v1/reports/export/balances.xlsx', '_blank')
}

onMounted(loadDaily)
</script>

<template>
  <div>
    <h2 class="page-title">统计报表</h2>
    <div v-if="error" class="error-box">{{ error }}</div>

    <div class="card">
      <h3>日报（统一指标）</h3>
      <div class="form-row">
        <label>日期 <input type="date" v-model="reportDate" /></label>
        <button class="btn primary" :disabled="loading" @click="loadDaily">查询</button>
        <button class="btn" @click="exportDaily">导出 Excel</button>
      </div>
      <div v-if="daily" class="metrics">
        <div v-for="m in dailyMetrics" :key="m.key" class="metric-card">
          <div class="metric-label">{{ m.label }}</div>
          <div class="metric-value">{{ m.value }}</div>
        </div>
      </div>
      <p v-else class="tip">选择日期后查询</p>
    </div>

    <div class="card">
      <h3>自定义区间（与日报同一指标定义）</h3>
      <div class="form-row">
        <label>开始 <input type="date" v-model="startDate" /></label>
        <label>结束 <input type="date" v-model="endDate" /></label>
        <button class="btn primary" :disabled="loading" @click="loadPeriod">查询</button>
        <button class="btn" @click="exportLedgers">导出流水 Excel</button>
        <button class="btn" @click="exportWorkOrders">导出工单 Excel</button>
        <button class="btn" @click="exportBalances">导出余额 Excel</button>
      </div>
      <div v-if="period" class="metrics">
        <div v-for="m in periodMetrics" :key="m.key" class="metric-card">
          <div class="metric-label">{{ m.label }}</div>
          <div class="metric-value">{{ m.value }}</div>
        </div>
      </div>
    </div>

    <div class="card tip-card">
      <h3>口径说明</h3>
      <ul>
        <li>采购入库 / 生产领料 / 生产入库：均来自 <code>stock_ledgers</code>，与页面库存流水一致</li>
        <li>IQC 合格率：期间合格数量 ÷ 检验数量</li>
        <li>库存总量：当前余额汇总（非期间发生额）</li>
        <li>Excel 导出依赖后端 openpyxl</li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.page-title { margin: 0 0 1rem; font-size: 1.25rem; color: #1e3a5f; }
.card { background: #fff; border-radius: 10px; padding: 1.25rem; box-shadow: 0 1px 3px rgba(0,0,0,.06); margin-bottom: 1rem; }
.card h3 { margin: 0 0 0.75rem; font-size: 0.95rem; color: #64748b; }
.form-row { display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: flex-end; margin-bottom: 1rem; }
label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.8rem; color: #64748b; }
input { padding: 0.45rem 0.6rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.875rem; }
.btn { padding: 0.45rem 1rem; border: none; border-radius: 6px; font-size: 0.875rem; cursor: pointer; background: #e2e8f0; }
.btn.primary { background: #1e3a5f; color: #fff; }
.btn:disabled { opacity: 0.6; }
.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 0.75rem;
}
.metric-card {
  background: #f8fafc;
  border-radius: 8px;
  padding: 0.85rem;
  border: 1px solid #e2e8f0;
}
.metric-label { font-size: 0.75rem; color: #64748b; margin-bottom: 0.35rem; }
.metric-value { font-size: 1.15rem; font-weight: 600; color: #1e3a5f; }
.error-box { background: #fef2f2; color: #b91c1c; padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.875rem; }
.tip { color: #94a3b8; font-size: 0.875rem; }
.tip-card ul { margin: 0; padding-left: 1.25rem; font-size: 0.85rem; color: #475569; line-height: 1.6; }
.tip-card code { background: #f1f5f9; padding: 0.1rem 0.35rem; border-radius: 4px; font-size: 0.8rem; }
</style>
