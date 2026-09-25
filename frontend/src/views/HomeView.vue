<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api, type HealthData } from '../api/client'
import StatusBadge from '../components/StatusBadge.vue'
import { useRouter } from '../router'

const health = ref<HealthData | null>(null)
const daily = ref<any>(null)
const error = ref('')
const loading = ref(true)
const { push } = useRouter()

const metricLabels: Record<string, string> = {
  purchase_receipt_qty: '今日采购入库',
  production_issue_qty: '今日生产领料',
  production_in_qty: '今日生产入库',
  stock_total_qty: '库存总量',
  open_quality_issues: '未关闭异常',
  po_created_count: '今日新建PO',
}

onMounted(async () => {
  try {
    const [h, d] = await Promise.all([
      api.get<HealthData>('/health'),
      api.get('/reports/daily').catch(() => null),
    ])
    health.value = h
    daily.value = d
  } catch (e: any) {
    error.value = e.message || '无法连接后端'
  } finally {
    loading.value = false
  }
})

function metricEntries() {
  if (!daily.value?.metrics) return []
  return Object.entries(metricLabels).map(([k, label]) => ({
    label,
    value: daily.value.metrics[k] ?? '—',
  }))
}
</script>

<template>
  <div>
    <h2 class="page-title">系统总览</h2>

    <div class="grid">
      <div class="card">
        <h3>后端状态</h3>
        <div v-if="loading" class="muted">检查中...</div>
        <div v-else-if="error" class="error-box">{{ error }}</div>
        <div v-else-if="health" class="status-list">
          <p><span class="label">应用</span> {{ health.app_name }} v{{ health.version }}</p>
          <p><span class="label">状态</span> <StatusBadge :status="health.status" /></p>
          <p><span class="label">环境</span> {{ health.environment }}</p>
          <p><span class="label">数据库</span> {{ health.database }}</p>
        </div>
      </div>

      <div class="card">
        <h3>首版进度</h3>
        <ul class="phases">
          <li class="done">阶段0 · 技术底座</li>
          <li class="done">阶段1 · 采购库存核心</li>
          <li class="done">阶段2 · 模切工程</li>
          <li class="done">阶段3 · MRP计划</li>
          <li class="done">阶段4 · 完整生产</li>
          <li class="done">阶段5 · 质量成本追溯</li>
          <li class="done">阶段6 · 统计Excel</li>
          <li class="done">阶段7 · 稳定化</li>
        </ul>
      </div>

      <div class="card full">
        <h3>今日关键指标</h3>
        <div v-if="daily" class="metrics">
          <div v-for="m in metricEntries()" :key="m.label" class="metric">
            <div class="m-label">{{ m.label }}</div>
            <div class="m-value">{{ m.value }}</div>
          </div>
        </div>
        <p v-else class="muted">暂无报表数据（可先运行 seed_demo_data.py）</p>
      </div>

      <div class="card full">
        <h3>快捷入口</h3>
        <div class="quick-links">
          <button class="ql" @click="push('mrp')">销售/MRP</button>
          <button class="ql" @click="push('board')">生产看板</button>
          <button class="ql" @click="push('workOrders')">生产工单</button>
          <button class="ql" @click="push('orders')">采购订单</button>
          <button class="ql" @click="push('returns')">采购退货</button>
          <button class="ql" @click="push('prices')">价格历史</button>
          <button class="ql" @click="push('arrivals')">到货/IQC</button>
          <button class="ql" @click="push('balances')">库存余额</button>
          <button class="ql" @click="push('adjust')">盘点/调拨</button>
          <button class="ql" @click="push('reports')">统计报表</button>
          <button class="ql" @click="push('products')">产品/BOM</button>
          <button class="ql" @click="push('quality')">质量追溯</button>
        </div>
      </div>

      <div class="card full">
        <h3>推荐操作路径</h3>
        <ol class="steps">
          <li>主数据：物料 / 仓库 / 供应商</li>
          <li>工程：产品 → 版本 → BOM + 工艺 → <strong>发布</strong></li>
          <li>采购：入库原料（或运行种子脚本写入库存）</li>
          <li>计划：销售订单 → 确认 → 跑 MRP</li>
          <li>生产：工单 → 下达 → 领料 → 报工 → 成品入库 → 完工</li>
          <li>质量：检验 / 异常 / 正反向追溯 / 工单成本</li>
          <li>统计：日报与 Excel 导出</li>
        </ol>
      </div>

      <div class="card full">
        <h3>核心原则</h3>
        <div class="principles">
          <span>库存唯一事实源</span>
          <span>历史不可覆盖</span>
          <span>版本冻结</span>
          <span>来源可追溯</span>
          <span>事务原子性</span>
          <span>期间锁定</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-title { margin: 0 0 1.25rem; font-size: 1.25rem; color: #1e3a5f; }
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}
.card {
  background: #fff;
  border-radius: 10px;
  padding: 1.25rem;
  box-shadow: 0 1px 3px rgba(0,0,0,.06);
}
.card.full { grid-column: 1 / -1; }
.card h3 { margin: 0 0 0.75rem; font-size: 0.95rem; color: #64748b; }
.status-list p { margin: 0.4rem 0; font-size: 0.9rem; }
.label { display: inline-block; width: 4rem; color: #94a3b8; }
.phases { list-style: none; padding: 0; margin: 0; }
.phases li {
  padding: 0.35rem 0;
  font-size: 0.875rem;
  color: #94a3b8;
  border-bottom: 1px solid #f1f5f9;
}
.phases li.done { color: #15803d; }
.phases li.done::before { content: "✓ "; }
.principles { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.principles span {
  background: #eff6ff;
  color: #1d4ed8;
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  font-size: 0.8rem;
}
.metrics {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 0.75rem;
}
.metric {
  background: #f8fafc;
  border-radius: 8px;
  padding: 0.75rem;
  border: 1px solid #e2e8f0;
}
.m-label { font-size: 0.75rem; color: #64748b; }
.m-value { font-size: 1.1rem; font-weight: 600; color: #1e3a5f; margin-top: 0.25rem; }
.steps { margin: 0; padding-left: 1.25rem; font-size: 0.875rem; color: #475569; line-height: 1.7; }
.muted { color: #94a3b8; font-size: 0.875rem; }
.quick-links { display: flex; flex-wrap: wrap; gap: 0.5rem; }
.ql { padding: 0.5rem 0.9rem; border: 1px solid #e2e8f0; border-radius: 8px; background: #f8fafc; cursor: pointer; font-size: 0.85rem; color: #1e3a5f; }
.ql:hover { background: #eff6ff; border-color: #93c5fd; }
.error-box { background: #fef2f2; color: #b91c1c; padding: 0.75rem; border-radius: 6px; font-size: 0.875rem; }
@media (max-width: 720px) {
  .grid { grid-template-columns: 1fr; }
}
</style>
