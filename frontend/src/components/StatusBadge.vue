<script setup lang="ts">
defineProps<{ status: string }>()

const colorMap: Record<string, string> = {
  DRAFT: 'gray',
  SUBMITTED: 'blue',
  APPROVED: 'blue',
  CONFIRMED: 'green',
  PARTIAL: 'orange',
  COMPLETED: 'green',
  CLOSED: 'gray',
  CANCELLED: 'red',
  RECEIVED: 'blue',
  QC_DONE: 'green',
  PENDING: 'orange',
  PASSED: 'green',
  FAILED: 'red',
  ok: 'green',
  degraded: 'orange',
}
</script>

<template>
  <span class="badge" :class="colorMap[status] || 'gray'">{{ status }}</span>
</template>

<style scoped>
.badge {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 500;
}
.badge.gray { background: #f1f5f9; color: #64748b; }
.badge.blue { background: #dbeafe; color: #1d4ed8; }
.badge.green { background: #dcfce7; color: #15803d; }
.badge.orange { background: #ffedd5; color: #c2410c; }
.badge.red { background: #fee2e2; color: #b91c1c; }
</style>
