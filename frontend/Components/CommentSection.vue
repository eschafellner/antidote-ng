<script setup>
import { ref } from 'vue';
import { useForm, router } from '@inertiajs/vue3';
import UserAvatar from './UserAvatar.vue';
import MarkdownViewer from './MarkdownViewer.vue';
import MarkdownEditor from './MarkdownEditor.vue';

const props = defineProps({
  projectSlug: {
    type: String,
    required: true,
  },
  issueKey: {
    type: String,
    required: true,
  },
  comments: {
    type: Array,
    default: () => [],
  },
  canComment: {
    type: Boolean,
    default: true,
  },
});

const newComment = ref('');
const isSubmitting = ref(false);
const editingCommentId = ref(null);
const editContent = ref('');

const addComment = () => {
  if (!newComment.value.trim()) return;
  isSubmitting.value = true;

  router.post(
    `/projects/${props.projectSlug}/issues/${props.issueKey}/comments/`,
    { content: newComment.value },
    {
      preserveScroll: true,
      onSuccess: () => {
        newComment.value = '';
        isSubmitting.value = false;
      },
      onFinish: () => {
        isSubmitting.value = false;
      },
    }
  );
};

const startEdit = comment => {
  editingCommentId.value = comment.id;
  editContent.value = comment.content;
};

const cancelEdit = () => {
  editingCommentId.value = null;
  editContent.value = '';
};

const saveEdit = commentId => {
  if (!editContent.value.trim()) return;

  router.post(
    `/projects/${props.projectSlug}/issues/${props.issueKey}/comments/${commentId}/update/`,
    { content: editContent.value },
    {
      preserveScroll: true,
      onSuccess: () => {
        editingCommentId.value = null;
        editContent.value = '';
      },
    }
  );
};

const deleteComment = commentId => {
  if (confirm('Are you sure you want to delete this comment?')) {
    router.post(
      `/projects/${props.projectSlug}/issues/${props.issueKey}/comments/${commentId}/delete/`,
      {},
      { preserveScroll: true }
    );
  }
};

const formatDate = dateStr => {
  const date = new Date(dateStr);
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};
</script>

<template>
  <div class="space-y-6">
    <!-- Comments List -->
    <div v-if="comments.length > 0" class="space-y-4">
      <div
        v-for="c in comments"
        :key="c.id"
        class="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs space-y-3"
      >
        <!-- Comment Header -->
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2.5">
            <UserAvatar :user="c.author" size="sm" />
            <div>
              <span class="text-xs font-bold text-slate-900">
                {{ c.author.first_name && c.author.last_name ? `${c.author.first_name} ${c.author.last_name}` : c.author.username }}
              </span>
              <span class="text-[11px] text-slate-400 ml-2">
                {{ formatDate(c.created_at) }}
              </span>
              <span v-if="c.is_edited" class="text-[10px] text-slate-400 italic ml-1">
                (edited)
              </span>
            </div>
          </div>

          <!-- Actions -->
          <div v-if="editingCommentId !== c.id" class="flex items-center gap-2 text-xs">
            <button
              v-if="c.can_edit"
              type="button"
              class="text-slate-400 hover:text-slate-600 font-medium"
              @click="startEdit(c)"
            >
              Edit
            </button>
            <button
              v-if="c.can_delete"
              type="button"
              class="text-slate-400 hover:text-rose-600 font-medium"
              @click="deleteComment(c.id)"
            >
              Delete
            </button>
          </div>
        </div>

        <!-- Comment Content (Viewer or Editor mode) -->
        <div v-if="editingCommentId === c.id" class="space-y-3 pt-1">
          <MarkdownEditor v-model="editContent" :rows="3" />
          <div class="flex items-center justify-end gap-2 text-xs">
            <button
              type="button"
              class="px-3 py-1.5 rounded-lg border border-slate-300 font-medium text-slate-700 hover:bg-slate-50"
              @click="cancelEdit"
            >
              Cancel
            </button>
            <button
              type="button"
              class="px-3 py-1.5 rounded-lg bg-indigo-600 font-semibold text-white hover:bg-indigo-700"
              @click="saveEdit(c.id)"
            >
              Save Changes
            </button>
          </div>
        </div>
        <div v-else class="text-xs text-slate-800">
          <MarkdownViewer :content="c.content" />
        </div>
      </div>
    </div>

    <!-- Empty Comments State -->
    <div v-else class="text-xs text-slate-400 italic py-2">
      No comments on this issue yet.
    </div>

    <!-- New Comment Box -->
    <div v-if="canComment" class="space-y-3 pt-2">
      <h4 class="text-xs font-bold uppercase tracking-wider text-slate-600">
        Leave a Comment
      </h4>
      <MarkdownEditor v-model="newComment" :rows="3" placeholder="Write markdown comment..." />

      <div class="flex justify-end">
        <button
          type="button"
          :disabled="!newComment.trim() || isSubmitting"
          class="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 rounded-lg shadow-sm hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          @click="addComment"
        >
          {{ isSubmitting ? 'Posting...' : 'Comment' }}
        </button>
      </div>
    </div>
  </div>
</template>
