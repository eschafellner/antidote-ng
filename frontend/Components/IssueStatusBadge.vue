<script setup>
import { computed } from 'vue';

const props = defineProps({
  status: {
    type: String,
    required: true,
  },
});

const config = computed(() => {
  switch (props.status) {
    case 'todo':
      return { label: 'To Do', class: 'bg-slate-100 text-slate-700 border-slate-200' };
    case 'in_progress':
      return { label: 'In Progress', class: 'bg-blue-50 text-blue-700 border-blue-200' };
    case 'review':
      return { label: 'Review', class: 'bg-purple-50 text-purple-700 border-purple-200' };
    case 'done':
      return { label: 'Done', class: 'bg-emerald-50 text-emerald-700 border-emerald-200' };
    case 'canceled':
      return { label: 'Canceled', class: 'bg-zinc-100 text-zinc-500 border-zinc-200 line-through' };
    default:
      return { label: props.status, class: 'bg-slate-100 text-slate-600 border-slate-200' };
  }
});
</script>

<template>
  <span
    :class="[
      'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border',
      config.class,
    ]"
  >
    {{ config.label }}
  </span>
</template>
