<script setup>
import { computed } from 'vue';

const props = defineProps({
  priority: {
    type: String,
    required: true,
  },
  showLabel: {
    type: Boolean,
    default: true,
  },
});

const config = computed(() => {
  switch (props.priority) {
    case 'urgent':
      return { label: 'Urgent', class: 'text-red-700 bg-red-50 border-red-200' };
    case 'high':
      return { label: 'High', class: 'text-orange-700 bg-orange-50 border-orange-200' };
    case 'medium':
      return { label: 'Medium', class: 'text-amber-700 bg-amber-50 border-amber-200' };
    case 'low':
    default:
      return { label: 'Low', class: 'text-slate-600 bg-slate-100 border-slate-200' };
  }
});
</script>

<template>
  <span
    :class="[
      'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium border',
      config.class,
    ]"
    :title="`Priority: ${config.label}`"
  >
    <!-- Priority indicator dots / icons -->
    <span v-if="priority === 'urgent'" class="w-1.5 h-1.5 rounded-full bg-red-600 animate-pulse"></span>
    <span v-else-if="priority === 'high'" class="w-1.5 h-1.5 rounded-full bg-orange-500"></span>
    <span v-else-if="priority === 'medium'" class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
    <span v-else class="w-1.5 h-1.5 rounded-full bg-slate-400"></span>

    <span v-if="showLabel">{{ config.label }}</span>
  </span>
</template>
