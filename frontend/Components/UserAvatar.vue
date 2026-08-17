<script setup>
import { computed } from 'vue';

const props = defineProps({
  user: {
    type: Object,
    default: null,
  },
  size: {
    type: String,
    default: 'md', // sm, md, lg
  },
});

const initials = computed(() => {
  if (!props.user) return '?';
  if (props.user.first_name && props.user.last_name) {
    return `${props.user.first_name[0]}${props.user.last_name[0]}`.toUpperCase();
  }
  const name = props.user.username || props.user.email || '?';
  return name.substring(0, 2).toUpperCase();
});

const displayName = computed(() => {
  if (!props.user) return 'Unassigned';
  if (props.user.first_name && props.user.last_name) {
    return `${props.user.first_name} ${props.user.last_name}`;
  }
  return props.user.username || props.user.email || 'User';
});

const sizeClasses = computed(() => {
  switch (props.size) {
    case 'sm':
      return 'w-6 h-6 text-xs';
    case 'lg':
      return 'w-10 h-10 text-sm';
    case 'md':
    default:
      return 'w-8 h-8 text-xs';
  }
});

// Deterministic pleasant color background based on name
const bgColorClass = computed(() => {
  const name = displayName.value;
  const colors = [
    'bg-indigo-100 text-indigo-700',
    'bg-emerald-100 text-emerald-700',
    'bg-amber-100 text-amber-700',
    'bg-sky-100 text-sky-700',
    'bg-rose-100 text-rose-700',
    'bg-purple-100 text-purple-700',
    'bg-teal-100 text-teal-700',
  ];
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
});
</script>

<template>
  <div
    v-if="user"
    :class="[
      'inline-flex items-center justify-center font-semibold rounded-full select-none flex-shrink-0',
      sizeClasses,
      bgColorClass,
    ]"
    :title="displayName"
  >
    {{ initials }}
  </div>
  <div
    v-else
    :class="[
      'inline-flex items-center justify-center font-medium rounded-full bg-slate-100 text-slate-400 select-none flex-shrink-0 border border-dashed border-slate-300',
      sizeClasses,
    ]"
    title="Unassigned"
  >
    <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
    </svg>
  </div>
</template>
