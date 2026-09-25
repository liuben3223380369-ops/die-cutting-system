/**
 * 轻量 hash 路由（不依赖 vue-router）
 */
import { ref, computed, type Component } from 'vue'

export type RouteName =
  | 'home'
  | 'materials'
  | 'suppliers'
  | 'warehouses'
  | 'balances'
  | 'ledgers'
  | 'adjust'
  | 'orders'
  | 'arrivals'
  | 'returns'
  | 'prices'
  | 'products'
  | 'mrp'
  | 'workOrders'
  | 'quality'
  | 'reports'
  | 'periods'
  | 'board'

const current = ref<RouteName>('home')

const routes: Record<RouteName, { title: string; group: string }> = {
  home: { title: '总览', group: '系统' },
  materials: { title: '物料主数据', group: '基础数据' },
  suppliers: { title: '供应商', group: '基础数据' },
  warehouses: { title: '仓库', group: '基础数据' },
  balances: { title: '库存余额', group: '库存' },
  ledgers: { title: '库存流水', group: '库存' },
  adjust: { title: '盘点/调拨', group: '库存' },
  orders: { title: '采购订单', group: '采购' },
  arrivals: { title: '到货/IQC', group: '采购' },
  returns: { title: '采购退货', group: '采购' },
  prices: { title: '价格历史', group: '采购' },
  products: { title: '产品/BOM/工艺', group: '工程' },
  mrp: { title: '销售订单/MRP', group: '计划' },
  workOrders: { title: '生产工单', group: '生产' },
  board: { title: '生产看板', group: '生产' },
  quality: { title: '质量/追溯/成本', group: '质量' },
  reports: { title: '统计报表', group: '统计' },
  periods: { title: '期间结账', group: '系统' },
}

function parseHash(): RouteName {
  const h = (location.hash.replace(/^#\/?/, '') || 'home') as RouteName
  return h in routes ? h : 'home'
}

export function useRouter() {
  const route = computed(() => current.value)
  const meta = computed(() => routes[current.value])

  function push(name: RouteName) {
    current.value = name
    location.hash = `#/${name}`
  }

  function init() {
    current.value = parseHash()
    window.addEventListener('hashchange', () => {
      current.value = parseHash()
    })
  }

  return { route, meta, push, routes, init }
}

export { routes }
