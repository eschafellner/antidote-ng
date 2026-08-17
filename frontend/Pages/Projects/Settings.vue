<script setup>
import { ref } from 'vue';
import { Head, useForm, router } from '@inertiajs/vue3';
import AppLayout from '@/Components/AppLayout.vue';
import UserAvatar from '@/Components/UserAvatar.vue';

const props = defineProps({
  project: {
    type: Object,
    required: true,
  },
  members: {
    type: Array,
    default: () => [],
  },
  invitations: {
    type: Array,
    default: () => [],
  },
  available_roles: {
    type: Array,
    default: () => [],
  },
  errors: {
    type: Object,
    default: () => ({}),
  },
});

// Project metadata form
const projectForm = useForm({
  name: props.project.name,
  description: props.project.description || '',
});

const updateProject = () => {
  projectForm.post(`/projects/${props.project.slug}/update/`, {
    preserveScroll: true,
  });
};

// Member invite form
const inviteForm = useForm({
  email: '',
  role: 'member',
});

const sendInvite = () => {
  inviteForm.post(`/projects/${props.project.slug}/invitations/`, {
    preserveScroll: true,
    onSuccess: () => {
      inviteForm.reset();
    },
  });
};

const changeMemberRole = (userId, newRole) => {
  router.post(
    `/projects/${props.project.slug}/members/${userId}/role/`,
    { role: newRole },
    { preserveScroll: true }
  );
};

const removeMember = userId => {
  if (confirm('Are you sure you want to remove this member from the project?')) {
    router.post(
      `/projects/${props.project.slug}/members/${userId}/remove/`,
      {},
      { preserveScroll: true }
    );
  }
};

const revokeInvite = invitationId => {
  router.post(
    `/projects/${props.project.slug}/invitations/${invitationId}/revoke/`,
    {},
    { preserveScroll: true }
  );
};

const deleteProject = () => {
  if (confirm(`Are you ABSOLUTELY sure you want to delete "${props.project.name}"? This action cannot be undone.`)) {
    router.post(`/projects/${props.project.slug}/delete/`);
  }
};
</script>

