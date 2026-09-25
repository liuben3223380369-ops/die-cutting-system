<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter, type RouteName } from './router'
import HomeView from './views/HomeView.vue'
import MaterialsView from './views/MaterialsView.vue'
import SuppliersView from './views/SuppliersView.vue'
import WarehousesView from './views/WarehousesView.vue'
import BalancesView from './views/BalancesView.vue'
import LedgersView from './views/LedgersView.vue'
import AdjustView from './views/AdjustView.vue'
import OrdersView from './views/OrdersView.vue'
import ArrivalsView from './views/ArrivalsView.vue'
import ReturnsView from './views/ReturnsView.vue'
import PricesView from './views/PricesView.vue'
import ProductsView from './views/ProductsView.vue'
import MrpView from './views/MrpView.vue'
import WorkOrdersView from './views/WorkOrdersView.vue'
import BoardView from './views/BoardView.vue'
import QualityView from './views/QualityView.vue'
import ReportsView from './views/ReportsView.vue'
import PeriodsView from './views/PeriodsView.vue'

const { route, meta, push, routes, init } = useRouter()

const viewMap: Record<RouteName, any> = {
  home: HomeView,
  materials: MaterialsView,
  suppliers: SuppliersView,
  warehouses: WarehousesView,
  balances: BalancesView,
  ledgers: LedgersView,
  adjust: AdjustView,
  orders: OrdersView,
  arrivals: ArrivalsView,
  returns: ReturnsView,
  prices: PricesView,
  products: ProductsView,
  mrp: MrpView,
  workOrders: WorkOrdersView,
  board: BoardView,
  quality: QualityView,
  reports: ReportsView,
  periods: PeriodsView,
}

const currentView = computed(() => viewMap[route.value])

const navGroups = computed(() => {
  const groups: Record<string, Array<{ name: RouteName; title: string }>> = {}
  for (const [name, info] of Object.entries(routes)) {
    if (!groups[info.group]) groups[info.group] = []
    groups[info.group].push({ name: name as RouteName, title: info.title })
  }
  return groups
})

onMounted(init)
</script>

<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand">
        <div class="logo">模切</div>
        <div>
          <div class="brand-title">模切流程系统</div>
          <div class="brand-sub">首版 · 非ERP</div>
        </div>
      </div>
      <nav>
        <div v-for="(items, group) in navGroups" :key="group" class="nav-group">
          <div class="nav-label">{{ group }}</div>
          <a
            v-for="item in items"
            :key="item.name"
            href="javascript:;"
            class="nav-item"
            :class="{ active: route === item.name }"
            @click="push(item.name)"
          >{{ item.title }}</a>
        </div>
      </nav>
    </aside>

    <div class="main-area">
      <header class="topbar">
        <span class="breadcrumb">{{ meta.group }} / {{ meta.title }}</span>
      </header>
      <main class="content">
        <component :is="currentView" />
      </main>
    </div>
  </div>
</template>

<style scoped>
.layout {
  display: flex;
  min-height: 100vh;
  background: #f1f5f9;
}
.sidebar {
  width: 220px;
  background: #1e3a5f;
  color: #fff;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
}
.brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1.25rem 1rem;
  border-bottom: 1px solid rgba(255,255,255,.1);
}
.logo {
  width: 36px;
  height: 36px;
  background: #3b82f6;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.8rem;
}
.brand-title { font-weight: 600; font-size: 0.95rem; }
.brand-sub { font-size: 0.7rem; opacity: 0.7; }
.nav-group { padding: 0.75rem 0 0.25rem; }
.nav-label {
  padding: 0.25rem 1rem;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  opacity: 0.5;
}
.nav-item {
  display: block;
  padding: 0.5rem 1rem;
  color: rgba(255,255,255,.8);
  text-decoration: none;
  font-size: 0.875rem;
  transition: background 0.15s;
}
.nav-item:hover { background: rgba(255,255,255,.08); color: #fff; }
.nav-item.active {
  background: rgba(59,130,246,.35);
  color: #fff;
  border-right: 3px solid #60a5fa;
}
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.topbar {
  background: #fff;
  padding: 0.85rem 1.5rem;
  border-bottom: 1px solid #e2e8f0;
  font-size: 0.875rem;
  color: #64748b;
}
.content {
  flex: 1;
  padding: 1.25rem 1.5rem;
  overflow: auto;
}
@media (max-width: 768px) {
  .sidebar { width: 180px; }
}
</style>
