<script setup>
import { Head, Link } from '@inertiajs/vue3';

const props = defineProps({
  token: {
    type: String,
    required: true,
  },
  project_name: {
    type: String,
    required: true,
  },
  project_key: {
    type: String,
    required: true,
  },
  email: {
    type: String,
    required: true,
  },
  role: {
    type: String,
    required: true,
  },
  invited_by: {
    type: String,
    required: true,
  },
});
</script>

<template>
  <Head :title="`Invitation to ${project_name}`" />

  <div class="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
    <div class="sm:mx-auto sm:w-full sm:max-w-md">
      <div class="flex justify-center">
        <div class="w-14 h-14 rounded-2xl bg-indigo-600 flex items-center justify-center text-white shadow-lg">
          <svg class="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
          </svg>
        </div>
      </div>
      <h2 class="mt-4 text-center text-2xl font-black tracking-tight text-slate-900">
        You're invited!
      </h2>
      <p class="mt-1 text-center text-xs text-slate-500">
        <strong>{{ invited_by }}</strong> invited you to collaborate on <strong>{{ project_name }}</strong> ({{ project_key }}).
      </p>
    </div>

    <div class="mt-6 sm:mx-auto sm:w-full sm:max-w-md">
      <div class="bg-white py-8 px-6 shadow-xl shadow-slate-200/50 rounded-2xl border border-slate-200/80 sm:px-10 text-center space-y-5">
        <div class="bg-slate-50 rounded-xl p-4 border border-slate-100 text-xs text-slate-600 space-y-1">
          <p><strong>Project:</strong> {{ project_name }}</p>
          <p><strong>Assigned Role:</strong> <span class="uppercase font-semibold text-indigo-600">{{ role }}</span></p>
          <p><strong>Invited Email:</strong> {{ email }}</p>
        </div>

        <div class="space-y-2">
          <Link
            :href="`/register/?token=${token}`"
            class="w-full flex justify-center py-2.5 px-4 rounded-lg shadow-sm text-sm font-bold text-white bg-indigo-600 hover:bg-indigo-700 transition-colors"
          >
            Create New Account & Join
          </Link>
          <Link
            :href="`/login/?next=/invitations/${token}/`"
            class="w-full flex justify-center py-2.5 px-4 rounded-lg border border-slate-300 text-sm font-semibold text-slate-700 bg-white hover:bg-slate-50 transition-colors"
          >
            I already have an account
          </Link>
        </div>
      </div>
    </div>
  </div>
</template>