<template>
  <AppLayout :project="project" :members="members">
    <Head :title="`${project.name} - Settings & Members`" />

    <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full space-y-8">
      <!-- Top Title -->
      <div>
        <h1 class="text-2xl font-black text-slate-900 tracking-tight">
          Project Settings
        </h1>
        <p class="text-xs text-slate-500 mt-1">
          Manage general metadata, team members, and role-based permissions.
        </p>
      </div>

      <!-- General Settings Card -->
      <div class="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div class="px-6 py-4 border-b border-slate-100 bg-slate-50/50">
          <h2 class="text-sm font-bold text-slate-900">General Information</h2>
        </div>

        <form @submit.prevent="updateProject" class="p-6 space-y-4">
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div class="sm:col-span-2">
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
                Project Name
              </label>
              <input
                v-model="projectForm.name"
                type="text"
                required
                class="w-full rounded-lg border-slate-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm"
              />
            </div>

            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
                Key Prefix
              </label>
              <input
                :value="project.key"
                disabled
                class="w-full rounded-lg border-slate-200 bg-slate-100 font-mono text-slate-500 text-sm cursor-not-allowed uppercase"
              />
            </div>
          </div>

          <div>
            <label class="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1">
              Description
            </label>
            <textarea
              v-model="projectForm.description"
              rows="3"
              class="w-full rounded-lg border-slate-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm"
            ></textarea>
          </div>

          <div class="flex justify-end">
            <button
              type="submit"
              :disabled="projectForm.processing"
              class="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 rounded-lg shadow-sm hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              Save Changes
            </button>
          </div>
        </form>
      </div>

      <!-- Member Management Card -->
      <div class="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div class="px-6 py-4 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
          <h2 class="text-sm font-bold text-slate-900">
            Team Members ({{ members.length }})
          </h2>
        </div>

        <div class="divide-y divide-slate-100">
          <div
            v-for="m in members"
            :key="m.id"
            class="px-6 py-3.5 flex items-center justify-between gap-4 hover:bg-slate-50/60 transition-colors"
          >
            <div class="flex items-center gap-3 min-w-0">
              <UserAvatar :user="m" size="md" />
              <div class="min-w-0">
                <p class="text-sm font-semibold text-slate-900 truncate">
                  {{ m.first_name && m.last_name ? `${m.first_name} ${m.last_name}` : m.username }}
                  <span v-if="m.is_owner" class="ml-1.5 text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700">
                    Owner
                  </span>
                </p>
                <p class="text-xs text-slate-500 truncate">{{ m.email }}</p>
              </div>
            </div>

            <!-- Role Selector & Actions -->
            <div class="flex items-center gap-3">
              <select
                :value="m.role"
                :disabled="m.is_owner"
                class="py-1 pl-2.5 pr-8 text-xs font-medium rounded-lg border-slate-300 focus:border-indigo-500 focus:ring-indigo-500 disabled:bg-slate-100 disabled:text-slate-400 disabled:cursor-not-allowed"
                @change="e => changeMemberRole(m.user_id, e.target.value)"
              >
                <option v-for="r in available_roles" :key="r.value" :value="r.value">
                  {{ r.label }}
                </option>
              </select>

              <button
                v-if="!m.is_owner"
                type="button"
                class="text-rose-600 hover:text-rose-700 p-1 rounded-md text-xs font-semibold hover:bg-rose-50 transition-colors"
                title="Remove Member"
                @click="removeMember(m.user_id)"
              >
                Remove
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Invitations Card -->
      <div class="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div class="px-6 py-4 border-b border-slate-100 bg-slate-50/50">
          <h2 class="text-sm font-bold text-slate-900">Invite New Members</h2>
        </div>

        <div class="p-6 space-y-6">
          <form @submit.prevent="sendInvite" class="flex flex-col sm:flex-row gap-3">
            <div class="flex-1">
              <input
                v-model="inviteForm.email"
                type="email"
                required
                placeholder="colleague@example.com"
                class="w-full rounded-lg border-slate-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm"
              />
              <p v-if="inviteForm.errors.email" class="mt-1 text-xs text-rose-600 font-medium">
                {{ inviteForm.errors.email }}
              </p>
            </div>

            <div class="w-full sm:w-40">
              <select
                v-model="inviteForm.role"
                class="w-full rounded-lg border-slate-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm"
              >
                <option v-for="r in available_roles" :key="r.value" :value="r.value">
                  {{ r.label }}
                </option>
              </select>
            </div>

            <button
              type="submit"
              :disabled="inviteForm.processing"
              class="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 rounded-lg shadow-sm hover:bg-indigo-700 disabled:opacity-50 transition-colors"
            >
              Generate Invite
            </button>
          </form>

          <!-- Pending Invites List -->
          <div v-if="invitations.length > 0" class="pt-4 border-t border-slate-100 space-y-3">
            <h3 class="text-xs font-bold uppercase tracking-wider text-slate-500">
              Pending Invitations
            </h3>

            <div class="divide-y divide-slate-100 border rounded-lg overflow-hidden">
              <div
                v-for="inv in invitations"
                :key="inv.id"
                class="px-4 py-3 flex items-center justify-between gap-4 text-xs"
              >
                <div class="min-w-0">
                  <p class="font-semibold text-slate-900 truncate">{{ inv.email }}</p>
                  <p class="text-slate-400">Role: <span class="uppercase font-mono">{{ inv.role }}</span></p>
                </div>

                <div class="flex items-center gap-3">
                  <button
                    type="button"
                    class="text-indigo-600 hover:text-indigo-700 font-medium"
                    @click="navigator.clipboard.writeText(`${window.location.origin}/invitations/${inv.token}/`); alert('Invitation link copied to clipboard!');"
                  >
                    Copy Link
                  </button>
                  <button
                    type="button"
                    class="text-rose-600 hover:text-rose-700 font-medium"
                    @click="revokeInvite(inv.id)"
                  >
                    Revoke
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Danger Zone -->
      <div v-if="project.is_owner" class="bg-rose-50/50 rounded-xl border border-rose-200 p-6">
        <h2 class="text-sm font-bold text-rose-900">Danger Zone</h2>
        <p class="text-xs text-rose-700 mt-1">
          Deleting this project will permanently remove all issues, comments, attachments, and memberships.
        </p>
        <button
          type="button"
          class="mt-4 px-4 py-2 text-xs font-semibold text-white bg-rose-600 rounded-lg shadow-sm hover:bg-rose-700 transition-colors"
          @click="deleteProject"
        >
          Delete Project
        </button>
      </div>
    </div>
  </AppLayout>
</template>
