<script setup>
import { ref, watch } from 'vue';
import { Head, router } from '@inertiajs/vue3';
import draggable from 'vuedraggable';
import AppLayout from '@/Components/AppLayout.vue';
import IssueCard from '@/Components/IssueCard.vue';
import CreateIssueModal from '@/Components/CreateIssueModal.vue';

const props = defineProps({
  project: {
    type: Object,
    required: true,
  },
  board: {
    type: Object,
    required: true,
  },
  members: {
    type: Array,
    default: () => [],
  },
});

// Local reactive columns state for optimistic drag and drop
const columns = ref({ ...props.board.columns });

watch(
  () => props.board.columns,
  newCols => {
    columns.value = { ...newCols };
  },
  { deep: true }
);

const showCreateModal = ref(false);
const defaultModalStatus = ref('todo');

const openCreateForStatus = status => {
  defaultModalStatus.value = status;
  showCreateModal.value = true;
};

// Kanban Column Metadata & Styling
const columnConfigs = [
  { id: 'todo', label: 'To Do', border: 'border-slate-300', bg: 'bg-slate-100/60', badge: 'bg-slate-200 text-slate-700' },
  { id: 'in_progress', label: 'In Progress', border: 'border-blue-400', bg: 'bg-blue-50/40', badge: 'bg-blue-100 text-blue-700' },
  { id: 'review', label: 'Review', border: 'border-purple-400', bg: 'bg-purple-50/40', badge: 'bg-purple-100 text-purple-700' },
  { id: 'done', label: 'Done', border: 'border-emerald-400', bg: 'bg-emerald-50/40', badge: 'bg-emerald-100 text-emerald-700' },
  { id: 'canceled', label: 'Canceled', border: 'border-zinc-300', bg: 'bg-zinc-100/40', badge: 'bg-zinc-200 text-zinc-600' },
];

/**
 * Handle Drag and Drop card movement with optimistic UI update and rollback.
 */
const onCardMove = (targetStatus, evt) => {
  // We handle 'added' or 'moved' events from vuedraggable
  if (evt.added || evt.moved) {
    const item = evt.added ? evt.added.element : evt.moved.element;
    const newIndex = evt.added ? evt.added.newIndex : evt.moved.newIndex;

    // Snapshot current state for rollback if server request fails
    const rollbackSnapshot = JSON.parse(JSON.stringify(columns.value));

    // Asynchronously patch movement on backend
    router.post(
      `/projects/${props.project.slug}/issues/${item.key}/move/`,
      {
        status: targetStatus,
        position: newIndex,
      },
      {
        preserveScroll: true,
        preserveState: true,
        onError: () => {
          // Rollback optimistic state
          columns.value = rollbackSnapshot;
        },
      }
    );
  }
};
</script>

<template>
  <AppLayout :project="project" :members="members">
    <Head :title="`${project.name} - Kanban Board`" />

    <div class="flex-1 flex flex-col p-4 sm:p-6 lg:p-8 overflow-hidden max-w-full">
      <!-- Board Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h1 class="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            Kanban Board
          </h1>
          <p class="text-xs text-slate-500 mt-0.5">
            Manage workflow and drag issues across columns.
          </p>
        </div>

        <div class="flex items-center gap-2">
          <button
            v-if="project.can_create_issue !== false"
            type="button"
            class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 rounded-lg shadow-xs hover:bg-indigo-700 transition-colors"
            @click="openCreateForStatus('todo')"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            Add Issue
          </button>
        </div>
      </div>

      <!-- Horizontal Scrollable Kanban Columns Container -->
      <div class="flex-1 flex gap-4 overflow-x-auto pb-4 items-start select-none">
        <div
          v-for="col in columnConfigs"
          :key="col.id"
          :class="[
            'w-72 sm:w-80 flex-shrink-0 flex flex-col max-h-[calc(100vh-12rem)] rounded-xl border p-3 shadow-2xs',
            col.bg,
            col.border,
          ]"
        >
          <!-- Column Header -->
          <div class="flex items-center justify-between mb-3 px-1">
            <div class="flex items-center gap-2">
              <h3 class="text-xs font-bold uppercase tracking-wider text-slate-700">
                {{ col.label }}
              </h3>
              <span
                :class="[
                  'px-2 py-0.5 rounded-full text-xs font-bold font-mono',
                  col.badge,
                ]"
              >
                {{ columns[col.id]?.length || 0 }}
              </span>
            </div>

            <button
              v-if="project.can_create_issue !== false"
              type="button"
              class="text-slate-400 hover:text-slate-700 p-1 rounded-md transition-colors"
              title="Add issue to this column"
              @click="openCreateForStatus(col.id)"
            >
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
              </svg>
            </button>
          </div>

          <!-- Draggable Cards Area -->
          <draggable
            v-model="columns[col.id]"
            group="issues"
            item-key="id"
            ghost-class="opacity-40"
            chosen-class="scale-102"
            drag-class="rotate-1"
            class="flex-1 overflow-y-auto space-y-2.5 min-h-[120px] p-0.5"
            @change="evt => onCardMove(col.id, evt)"
          >
            <template #item="{ element }">
              <IssueCard :issue="element" :project-slug="project.slug" />
            </template>

            <!-- Empty Column State -->
            <template #footer>
              <div
                v-if="!columns[col.id] || columns[col.id].length === 0"
                class="flex flex-col items-center justify-center py-8 text-center text-slate-400 border border-dashed border-slate-300/80 rounded-lg bg-white/40"
              >
                <p class="text-xs font-medium">No issues in {{ col.label }}</p>
                <button
                  v-if="project.can_create_issue !== false"
                  type="button"
                  class="mt-1.5 text-xs text-indigo-600 hover:text-indigo-700 font-semibold"
                  @click="openCreateForStatus(col.id)"
                >
                  + Create one
                </button>
              </div>
            </template>
          </draggable>
        </div>
      </div>
    </div>

    <!-- Quick Create Modal -->
    <CreateIssueModal
      :show="showCreateModal"
      :project-slug="project.slug"
      :members="members"
      :default-status="defaultModalStatus"
      @close="showCreateModal = false"
    />
  </AppLayout>
</template>
