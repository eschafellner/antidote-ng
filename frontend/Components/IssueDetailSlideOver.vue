<script setup>
import { ref, watch, computed } from 'vue';
import { router } from '@inertiajs/vue3';
import UserAvatar from './UserAvatar.vue';
import IssueStatusBadge from './IssueStatusBadge.vue';
import IssuePriorityBadge from './IssuePriorityBadge.vue';
import IssueTypeBadge from './IssueTypeBadge.vue';
import MarkdownViewer from './MarkdownViewer.vue';
import MarkdownEditor from './MarkdownEditor.vue';
import AttachmentManager from './AttachmentManager.vue';
import CommentSection from './CommentSection.vue';
import ActivityTimeline from './ActivityTimeline.vue';

const props = defineProps({
  show: {
    type: Boolean,
    default: true,
  },
  isSlideOver: {
    type: Boolean,
    default: true,
  },
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
    default: () => [
      { value: 'todo', label: 'To Do' },
      { value: 'in_progress', label: 'In Progress' },
      { value: 'review', label: 'Review' },
      { value: 'done', label: 'Done' },
      { value: 'canceled', label: 'Canceled' },
    ],
  },
  types: {
    type: Array,
    default: () => [
      { value: 'task', label: 'Task' },
      { value: 'bug', label: 'Bug' },
      { value: 'story', label: 'Story' },
    ],
  },
  priorities: {
    type: Array,
    default: () => [
      { value: 'low', label: 'Low' },
      { value: 'medium', label: 'Medium' },
      { value: 'high', label: 'High' },
      { value: 'urgent', label: 'Urgent' },
    ],
  },
});

const emit = defineEmits(['close']);

const issue = computed(() => props.detail.issue);
const permissions = computed(() => props.detail.permissions || {});

// Inline editing states
const isEditingTitle = ref(false);
const editTitle = ref(issue.value.title);

const isEditingDescription = ref(false);
const editDescription = ref(issue.value.description || '');

const activeTab = ref('comments'); // 'comments' | 'attachments' | 'activity'

watch(
  () => issue.value,
  newVal => {
    editTitle.value = newVal.title;
    editDescription.value = newVal.description || '';
  },
  { deep: true }
);

const updateField = (fieldName, value) => {
  const payload = {};
  payload[fieldName] = value;

  router.post(
    `/projects/${issue.value.project.slug}/issues/${issue.value.key}/update/`,
    payload,
    {
      preserveScroll: true,
      preserveState: true,
    }
  );
};

const saveTitle = () => {
  if (editTitle.value.trim() && editTitle.value !== issue.value.title) {
    updateField('title', editTitle.value.trim());
  }
  isEditingTitle.value = false;
};

const saveDescription = () => {
  updateField('description', editDescription.value);
  isEditingDescription.value = false;
};

const cancelDescription = () => {
  editDescription.value = issue.value.description || '';
  isEditingDescription.value = false;
};

const softDeleteIssue = () => {
  if (confirm(`Are you sure you want to delete issue ${issue.value.key}?`)) {
    router.post(
      `/projects/${issue.value.project.slug}/issues/${issue.value.key}/delete/`,
      {},
      {
        onSuccess: () => {
          emit('close');
        },
      }
    );
  }
};

const restoreIssue = () => {
  router.post(
    `/projects/${issue.value.project.slug}/issues/${issue.value.key}/restore/`,
    {},
    { preserveScroll: true }
  );
};
</script>

