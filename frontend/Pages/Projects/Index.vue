<script setup>
import { ref } from 'vue';
import { Head, Link, useForm } from '@inertiajs/vue3';
import AppLayout from '@/Components/AppLayout.vue';

const props = defineProps({
  projects: {
    type: Array,
    default: () => [],
  },
  errors: {
    type: Object,
    default: () => ({}),
  },
});

const showNewProjectModal = ref(false);

const form = useForm({
  name: '',
  key: '',
  description: '',
});

const createProject = () => {
  form.post('/projects/new/', {
    onSuccess: () => {
      form.reset();
      showNewProjectModal.value = false;
    },
  });
};
</script>

<template>
  <AppLayout>
    <Head title="Projects - Antidote" />

    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full space-y-6">
      <!-- Dashboard Top Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 class="text-2xl font-black text-slate-900 tracking-tight">
            Your Projects
          </h1>
          <p class="text-xs text-slate-500 mt-1">
            Workspaces and issue boards you have access to.
          </p>
        </div>

        <button
          type="button"
          class="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-indigo-600 rounded-lg shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
          @click="showNewProjectModal = true"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4" />
          </svg>
          Create Project
        </button>
      </div>

      <!-- Project Cards Grid -->
      <div v-if="projects.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        <div
          v-for="p in projects"
          :key="p.id"
          class="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs hover:shadow-md hover:border-indigo-300 transition-all flex flex-col justify-between group"
        >
          <div>
            <div class="flex items-center justify-between gap-2 mb-3">
              <span class="font-mono text-xs font-bold px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded border border-indigo-100">
                {{ p.key }}
              </span>
              <span class="text-[11px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-100 text-slate-600">
                {{ p.role }}
              </span>
            </div>

            <h3 class="text-base font-bold text-slate-900 group-hover:text-indigo-600 transition-colors">
              <Link :href="`/projects/${p.slug}/board/`">
                {{ p.name }}
              </Link>
            </h3>

            <p class="text-xs text-slate-500 mt-1 line-clamp-2 min-h-[2rem]">
              {{ p.description || 'No description provided.' }}
            </p>
          </div>

          <div class="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between text-xs">
            <div class="flex items-center gap-3 text-slate-600">
              <span title="Open Issues">
                <strong class="text-slate-900 font-semibold">{{ p.open_issues }}</strong> open
              </span>
              <span class="text-slate-300">•</span>
              <span title="Total Issues">
                <strong class="text-slate-900 font-semibold">{{ p.total_issues }}</strong> total
              </span>
            </div>

            <Link
              :href="`/projects/${p.slug}/board/`"
              class="font-semibold text-indigo-600 hover:text-indigo-700 transition-colors flex items-center gap-1"
            >
              Open Board &rarr;
            </Link>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div
        v-else
        class="bg-white rounded-2xl border-2 border-dashed border-slate-200 p-12 text-center max-w-lg mx-auto"
      >
        <div class="w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center mx-auto mb-4">
          <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
        </div>
        <h3 class="text-base font-bold text-slate-900">No projects yet</h3>
        <p class="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
          Get started by creating your first project workspace to track bugs, tasks, and stories.
        </p>
        <button
          type="button"
          class="mt-5 inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-indigo-600 rounded-lg shadow-sm hover:bg-indigo-700 transition-colors"
          @click="showNewProjectModal = true"
        >
          Create your first project
        </button>
      </div>
    </div>

    <!-- Create Project Modal -->
    <div v-if="showNewProjectModal" class="fixed inset-0 z-50 overflow-y-auto" role="dialog" aria-modal="true">
      <div
        class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm transition-opacity"
        @click="showNewProjectModal = false"
      ></div>

      <div class="flex min-h-full items-center justify-center p-4 text-center">
        <div class="relative transform overflow-hidden rounded-xl bg-white text-left shadow-2xl transition-all sm:my-8 sm:w-full sm:max-w-lg border border-slate-200">
          <div class="px-6 py-4 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
            <h3 class="text-base font-semibold text-slate-900">Create New Project</h3>
            <button
              type="button"
              class="text-slate-400 hover:text-slate-500 rounded p-1"
              @click="showNewProjectModal = false"
            >
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <form @submit.prevent="createProject">
            <div class="p-6 space-y-5">
              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                  Project Name <span class="text-rose-500">*</span>
                </label>
                <input
                  v-model="form.name"
                  type="text"
                  required
                  placeholder="e.g. Mobile Banking App"
                  class="w-full rounded-xl border-slate-300 shadow-xs focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 text-sm font-medium px-3.5 py-2.5 bg-white"
                />
                <p v-if="form.errors.name" class="mt-1.5 text-xs text-rose-600 font-medium">
                  {{ form.errors.name }}
                </p>
              </div>

              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                  Project Key <span class="text-rose-500">*</span>
                  <span class="text-slate-400 font-normal text-[11px] ml-1">(2-10 uppercase chars, e.g. 'BANK')</span>
                </label>
                <input
                  v-model="form.key"
                  type="text"
                  required
                  maxlength="10"
                  placeholder="BANK"
                  class="w-full rounded-xl border-slate-300 shadow-xs focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 font-mono font-bold uppercase text-sm px-3.5 py-2.5 bg-white"
                />
                <p v-if="form.errors.key" class="mt-1.5 text-xs text-rose-600 font-medium">
                  {{ form.errors.key }}
                </p>
              </div>

              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                  Description
                </label>
                <textarea
                  v-model="form.description"
                  rows="3"
                  placeholder="Brief summary of this project..."
                  class="w-full rounded-xl border-slate-300 shadow-xs focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 text-sm p-3.5 leading-relaxed bg-white"
                ></textarea>
              </div>
            </div>

            <div class="px-6 py-4 bg-slate-50 border-t border-slate-100 flex items-center justify-end gap-3 rounded-b-2xl">
              <button
                type="button"
                class="px-4 py-2.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-xl hover:bg-slate-50 transition-colors"
                @click="showNewProjectModal = false"
              >
                Cancel
              </button>
              <button
                type="submit"
                :disabled="form.processing"
                class="px-4 py-2.5 text-xs font-bold text-white bg-indigo-600 rounded-xl shadow-xs hover:bg-indigo-700 disabled:opacity-50 transition-colors"
              >
                Create Project
              </button>
            </div>
          </form>

        </div>
      </div>
    </div>
  </AppLayout>
</template>
