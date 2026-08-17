<script setup>
import { computed } from 'vue';
import { Link } from '@inertiajs/vue3';
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
});

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
</script>

<template>
  <div
    class="group relative bg-white rounded-lg p-3.5 shadow-sm border border-slate-200/80 hover:shadow-md hover:border-indigo-300 transition-all duration-150 cursor-grab active:cursor-grabbing"
  >
    <!-- Header: Type, Key, Priority -->
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

      <IssuePriorityBadge :priority="issue.priority" :show-label="false" />
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
