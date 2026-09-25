<script setup lang="ts">
defineProps<{
  columns: Array<{ key: string; label: string; width?: string }>
  rows: Array<Record<string, unknown>>
  loading?: boolean
  emptyText?: string
}>()
</script>

<template>
  <div class="table-wrap">
    <div v-if="loading" class="hint">加载中...</div>
    <div v-else-if="!rows.length" class="hint">{{ emptyText || '暂无数据' }}</div>
    <table v-else class="table">
      <thead>
        <tr>
          <th v-for="col in columns" :key="col.key" :style="col.width ? { width: col.width } : {}">
            {{ col.label }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, idx) in rows" :key="idx">
          <td v-for="col in columns" :key="col.key">
            <slot :name="col.key" :row="row">{{ row[col.key] ?? '—' }}</slot>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.table-wrap {
  overflow-x: auto;
}
.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}
.table th,
.table td {
  padding: 0.6rem 0.75rem;
  text-align: left;
  border-bottom: 1px solid #e5e7eb;
}
.table th {
  background: #f8fafc;
  font-weight: 600;
  color: #475569;
  white-space: nowrap;
}
.table tbody tr:hover {
  background: #f1f5f9;
}
.hint {
  padding: 2rem;
  text-align: center;
  color: #94a3b8;
}
</style>
