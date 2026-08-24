<script setup>
import { Head, Link, useForm } from '@inertiajs/vue3';

const props = defineProps({
  token: {
    type: String,
    default: '',
  },
  invite: {
    type: Object,
    default: null,
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
  email: props.invite ? props.invite.email : (props.values.email || ''),
  password: '',
  first_name: props.values.first_name || '',
  last_name: props.values.last_name || '',
  token: props.token,
});

const submit = () => {
  form.post('/register/');
};
</script>

<template>
  <Head title="Create Account - Antidote" />

  <div class="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
    <div class="sm:mx-auto sm:w-full sm:max-w-md">
      <div class="flex justify-center">
        <div class="w-12 h-12 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-md">
          <svg class="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
          </svg>
        </div>
      </div>
      <h2 class="mt-4 text-center text-2xl font-black tracking-tight text-slate-900">
        Create your account
      </h2>
      <p v-if="invite" class="mt-1 text-center text-xs text-indigo-600 font-medium">
        You've been invited to join <strong>{{ invite.project_name }}</strong>!
      </p>
      <p v-else class="mt-1 text-center text-xs text-slate-500">
        Get started with agile issue tracking
      </p>
    </div>

    <div class="mt-6 sm:mx-auto sm:w-full sm:max-w-md">
      <div class="bg-white py-8 px-6 shadow-xl shadow-slate-200/50 rounded-2xl border border-slate-200/80 sm:px-10">
        <!-- Global Errors -->
        <div
          v-if="errors.non_field_errors"
          class="mb-6 rounded-xl bg-rose-50 border border-rose-200 p-3.5 text-xs text-rose-700 font-medium"
        >
          {{ errors.non_field_errors }}
        </div>

        <form class="space-y-4" @submit.prevent="submit">
          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
              Username <span class="text-rose-500">*</span>
            </label>
            <input
              v-model="form.username"
              type="text"
              required
              autofocus
              placeholder="johndoe"
              class="w-full rounded-xl border-slate-300 shadow-xs focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 text-sm px-3.5 py-2.5 leading-relaxed placeholder:text-slate-400 bg-white"
            />
            <p v-if="errors.username" class="mt-1.5 text-xs text-rose-600 font-medium">
              {{ errors.username }}
            </p>
          </div>

          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
              Email Address <span class="text-rose-500">*</span>
            </label>
            <input
              v-model="form.email"
              type="email"
              required
              :disabled="!!invite"
              placeholder="john@example.com"
              class="w-full rounded-xl border-slate-300 shadow-xs focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 text-sm px-3.5 py-2.5 leading-relaxed placeholder:text-slate-400 disabled:bg-slate-100 disabled:text-slate-500"
            />
            <p v-if="errors.email" class="mt-1.5 text-xs text-rose-600 font-medium">
              {{ errors.email }}
            </p>
          </div>

          <div class="grid grid-cols-2 gap-3.5">
            <div>
              <label class="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                First Name
              </label>
              <input
                v-model="form.first_name"
                type="text"
                placeholder="John"
                class="w-full rounded-xl border-slate-300 shadow-xs focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 text-sm px-3.5 py-2.5 leading-relaxed placeholder:text-slate-400 bg-white"
              />
            </div>
            <div>
              <label class="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                Last Name
              </label>
              <input
                v-model="form.last_name"
                type="text"
                placeholder="Doe"
                class="w-full rounded-xl border-slate-300 shadow-xs focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 text-sm px-3.5 py-2.5 leading-relaxed placeholder:text-slate-400 bg-white"
              />
            </div>
          </div>

          <div>
            <label class="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
              Password <span class="text-rose-500">*</span>
            </label>
            <input
              v-model="form.password"
              type="password"
              required
              placeholder="••••••••"
              class="w-full rounded-xl border-slate-300 shadow-xs focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 text-sm px-3.5 py-2.5 leading-relaxed placeholder:text-slate-400 bg-white"
            />
            <p v-if="errors.password" class="mt-1.5 text-xs text-rose-600 font-medium">
              {{ errors.password }}
            </p>
          </div>

          <button
            type="submit"
            :disabled="form.processing"
            class="w-full mt-3 flex justify-center py-2.5 px-4 border border-transparent rounded-xl shadow-sm text-sm font-bold text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 transition-colors"
          >
            Create Account
          </button>
        </form>

        <div class="mt-6 text-center text-xs text-slate-500">
          Already have an account?
          <Link href="/login/" class="font-semibold text-indigo-600 hover:text-indigo-700">
            Sign in
          </Link>
        </div>
      </div>
    </div>
  </div>
</template>
