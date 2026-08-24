<script setup>
import { ref, watch } from 'vue';
import { Head, Link, router } from '@inertiajs/vue3';
import AppLayout from '@/Components/AppLayout.vue';
import IssueStatusBadge from '@/Components/IssueStatusBadge.vue';
import IssuePriorityBadge from '@/Components/IssuePriorityBadge.vue';
import IssueTypeBadge from '@/Components/IssueTypeBadge.vue';
import UserAvatar from '@/Components/UserAvatar.vue';
import CreateIssueModal from '@/Components/CreateIssueModal.vue';

const props = defineProps({
  project: {
    type: Object,
    required: true,
  },
  issues: {
    type: Array,
    default: () => [],
  },
  pagination: {
    type: Object,
    required: true,
  },
  filters: {
    type: Object,
    default: () => ({}),
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

const search = ref(props.filters.search || '');
const status = ref(props.filters.status || '');
const priority = ref(props.filters.priority || '');
const type = ref(props.filters.type || '');
const assignee = ref(props.filters.assignee_id !== null && props.filters.assignee_id !== undefined ? String(props.filters.assignee_id) : '');

const showCreateModal = ref(false);

const applyFilters = (page = 1) => {
  router.get(
    `/projects/${props.project.slug}/issues/`,
    {
      search: search.value || undefined,
      status: status.value || undefined,
      priority: priority.value || undefined,
      type: type.value || undefined,
      assignee: assignee.value !== '' ? assignee.value : undefined,
      page: page > 1 ? page : undefined,
    },
    {
      preserveState: true,
      preserveScroll: true,
    }
  );
};

const resetFilters = () => {
  search.value = '';
  status.value = '';
  priority.value = '';
  type.value = '';
  assignee.value = '';
  applyFilters(1);
};
</script>

<template>
  <AppLayout :project="project" :members="members">
    <Head :title="`${project.name} - Issues Backlog`" />

    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 w-full space-y-6">
      <!-- Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 class="text-xl font-bold text-slate-900 tracking-tight">
            Issue List & Backlog
          </h1>
          <p class="text-xs text-slate-500 mt-0.5">
            Filter, search, and manage project issues.
          </p>
        </div>

        <button
          v-if="project.can_create_issue !== false"
          type="button"
          class="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-indigo-600 rounded-lg shadow-xs hover:bg-indigo-700 transition-colors self-start sm:self-auto"
          @click="showCreateModal = true"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4" />
          </svg>
          Create Issue
        </button>
      </div>

      <!-- Filter Controls Bar -->
      <div class="bg-white p-4 sm:p-5 rounded-2xl border border-slate-200/80 shadow-xs space-y-3.5">
        <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3.5">
          <!-- Text Search -->
          <div class="md:col-span-2">
            <div class="relative">
              <input
                v-model="search"
                type="text"
                placeholder="Search issues by key, title, description..."
                class="w-full pl-10 pr-4 py-2 text-sm rounded-xl border-slate-300 shadow-xs focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 placeholder:text-slate-400 bg-white"
                @keyup.enter="applyFilters(1)"
              />
              <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
            </div>
          </div>

          <!-- Status Filter -->
          <div>
            <select
              v-model="status"
              class="w-full py-2 px-3 text-sm rounded-xl border-slate-300 shadow-xs focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 bg-white"
              @change="applyFilters(1)"
            >
              <option value="">All Statuses</option>
              <option v-for="s in statuses" :key="s.value" :value="s.value">
                {{ s.label }}
              </option>
            </select>
          </div>

          <!-- Priority Filter -->
          <div>
            <select
              v-model="priority"
              class="w-full py-2 px-3 text-sm rounded-xl border-slate-300 shadow-xs focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 bg-white"
              @change="applyFilters(1)"
            >
              <option value="">All Priorities</option>
              <option v-for="p in priorities" :key="p.value" :value="p.value">
                {{ p.label }}
              </option>
            </select>
          </div>

          <!-- Assignee Filter -->
          <div>
            <select
              v-model="assignee"
              class="w-full py-2 px-3 text-sm rounded-xl border-slate-300 shadow-xs focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 bg-white"
              @change="applyFilters(1)"
            >
              <option value="">All Assignees</option>
              <option value="0">Unassigned</option>
              <option v-for="m in members" :key="m.user_id" :value="m.user_id">
                {{ m.first_name && m.last_name ? `${m.first_name} ${m.last_name}` : m.username }}
              </option>
            </select>
          </div>
        </div>


        <div class="flex items-center justify-between pt-2 border-t border-slate-100 text-xs">
          <span class="text-slate-500 font-medium">
            Found {{ pagination.total_items }} issues
          </span>
          <div class="flex items-center gap-2">
            <button
              type="button"
              class="text-indigo-600 hover:text-indigo-700 font-semibold transition-colors"
              @click="applyFilters(1)"
            >
              Apply Filters
            </button>
            <span class="text-slate-300">|</span>
            <button
              type="button"
              class="text-slate-400 hover:text-slate-600 transition-colors"
              @click="resetFilters"
            >
              Reset
            </button>
          </div>
        </div>
      </div>

      <!-- Issues Table -->
      <div class="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200">
            <thead class="bg-slate-50 text-slate-500 text-[11px] font-bold uppercase tracking-wider text-left">
              <tr>
                <th scope="col" class="py-3 pl-4 pr-3 sm:pl-6">Key</th>
                <th scope="col" class="px-3 py-3">Type</th>
                <th scope="col" class="px-3 py-3">Title</th>
                <th scope="col" class="px-3 py-3">Status</th>
                <th scope="col" class="px-3 py-3">Priority</th>
                <th scope="col" class="px-3 py-3">Assignee</th>
                <th scope="col" class="px-3 py-3">Due Date</th>
                <th scope="col" class="relative py-3 pl-3 pr-4 sm:pr-6"><span class="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs text-slate-700">
              <tr
                v-for="item in issues"
                :key="item.id"
                class="hover:bg-slate-50/80 transition-colors group cursor-pointer"
                @click="router.get(`/projects/${project.slug}/issues/${item.key}/`)"
              >
                <!-- Key -->
                <td class="py-3.5 pl-4 pr-3 sm:pl-6 font-mono font-bold text-indigo-600 whitespace-nowrap">
                  <Link :href="`/projects/${project.slug}/issues/${item.key}/`" class="hover:underline">
                    {{ item.key }}
                  </Link>
                </td>

                <!-- Type -->
                <td class="px-3 py-3.5 whitespace-nowrap">
                  <IssueTypeBadge :type="item.type" />
                </td>

                <!-- Title -->
                <td class="px-3 py-3.5 font-medium text-slate-900 max-w-md truncate group-hover:text-indigo-600 transition-colors">
                  {{ item.title }}
                </td>

                <!-- Status -->
                <td class="px-3 py-3.5 whitespace-nowrap">
                  <IssueStatusBadge :status="item.status" />
                </td>

                <!-- Priority -->
                <td class="px-3 py-3.5 whitespace-nowrap">
                  <IssuePriorityBadge :priority="item.priority" />
                </td>

                <!-- Assignee -->
                <td class="px-3 py-3.5 whitespace-nowrap">
                  <div class="flex items-center gap-2">
                    <UserAvatar :user="item.assignee" size="sm" />
                    <span class="text-slate-600">
                      {{ item.assignee?.username || 'Unassigned' }}
                    </span>
                  </div>
                </td>

                <!-- Due Date -->
                <td class="px-3 py-3.5 whitespace-nowrap text-slate-500">
                  {{ item.due_date || '—' }}
                </td>

                <!-- Arrow Action -->
                <td class="py-3.5 pl-3 pr-4 sm:pr-6 text-right font-medium text-slate-400 group-hover:text-slate-600 whitespace-nowrap">
                  &rarr;
                </td>
              </tr>

              <!-- Empty State -->
              <tr v-if="issues.length === 0">
                <td colspan="8" class="py-12 text-center text-slate-400">
                  <p class="text-sm font-medium">No issues found matching your filters.</p>
                  <button
                    type="button"
                    class="mt-2 text-xs font-semibold text-indigo-600 hover:text-indigo-700"
                    @click="resetFilters"
                  >
                    Clear all filters
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Server-side Pagination Bar -->
        <div
          v-if="pagination.total_pages > 1"
          class="flex items-center justify-between px-6 py-3 border-t border-slate-100 bg-slate-50/50 text-xs text-slate-600"
        >
          <span>
            Page {{ pagination.current_page }} of {{ pagination.total_pages }}
          </span>

          <div class="flex items-center gap-2">
            <button
              :disabled="!pagination.has_previous"
              class="px-3 py-1.5 rounded border border-slate-300 bg-white font-medium hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              @click="applyFilters(pagination.current_page - 1)"
            >
              Previous
            </button>
            <button
              :disabled="!pagination.has_next"
              class="px-3 py-1.5 rounded border border-slate-300 bg-white font-medium hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              @click="applyFilters(pagination.current_page + 1)"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Issue Modal -->
    <CreateIssueModal
      :show="showCreateModal"
      :project-slug="project.slug"
      :members="members"
      @close="showCreateModal = false"
    />
  </AppLayout>
</template>
