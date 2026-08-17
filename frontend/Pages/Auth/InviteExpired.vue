<script setup>
import { Head, Link } from '@inertiajs/vue3';

defineProps({
  error: {
    type: String,
    default: 'This invitation link is invalid or has expired.',
  },
});
</script>

<template>
  <Head title="Invitation Expired - Antidote" />

  <div class="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
    <div class="sm:mx-auto sm:w-full sm:max-w-md text-center">
      <div class="w-14 h-14 rounded-2xl bg-amber-100 text-amber-600 flex items-center justify-center mx-auto shadow-sm">
        <svg class="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      </div>

      <h2 class="mt-4 text-2xl font-black tracking-tight text-slate-900">
        Invitation Invalid
      </h2>
      <p class="mt-2 text-xs text-slate-600 max-w-sm mx-auto">
        {{ error }}
      </p>

      <div class="mt-6">
        <Link
          href="/login/"
          class="inline-flex items-center px-4 py-2 text-xs font-semibold text-white bg-indigo-600 rounded-lg shadow-sm hover:bg-indigo-700 transition-colors"
        >
          Return to Sign In
        </Link>
      </div>
    </div>
  </div>
</template>
