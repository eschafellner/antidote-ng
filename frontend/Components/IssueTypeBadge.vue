<script setup>
import { computed } from 'vue';

const props = defineProps({
  type: {
    type: String,
    required: true,
  },
});

const config = computed(() => {
  switch (props.type) {
    case 'bug':
      return { label: 'Bug', color: 'text-rose-600 bg-rose-50 border-rose-200' };
    case 'story':
      return { label: 'Story', color: 'text-emerald-600 bg-emerald-50 border-emerald-200' };
    case 'task':
    default:
      return { label: 'Task', color: 'text-blue-600 bg-blue-50 border-blue-200' };
  }
});
</script>

<template>
  <span
    :class="[
      'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium border uppercase tracking-wider',
      config.color,
    ]"
  >
    <!-- Simple SVGs for type -->
    <svg v-if="type === 'bug'" class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
    <svg v-else-if="type === 'story'" class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
    <svg v-else class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
    </svg>
    <span>{{ config.label }}</span>
  </span>
</template>
