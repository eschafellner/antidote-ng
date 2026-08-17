<script setup>
import { ref, watch } from 'vue';
import { useForm } from '@inertiajs/vue3';

const props = defineProps({
  show: {
    type: Boolean,
    default: false,
  },
  projectSlug: {
    type: String,
    required: true,
  },
  members: {
    type: Array,
    default: () => [],
  },
  defaultStatus: {
    type: String,
    default: 'todo',
  },
});

const emit = defineEmits(['close']);

const form = useForm({
  title: '',
  description: '',
  type: 'task',
  status: props.defaultStatus,
  priority: 'medium',
  assignee_id: '',
  due_date: '',
});

watch(
  () => props.defaultStatus,
  newStatus => {
    form.status = newStatus;
  }
);

const submit = () => {
  form.post(`/projects/${props.projectSlug}/issues/new/`, {
    preserveScroll: true,
    onSuccess: () => {
      form.reset();
      emit('close');
    },
  });
};
</script>

<template>
  <div v-if="show" class="fixed inset-0 z-50 overflow-y-auto" role="dialog" aria-modal="true">
    <!-- Backdrop -->
    <div
      class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm transition-opacity"
      @click="emit('close')"
    ></div>

    <div class="flex min-h-full items-center justify-center p-4 text-center sm:p-0">
      <div
        class="relative transform overflow-hidden rounded-xl bg-white text-left shadow-2xl transition-all sm:my-8 sm:w-full sm:max-w-xl border border-slate-200"
      >
        <!-- Modal Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/50">
          <h3 class="text-base font-semibold text-slate-900">Create New Issue</h3>
          <button
            type="button"
            class="text-slate-400 hover:text-slate-500 rounded-lg p-1 transition-colors"
            @click="emit('close')"
          >
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <!-- Form Body -->
        <form @submit.prevent="submit">
          <div class="px-6 py-5 space-y-4">
            <!-- Title -->
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
                Title <span class="text-rose-500">*</span>
              </label>
              <input
                v-model="form.title"
                type="text"
                required
                placeholder="What needs to be done?"
                class="w-full rounded-lg border-slate-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm placeholder:text-slate-400"
              />
              <p v-if="form.errors.title" class="mt-1 text-xs text-rose-600 font-medium">
                {{ form.errors.title }}
              </p>
            </div>

            <!-- Description (Markdown) -->
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
                Description (Markdown)
              </label>
              <textarea
                v-model="form.description"
                rows="4"
                placeholder="Add detailed context, reproduction steps, or acceptance criteria..."
                class="w-full rounded-lg border-slate-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm placeholder:text-slate-400 font-mono text-xs"
              ></textarea>
              <p v-if="form.errors.description" class="mt-1 text-xs text-rose-600 font-medium">
                {{ form.errors.description }}
              </p>
            </div>

            <!-- Selects Grid: Type, Priority, Status, Assignee -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <!-- Issue Type -->
              <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">Type</label>
                <select
                  v-model="form.type"
                  class="w-full rounded-lg border-slate-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm"
                >
                  <option value="task">Task</option>
                  <option value="bug">Bug</option>
                  <option value="story">Story</option>
                </select>
              </div>

              <!-- Priority -->
              <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">Priority</label>
                <select
                  v-model="form.priority"
                  class="w-full rounded-lg border-slate-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="urgent">Urgent</option>
                </select>
              </div>

              <!-- Status -->
              <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">Status</label>
                <select
                  v-model="form.status"
                  class="w-full rounded-lg border-slate-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm"
                >
                  <option value="todo">To Do</option>
                  <option value="in_progress">In Progress</option>
                  <option value="review">Review</option>
                  <option value="done">Done</option>
                  <option value="canceled">Canceled</option>
                </select>
              </div>

              <!-- Assignee -->
              <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">Assignee</label>
                <select
                  v-model="form.assignee_id"
                  class="w-full rounded-lg border-slate-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm"
                >
                  <option value="">Unassigned</option>
                  <option v-for="m in members" :key="m.user_id" :value="m.user_id">
                    {{ m.first_name && m.last_name ? `${m.first_name} ${m.last_name}` : m.username }}
                  </option>
                </select>
              </div>
            </div>

            <!-- Due Date -->
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">Due Date</label>
              <input
                v-model="form.due_date"
                type="date"
                class="w-full sm:w-1/2 rounded-lg border-slate-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm"
              />
            </div>
          </div>

          <!-- Modal Footer -->
          <div class="px-6 py-4 bg-slate-50 border-t border-slate-100 flex items-center justify-end gap-3 rounded-b-xl">
            <button
              type="button"
              class="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
              @click="emit('close')"
            >
              Cancel
            </button>
            <button
              type="submit"
              :disabled="form.processing"
              class="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-indigo-600 border border-transparent rounded-lg shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 transition-colors"
            >
              <svg
                v-if="form.processing"
                class="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Create Issue
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
