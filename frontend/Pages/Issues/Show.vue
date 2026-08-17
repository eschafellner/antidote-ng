<script setup>
import { Head, Link } from '@inertiajs/vue3';
import AppLayout from '@/Components/AppLayout.vue';
import IssueDetailSlideOver from '@/Components/IssueDetailSlideOver.vue';

const props = defineProps({
  detail: {
    type: Object,
    required: true,
  },
  members: {
    type: Array,
    default: () => [],
  },
  statuses: {
    type: Array,
    default: () => [],
  },
  types: {
    type: Array,
    default: () => [],
  },
  priorities: {
    type: Array,
    default: () => [],
  },
});
</script>

<template>
  <AppLayout :project="detail.issue.project" :members="members">
    <Head :title="`${detail.issue.key}: ${detail.issue.title}`" />

    <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full space-y-4">
      <!-- Breadcrumb Navigation -->
      <div class="flex items-center gap-2 text-xs text-slate-500">
        <Link :href="`/projects/${detail.issue.project.slug}/board/`" class="hover:text-indigo-600 font-medium">
          &larr; Back to Kanban Board
        </Link>
      </div>

      <!-- Embedded Issue Detail View -->
      <IssueDetailSlideOver
        :detail="detail"
        :members="members"
        :statuses="statuses"
        :types="types"
        :priorities="priorities"
        :is-slide-over="false"
      />
    </div>
  </AppLayout>
</template>
