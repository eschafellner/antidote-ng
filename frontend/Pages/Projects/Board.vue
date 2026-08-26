<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
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
const focusedIssueKey = ref(null);

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

const allIssues = computed(() => {
  const list = [];
  columnConfigs.forEach(col => {
    (columns.value[col.id] || []).forEach(item => {
      list.push(item);
    });
  });
  return list;
});

const totalIssuesCount = computed(() => allIssues.value.length);

/**
 * Handle Drag and Drop card movement with optimistic UI update and rollback.
 */
const onCardMove = (targetStatus, evt) => {
  if (evt.added || evt.moved) {
    const item = evt.added ? evt.added.element : evt.moved.element;
    const newIndex = evt.added ? evt.added.newIndex : evt.moved.newIndex;

    const rollbackSnapshot = JSON.parse(JSON.stringify(columns.value));

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
          columns.value = rollbackSnapshot;
        },
      }
    );
  }
};

/**
 * Handle accessible status change (from keyboard or dropdown menu)
 */
const handleDirectStatusChange = ({ issue, newStatus }) => {
  if (issue.status === newStatus) return;

  const rollbackSnapshot = JSON.parse(JSON.stringify(columns.value));

  // Optimistically remove from old column
  const oldCol = columns.value[issue.status] || [];
  columns.value[issue.status] = oldCol.filter(i => i.key !== issue.key);

  // Add to new column
  const updatedIssue = { ...issue, status: newStatus };
  if (!columns.value[newStatus]) columns.value[newStatus] = [];
  columns.value[newStatus].push(updatedIssue);

  router.post(
    `/projects/${props.project.slug}/issues/${issue.key}/move/`,
    {
      status: newStatus,
      position: columns.value[newStatus].length - 1,
    },
    {
      preserveScroll: true,
      preserveState: true,
      onError: () => {
        columns.value = rollbackSnapshot;
      },
    }
  );
};

// Keyboard Navigation (J / K / Enter / S)
const handleBoardKeyDown = e => {
  const target = e.target;
  const isInput =
    target.tagName === 'INPUT' ||
    target.tagName === 'TEXTAREA' ||
    target.tagName === 'SELECT' ||
    target.isContentEditable;

  if (isInput || showCreateModal.value) return;

  const items = allIssues.value;
  if (!items.length) return;

  const currentIndex = items.findIndex(i => i.key === focusedIssueKey.value);

  if (e.key === 'j' || e.key === 'J' || e.key === 'ArrowDown') {
    e.preventDefault();
    const nextIndex = currentIndex < items.length - 1 ? currentIndex + 1 : 0;
    focusedIssueKey.value = items[nextIndex].key;
  } else if (e.key === 'k' || e.key === 'K' || e.key === 'ArrowUp') {
    e.preventDefault();
    const prevIndex = currentIndex > 0 ? currentIndex - 1 : items.length - 1;
    focusedIssueKey.value = items[prevIndex].key;
  } else if (e.key === 'Enter' && focusedIssueKey.value) {
    e.preventDefault();
    router.visit(`/projects/${props.project.slug}/issues/${focusedIssueKey.value}/`);
  } else if ((e.key === 's' || e.key === 'S') && focusedIssueKey.value) {
    e.preventDefault();
    const currentItem = items.find(i => i.key === focusedIssueKey.value);
    if (currentItem) {
      const statusOrder = ['todo', 'in_progress', 'review', 'done', 'canceled'];
      const nextStatusIndex = (statusOrder.indexOf(currentItem.status) + 1) % statusOrder.length;
      handleDirectStatusChange({ issue: currentItem, newStatus: statusOrder[nextStatusIndex] });
    }
  }
};

onMounted(() => {
  window.addEventListener('keydown', handleBoardKeyDown);
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleBoardKeyDown);
});
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

      <!-- Board Empty State (when 0 issues across all columns) -->
      <div
        v-if="totalIssuesCount === 0"
        class="mb-6 p-8 bg-white border border-indigo-100 rounded-2xl shadow-xs text-center flex flex-col items-center max-w-xl mx-auto"
      >
        <div class="w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center mb-3">
          <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v3m0 0v3m0-3h3m-3 0H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h3 class="text-base font-bold text-slate-900 mb-1">Your board is empty</h3>
        <p class="text-xs text-slate-500 mb-4 max-w-sm">
          Get started by creating your first issue. Press <kbd class="px-1.5 py-0.5 bg-slate-100 border border-slate-300 rounded font-mono text-[10px] text-slate-800 font-semibold">C</kbd> anywhere or click below.
        </p>
        <button
          v-if="project.can_create_issue !== false"
          type="button"
          class="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-white bg-indigo-600 rounded-xl shadow-sm hover:bg-indigo-700 transition-colors"
          @click="openCreateForStatus('todo')"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4" />
          </svg>
          Create First Issue
        </button>
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
              <IssueCard
                :issue="element"
                :project-slug="project.slug"
                :is-focused="focusedIssueKey === element.key"
                @status-change="handleDirectStatusChange"
              />
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
