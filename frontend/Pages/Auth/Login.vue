<script setup>
import { Head, Link, useForm } from '@inertiajs/vue3';

const props = defineProps({
  next: {
    type: String,
    default: '',
  },
  errors: {
    type: Object,
    default: () => ({}),
  },
  values: {
    type: Object,
    default: () => ({}),
  },
});

const form = useForm({
  username: props.values.username || '',
  password: '',
  next: props.next,
});

const submit = () => {
  form.post('/login/');
};
</script>

<template>
  <Head title="Sign In - Antidote" />

  <div class="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
    <div class="sm:mx-auto sm:w-full sm:max-w-md">
      <!-- Logo -->
      <div class="flex justify-center">
        <div class="w-12 h-12 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-md">
          <svg class="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
          </svg>
        </div>
      </div>
      <h2 class="mt-4 text-center text-2xl font-black tracking-tight text-slate-900">
        Sign in to Antidote
      </h2>
      <p class="mt-1 text-center text-xs text-slate-500">
        High-performance issue tracker and agile board
      </p>
    </div>

    <div class="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
      <div class="bg-white py-8 px-6 shadow-xl shadow-slate-200/50 rounded-2xl border border-slate-200/80 sm:px-10">
        <!-- Global Error Alert -->
        <div
          v-if="errors.non_field_errors"
          class="mb-5 rounded-lg bg-rose-50 border border-rose-200 p-3 text-xs text-rose-700 font-medium"
        >
          {{ errors.non_field_errors }}
        </div>

        <form class="space-y-4" @submit.prevent="submit">
          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
              Username or Email
            </label>
            <input
              v-model="form.username"
              type="text"
              required
              autofocus
              placeholder="developer@company.com"
              class="w-full rounded-lg border-slate-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm"
            />
            <p v-if="errors.username" class="mt-1 text-xs text-rose-600 font-medium">
              {{ errors.username }}
            </p>
          </div>

          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-700 mb-1">
              Password
            </label>
            <input
              v-model="form.password"
              type="password"
              required
              placeholder="••••••••"
              class="w-full rounded-lg border-slate-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm"
            />
          </div>

          <button
            type="submit"
            :disabled="form.processing"
            class="w-full mt-2 flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-bold text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 transition-colors"
          >
            Sign in
          </button>
        </form>

        <div class="mt-6 text-center text-xs text-slate-500">
          Don't have an account?
          <Link href="/register/" class="font-semibold text-indigo-600 hover:text-indigo-700">
            Create account
          </Link>
        </div>
      </div>
    </div>
  </div>
</template>
