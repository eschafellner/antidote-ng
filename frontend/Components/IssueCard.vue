<script setup>
import { ref, computed } from 'vue';
import { Link, router } from '@inertiajs/vue3';
import UserAvatar from './UserAvatar.vue';
import IssuePriorityBadge from './IssuePriorityBadge.vue';
import IssueTypeBadge from './IssueTypeBadge.vue';

const props = defineProps({
  issue: {
    type: Object,
    required: true,
  },
  projectSlug: {
    type: String,
    required: true,
  },
  isFocused: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['statusChange']);

const showQuickMenu = ref(false);

const isOverdue = computed(() => {
  if (!props.issue.due_date) return false;
  if (props.issue.status === 'done' || props.issue.status === 'canceled') return false;
  const today = new Date().toISOString().split('T')[0];
  return props.issue.due_date < today;
});

const formattedDueDate = computed(() => {
  if (!props.issue.due_date) return '';
  const date = new Date(props.issue.due_date);
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
});

const statuses = [
  { id: 'todo', label: 'To Do' },
  { id: 'in_progress', label: 'In Progress' },
  { id: 'review', label: 'Review' },
  { id: 'done', label: 'Done' },
  { id: 'canceled', label: 'Canceled' },
];

const changeStatus = newStatus => {
  showQuickMenu.value = false;
  emit('statusChange', { issue: props.issue, newStatus });
};
</script>

<template>
  <div
    :class="[
      'group relative bg-white rounded-lg p-3.5 shadow-sm transition-all duration-150 cursor-grab active:cursor-grabbing border',
      isFocused
        ? 'ring-2 ring-indigo-500 ring-offset-2 border-indigo-400 shadow-md'
        : 'border-slate-200/80 hover:shadow-md hover:border-indigo-300',
    ]"
    tabindex="0"
  >
    <!-- Header: Type, Key, Priority & Quick Status Menu -->
    <div class="flex items-center justify-between gap-2 mb-2">
      <div class="flex items-center gap-1.5 min-w-0">
        <IssueTypeBadge :type="issue.type" />
        <Link
          :href="`/projects/${projectSlug}/issues/${issue.key}/`"
          class="text-xs font-mono font-semibold text-slate-500 hover:text-indigo-600 truncate transition-colors"
          @click.stop
        >
          {{ issue.key }}
        </Link>
      </div>

      <div class="flex items-center gap-1">
        <IssuePriorityBadge :priority="issue.priority" :show-label="false" />

        <!-- Quick Status Dropdown (Accessible / Keyboard fallback) -->
        <div class="relative">
          <button
            type="button"
            class="p-1 rounded text-slate-300 hover:text-slate-600 opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity"
            title="Change status"
            aria-label="Change status"
            @click.stop="showQuickMenu = !showQuickMenu"
          >
            <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
            </svg>
          </button>

          <div
            v-if="showQuickMenu"
            class="origin-top-right absolute right-0 mt-1 w-36 rounded-lg shadow-lg bg-white border border-slate-200 py-1 z-30 text-xs focus:outline-none"
            @click.stop
          >
            <p class="px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-400 border-b border-slate-100">
              Move to:
            </p>
            <button
              v-for="s in statuses"
              :key="s.id"
              type="button"
              :class="[
                'w-full text-left px-2.5 py-1.5 hover:bg-slate-50 flex items-center justify-between',
                issue.status === s.id ? 'font-bold text-indigo-600' : 'text-slate-700',
              ]"
              @click="changeStatus(s.id)"
            >
              <span>{{ s.label }}</span>
              <span v-if="issue.status === s.id" class="text-indigo-600">&check;</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Title -->
    <h4 class="text-sm font-medium text-slate-900 line-clamp-2 mb-3 leading-snug group-hover:text-indigo-600 transition-colors">
      <Link :href="`/projects/${projectSlug}/issues/${issue.key}/`" @click.stop>
        {{ issue.title }}
      </Link>
    </h4>

    <!-- Footer: Due Date & Assignee -->
    <div class="flex items-center justify-between pt-2 border-t border-slate-100 text-xs text-slate-500">
      <div class="flex items-center gap-1">
        <span
          v-if="issue.due_date"
          :class="[
            'inline-flex items-center gap-1 font-medium',
            isOverdue ? 'text-rose-600' : 'text-slate-500',
          ]"
          :title="isOverdue ? 'Overdue!' : 'Due Date'"
        >
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          {{ formattedDueDate }}
        </span>
      </div>

      <div>
        <UserAvatar :user="issue.assignee" size="sm" />
      </div>
    </div>
  </div>
</template>