<template>
  <div>
    <!-- Backdrop (for slide-over mode) -->
    <div
      v-if="isSlideOver && show"
      class="fixed inset-0 bg-slate-900/40 backdrop-blur-xs z-50 transition-opacity"
      @click="emit('close')"
    ></div>

    <!-- Container / Slide-over Drawer -->
    <div
      :class="[
        isSlideOver
          ? 'fixed inset-y-0 right-0 z-50 w-full max-w-2xl bg-white shadow-2xl border-l border-slate-200 flex flex-col transform transition-transform duration-300'
          : 'w-full bg-white rounded-2xl border border-slate-200 shadow-xs flex flex-col',
        isSlideOver && !show ? 'translate-x-full' : 'translate-x-0',
      ]"
    >
      <!-- Slide-over Top Bar -->
      <div class="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
        <div class="flex items-center gap-2">
          <span class="font-mono text-sm font-bold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-100">
            {{ issue.key }}
          </span>
          <span v-if="issue.is_deleted" class="text-xs font-bold text-rose-700 bg-rose-100 px-2 py-0.5 rounded">
            DELETED
          </span>
        </div>

        <div class="flex items-center gap-2">
          <button
            v-if="issue.is_deleted && permissions.can_delete"
            type="button"
            class="text-xs font-semibold text-emerald-600 hover:text-emerald-700 px-2.5 py-1 rounded bg-emerald-50 border border-emerald-200"
            @click="restoreIssue"
          >
            Restore Issue
          </button>
          <button
            v-else-if="permissions.can_delete"
            type="button"
            class="text-xs font-semibold text-rose-600 hover:text-rose-700 px-2.5 py-1 rounded hover:bg-rose-50"
            title="Soft Delete Issue"
            @click="softDeleteIssue"
          >
            Delete
          </button>

          <button
            v-if="isSlideOver"
            type="button"
            class="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
            @click="emit('close')"
          >
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <!-- Slide-over Scrollable Body -->
      <div class="flex-1 overflow-y-auto p-6 space-y-6">
        <!-- Title (Inline edit) -->
        <div>
          <div v-if="isEditingTitle && permissions.can_edit" class="flex items-center gap-2">
            <input
              v-model="editTitle"
              type="text"
              autofocus
              class="w-full rounded-lg border-indigo-500 font-bold text-lg text-slate-900 focus:ring-indigo-500"
              @keyup.enter="saveTitle"
              @keyup.esc="isEditingTitle = false"
            />
            <button
              type="button"
              class="px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 rounded-lg hover:bg-indigo-700"
              @click="saveTitle"
            >
              Save
            </button>
            <button
              type="button"
              class="px-3 py-1.5 text-xs font-medium text-slate-600 rounded-lg border hover:bg-slate-50"
              @click="isEditingTitle = false"
            >
              Cancel
            </button>
          </div>
          <h1
            v-else
            :class="[
              'text-xl font-bold text-slate-900 tracking-tight leading-snug',
              permissions.can_edit ? 'hover:bg-slate-50 cursor-pointer rounded p-1 -ml-1 transition-colors' : '',
            ]"
            title="Click to edit title"
            @click="permissions.can_edit && (isEditingTitle = true)"
          >
            {{ issue.title }}
          </h1>
        </div>

        <!-- Inline Attributes Grid: Status, Priority, Type, Assignee, Due Date -->
        <div class="bg-slate-50/80 rounded-xl p-4 border border-slate-200/80 grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs">
          <!-- Status -->
          <div>
            <span class="text-slate-400 block font-semibold uppercase text-[10px] tracking-wider mb-1">Status</span>
            <select
              :value="issue.status"
              :disabled="!permissions.can_edit"
              class="w-full py-1 px-2 text-xs font-medium rounded-lg border-slate-300 focus:border-indigo-500 focus:ring-indigo-500 disabled:bg-slate-100 disabled:cursor-not-allowed"
              @change="e => updateField('status', e.target.value)"
            >
              <option v-for="s in statuses" :key="s.value" :value="s.value">
                {{ s.label }}
              </option>
            </select>
          </div>

          <!-- Priority -->
          <div>
            <span class="text-slate-400 block font-semibold uppercase text-[10px] tracking-wider mb-1">Priority</span>
            <select
              :value="issue.priority"
              :disabled="!permissions.can_edit"
              class="w-full py-1 px-2 text-xs font-medium rounded-lg border-slate-300 focus:border-indigo-500 focus:ring-indigo-500 disabled:bg-slate-100 disabled:cursor-not-allowed"
              @change="e => updateField('priority', e.target.value)"
            >
              <option v-for="p in priorities" :key="p.value" :value="p.value">
                {{ p.label }}
              </option>
            </select>
          </div>

          <!-- Type -->
          <div>
            <span class="text-slate-400 block font-semibold uppercase text-[10px] tracking-wider mb-1">Type</span>
            <select
              :value="issue.type"
              :disabled="!permissions.can_edit"
              class="w-full py-1 px-2 text-xs font-medium rounded-lg border-slate-300 focus:border-indigo-500 focus:ring-indigo-500 disabled:bg-slate-100 disabled:cursor-not-allowed"
              @change="e => updateField('type', e.target.value)"
            >
              <option v-for="t in types" :key="t.value" :value="t.value">
                {{ t.label }}
              </option>
            </select>
          </div>

          <!-- Assignee -->
          <div>
            <span class="text-slate-400 block font-semibold uppercase text-[10px] tracking-wider mb-1">Assignee</span>
            <select
              :value="issue.assignee ? issue.assignee.id : ''"
              :disabled="!permissions.can_edit"
              class="w-full py-1 px-2 text-xs font-medium rounded-lg border-slate-300 focus:border-indigo-500 focus:ring-indigo-500 disabled:bg-slate-100 disabled:cursor-not-allowed"
              @change="e => updateField('assignee_id', e.target.value ? Number(e.target.value) : null)"
            >
              <option value="">Unassigned</option>
              <option v-for="m in members" :key="m.user_id" :value="m.user_id">
                {{ m.first_name && m.last_name ? `${m.first_name} ${m.last_name}` : m.username }}
              </option>
            </select>
          </div>

          <!-- Reporter -->
          <div>
            <span class="text-slate-400 block font-semibold uppercase text-[10px] tracking-wider mb-1">Reporter</span>
            <div class="flex items-center gap-1.5 py-1">
              <UserAvatar :user="issue.reporter" size="sm" />
              <span class="text-slate-700 font-medium">{{ issue.reporter.username }}</span>
            </div>
          </div>

          <!-- Due Date -->
          <div>
            <span class="text-slate-400 block font-semibold uppercase text-[10px] tracking-wider mb-1">Due Date</span>
            <input
              :value="issue.due_date || ''"
              type="date"
              :disabled="!permissions.can_edit"
              class="w-full py-1 px-2 text-xs font-medium rounded-lg border-slate-300 focus:border-indigo-500 focus:ring-indigo-500 disabled:bg-slate-100 disabled:cursor-not-allowed"
              @change="e => updateField('due_date', e.target.value || null)"
            />
          </div>
        </div>

        <!-- Description Section (Markdown Edit & View) -->
        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <h3 class="text-xs font-bold uppercase tracking-wider text-slate-700">
              Description
            </h3>
            <button
              v-if="!isEditingDescription && permissions.can_edit"
              type="button"
              class="text-xs font-semibold text-indigo-600 hover:text-indigo-700"
              @click="isEditingDescription = true"
            >
              Edit
            </button>
          </div>

          <!-- Editor view -->
          <div v-if="isEditingDescription" class="space-y-3">
            <MarkdownEditor v-model="editDescription" :rows="6" />
            <div class="flex items-center justify-end gap-2 text-xs">
              <button
                type="button"
                class="px-3 py-1.5 rounded-lg border border-slate-300 font-medium text-slate-700 hover:bg-slate-50"
                @click="cancelDescription"
              >
                Cancel
              </button>
              <button
                type="button"
                class="px-3 py-1.5 rounded-lg bg-indigo-600 font-semibold text-white hover:bg-indigo-700"
                @click="saveDescription"
              >
                Save Description
              </button>
            </div>
          </div>

          <!-- Viewer view -->
          <div
            v-else
            :class="[
              'rounded-xl p-4 border bg-white min-h-[80px]',
              permissions.can_edit ? 'hover:border-indigo-300 cursor-pointer transition-colors' : '',
            ]"
            @click="permissions.can_edit && (isEditingDescription = true)"
          >
            <MarkdownViewer :content="issue.description" placeholder="Click to add a markdown description..." />
          </div>
        </div>

        <!-- Tabs: Comments / Attachments / Activity Timeline -->
        <div class="space-y-4 pt-4 border-t border-slate-200">
          <div class="flex items-center gap-4 border-b border-slate-200 text-xs font-bold">
            <button
              type="button"
              :class="[
                'pb-2.5 transition-colors border-b-2 flex items-center gap-1.5',
                activeTab === 'comments'
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700',
              ]"
              @click="activeTab = 'comments'"
            >
              Comments
              <span class="px-1.5 py-0.5 rounded-full text-[10px] bg-slate-100 text-slate-600">
                {{ detail.comments?.length || 0 }}
              </span>
            </button>

            <button
              type="button"
              :class="[
                'pb-2.5 transition-colors border-b-2 flex items-center gap-1.5',
                activeTab === 'attachments'
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700',
              ]"
              @click="activeTab = 'attachments'"
            >
              Attachments
              <span class="px-1.5 py-0.5 rounded-full text-[10px] bg-slate-100 text-slate-600">
                {{ detail.attachments?.length || 0 }}
              </span>
            </button>

            <button
              type="button"
              :class="[
                'pb-2.5 transition-colors border-b-2 flex items-center gap-1.5',
                activeTab === 'activity'
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700',
              ]"
              @click="activeTab = 'activity'"
            >
              Activity Log
              <span class="px-1.5 py-0.5 rounded-full text-[10px] bg-slate-100 text-slate-600">
                {{ detail.activity_logs?.length || 0 }}
              </span>
            </button>
          </div>

          <!-- Tab Content -->
          <div v-show="activeTab === 'comments'">
            <CommentSection
              :project-slug="issue.project.slug"
              :issue-key="issue.key"
              :comments="detail.comments"
              :can-comment="permissions.can_comment"
            />
          </div>

          <div v-show="activeTab === 'attachments'">
            <AttachmentManager
              :project-slug="issue.project.slug"
              :issue-key="issue.key"
              :attachments="detail.attachments"
              :can-upload="permissions.can_upload"
            />
          </div>

          <div v-show="activeTab === 'activity'">
            <ActivityTimeline :activities="detail.activity_logs" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
