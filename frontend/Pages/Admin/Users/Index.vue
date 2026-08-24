<script setup>
import { ref, computed } from 'vue';
import { Head, useForm, router, usePage } from '@inertiajs/vue3';
import AppLayout from '@/Components/AppLayout.vue';
import UserAvatar from '@/Components/UserAvatar.vue';

const props = defineProps({
  users: {
    type: Array,
    default: () => [],
  },
  projects: {
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

const page = usePage();
const currentUser = computed(() => page.props.auth?.user);

// Search & Filter
const searchQuery = ref('');
const roleFilter = ref('all'); // 'all' | 'admin' | 'member'

const filteredUsers = computed(() => {
  return props.users.filter(u => {
    const matchesSearch =
      u.username.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      u.email.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
      `${u.first_name} ${u.last_name}`.toLowerCase().includes(searchQuery.value.toLowerCase());

    const matchesRole =
      roleFilter.value === 'all' ||
      (roleFilter.value === 'admin' && u.is_global_admin) ||
      (roleFilter.value === 'member' && !u.is_global_admin);

    return matchesSearch && matchesRole;
  });
});

// Modal States
const showCreateModal = ref(false);
const showEditModal = ref(false);
const showAccessModal = ref(false);

const selectedUser = ref(null);

// Create User Form
const createForm = useForm({
  username: '',
  email: '',
  password: '',
  first_name: '',
  last_name: '',
  is_global_admin: false,
  project_access: [],
});

// Edit User Form
const editForm = useForm({
  username: '',
  email: '',
  password: '',
  first_name: '',
  last_name: '',
  is_global_admin: false,
});

// Project Access Form
const accessForm = useForm({
  project_roles: [],
});

// Actions
const openCreateModal = () => {
  createForm.reset();
  // Initialize project access matrix
  createForm.project_access = props.projects.map(p => ({
    project_id: p.id,
    project_name: p.name,
    project_key: p.key,
    role: '',
  }));
  showCreateModal.value = true;
};

const submitCreateUser = () => {
  createForm.post('/users/new/', {
    onSuccess: () => {
      showCreateModal.value = false;
      createForm.reset();
    },
  });
};

const openEditModal = user => {
  selectedUser.value = user;
  editForm.username = user.username;
  editForm.email = user.email;
  editForm.first_name = user.first_name || '';
  editForm.last_name = user.last_name || '';
  editForm.is_global_admin = user.is_global_admin;
  editForm.password = '';
  showEditModal.value = true;
};

const submitEditUser = () => {
  if (!selectedUser.value) return;
  editForm.post(`/users/${selectedUser.value.id}/update/`, {
    onSuccess: () => {
      showEditModal.value = false;
    },
  });
};

const openAccessModal = user => {
  selectedUser.value = user;
  const currentMemberships = {};
  user.memberships.forEach(m => {
    currentMemberships[m.project_id] = m.role;
  });

  accessForm.project_roles = props.projects.map(p => ({
    project_id: p.id,
    project_name: p.name,
    project_key: p.key,
    role: currentMemberships[p.id] || '',
  }));
  showAccessModal.value = true;
};

const submitAccessModal = () => {
  if (!selectedUser.value) return;
  accessForm.post(`/users/${selectedUser.value.id}/projects/`, {
    onSuccess: () => {
      showAccessModal.value = false;
    },
  });
};

const deleteUser = user => {
  if (confirm(`Are you sure you want to delete user "${user.username}"?`)) {
    router.post(`/users/${user.id}/delete/`);
  }
};
</script>

<template>
  <AppLayout>
    <Head title="User Management - Antidote" />

    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full space-y-6">
      <!-- Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 class="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2.5">
            <div class="w-8 h-8 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center">
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
            </div>
            Global User Management
          </h1>
          <p class="text-xs text-slate-500 mt-1">
            Manage system users, global admin privileges, and multi-project role assignments.
          </p>
        </div>

        <button
          type="button"
          class="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-indigo-600 rounded-lg shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors self-start sm:self-auto"
          @click="openCreateModal"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4" />
          </svg>
          Add New User
        </button>
      </div>

      <!-- Global Error Alert -->
      <div
        v-if="errors.non_field_errors || errors.user"
        class="rounded-xl bg-rose-50 border border-rose-200 p-4 text-xs text-rose-700 font-medium"
      >
        {{ errors.non_field_errors || errors.user }}
      </div>

      <!-- Filter Controls Bar -->
      <div class="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-4">
        <div class="relative w-full sm:w-80">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search by username, name, or email..."
            class="w-full pl-9 pr-4 py-1.5 text-xs rounded-lg border-slate-300 focus:border-indigo-500 focus:ring-indigo-500 placeholder:text-slate-400"
          />
          <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
        </div>

        <div class="flex items-center gap-2 w-full sm:w-auto">
          <span class="text-xs font-semibold text-slate-500">Filter Role:</span>
          <div class="flex rounded-lg bg-slate-100 p-0.5 text-xs">
            <button
              type="button"
              :class="[
                'px-3 py-1 rounded-md font-medium transition-colors',
                roleFilter === 'all' ? 'bg-white text-slate-900 shadow-2xs font-semibold' : 'text-slate-600 hover:text-slate-900',
              ]"
              @click="roleFilter = 'all'"
            >
              All ({{ users.length }})
            </button>
            <button
              type="button"
              :class="[
                'px-3 py-1 rounded-md font-medium transition-colors',
                roleFilter === 'admin' ? 'bg-white text-indigo-700 shadow-2xs font-semibold' : 'text-slate-600 hover:text-slate-900',
              ]"
              @click="roleFilter = 'admin'"
            >
              Admins
            </button>
            <button
              type="button"
              :class="[
                'px-3 py-1 rounded-md font-medium transition-colors',
                roleFilter === 'member' ? 'bg-white text-slate-900 shadow-2xs font-semibold' : 'text-slate-600 hover:text-slate-900',
              ]"
              @click="roleFilter = 'member'"
            >
              Members
            </button>
          </div>
        </div>
      </div>

      <!-- Users Table -->
      <div class="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-slate-200">
            <thead class="bg-slate-50 text-slate-500 text-[11px] font-bold uppercase tracking-wider text-left">
              <tr>
                <th scope="col" class="py-3.5 pl-4 pr-3 sm:pl-6">User</th>
                <th scope="col" class="px-3 py-3.5">Global Role</th>
                <th scope="col" class="px-3 py-3.5">Project Access</th>
                <th scope="col" class="px-3 py-3.5">Joined</th>
                <th scope="col" class="relative py-3.5 pl-3 pr-4 sm:pr-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100 text-xs text-slate-700">
              <tr
                v-for="u in filteredUsers"
                :key="u.id"
                class="hover:bg-slate-50/70 transition-colors"
              >
                <!-- User Info -->
                <td class="py-3.5 pl-4 pr-3 sm:pl-6">
                  <div class="flex items-center gap-3">
                    <UserAvatar :user="u" size="md" />
                    <div>
                      <div class="font-bold text-slate-900 flex items-center gap-1.5">
                        {{ u.first_name && u.last_name ? `${u.first_name} ${u.last_name}` : u.username }}
                        <span v-if="u.id === currentUser?.id" class="text-[10px] bg-slate-100 text-slate-500 px-1.5 py-0.2 rounded font-normal">
                          (You)
                        </span>
                      </div>
                      <div class="text-[11px] text-slate-500">
                        @{{ u.username }} &bull; {{ u.email }}
                      </div>
                    </div>
                  </div>
                </td>

                <!-- Global Role -->
                <td class="px-3 py-3.5 whitespace-nowrap">
                  <span
                    v-if="u.is_global_admin"
                    class="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200"
                  >
                    <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                    Global Admin
                  </span>
                  <span
                    v-else
                    class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200"
                  >
                    Global Member
                  </span>
                </td>

                <!-- Project Access -->
                <td class="px-3 py-3.5">
                  <div v-if="u.is_global_admin" class="text-xs text-indigo-700 font-medium flex items-center gap-1">
                    <span>All projects (Superuser access)</span>
                  </div>
                  <div v-else-if="u.memberships.length > 0" class="flex flex-wrap gap-1.5 max-w-sm">
                    <span
                      v-for="m in u.memberships"
                      :key="m.project_id"
                      class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-200"
                      :title="`${m.project_name} (${m.role})`"
                    >
                      <strong class="font-mono text-slate-900">{{ m.project_key }}</strong>
                      <span class="text-[10px] text-slate-500 uppercase">({{ m.role }})</span>
                    </span>
                  </div>
                  <span v-else class="text-xs text-slate-400 italic">
                    No assigned projects
                  </span>
                </td>

                <!-- Joined Date -->
                <td class="px-3 py-3.5 whitespace-nowrap text-slate-500 text-[11px]">
                  {{ u.date_joined ? new Date(u.date_joined).toLocaleDateString() : '—' }}
                </td>

                <!-- Actions -->
                <td class="py-3.5 pl-3 pr-4 sm:pr-6 text-right whitespace-nowrap">
                  <div class="flex items-center justify-end gap-2">
                    <button
                      type="button"
                      class="px-2.5 py-1 text-xs font-semibold text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-md border border-indigo-100 transition-colors"
                      title="Manage project memberships"
                      @click="openAccessModal(u)"
                    >
                      Project Access
                    </button>
                    <button
                      type="button"
                      class="p-1 text-slate-400 hover:text-slate-600 rounded hover:bg-slate-100 transition-colors"
                      title="Edit User"
                      @click="openEditModal(u)"
                    >
                      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                    </button>
                    <button
                      v-if="u.id !== currentUser?.id"
                      type="button"
                      class="p-1 text-slate-400 hover:text-rose-600 rounded hover:bg-rose-50 transition-colors"
                      title="Delete User"
                      @click="deleteUser(u)"
                    >
                      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Create User Modal -->
    <div v-if="showCreateModal" class="fixed inset-0 z-50 overflow-y-auto" role="dialog" aria-modal="true">
      <div class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm" @click="showCreateModal = false"></div>
      <div class="flex min-h-full items-center justify-center p-4">
        <div class="relative w-full max-w-xl bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden text-left">
          <div class="px-6 py-4 border-b border-slate-100 bg-slate-50/60 flex items-center justify-between">
            <h3 class="text-base font-bold text-slate-900">Create New User</h3>
            <button type="button" class="text-slate-400 hover:text-slate-600 p-1 rounded-lg" @click="showCreateModal = false">
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <form @submit.prevent="submitCreateUser">
            <div class="p-6 space-y-5 max-h-[75vh] overflow-y-auto">
              <!-- Basic fields -->
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label class="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">Username *</label>
                  <input
                    v-model="createForm.username"
                    type="text"
                    required
                    placeholder="johndoe"
                    class="w-full rounded-xl border-slate-300 shadow-xs text-sm px-3.5 py-2.5 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 bg-white"
                  />
                  <p v-if="createForm.errors.username" class="text-xs text-rose-600 mt-1.5 font-medium">{{ createForm.errors.username }}</p>
                </div>
                <div>
                  <label class="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">Email *</label>
                  <input
                    v-model="createForm.email"
                    type="email"
                    required
                    placeholder="john@example.com"
                    class="w-full rounded-xl border-slate-300 shadow-xs text-sm px-3.5 py-2.5 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 bg-white"
                  />
                  <p v-if="createForm.errors.email" class="text-xs text-rose-600 mt-1.5 font-medium">{{ createForm.errors.email }}</p>
                </div>
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label class="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">First Name</label>
                  <input
                    v-model="createForm.first_name"
                    type="text"
                    placeholder="John"
                    class="w-full rounded-xl border-slate-300 shadow-xs text-sm px-3.5 py-2.5 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 bg-white"
                  />
                </div>
                <div>
                  <label class="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">Last Name</label>
                  <input
                    v-model="createForm.last_name"
                    type="text"
                    placeholder="Doe"
                    class="w-full rounded-xl border-slate-300 shadow-xs text-sm px-3.5 py-2.5 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 bg-white"
                  />
                </div>
              </div>

              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">Password * (min. 6 chars)</label>
                <input
                  v-model="createForm.password"
                  type="password"
                  required
                  placeholder="••••••••"
                  class="w-full rounded-xl border-slate-300 shadow-xs text-sm px-3.5 py-2.5 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 bg-white"
                />
                <p v-if="createForm.errors.password" class="text-xs text-rose-600 mt-1.5 font-medium">{{ createForm.errors.password }}</p>
              </div>

              <!-- Global Role Toggle -->
              <div class="pt-2 border-t border-slate-100">
                <label class="flex items-center gap-3 cursor-pointer p-3.5 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-slate-50 transition-colors">
                  <input
                    v-model="createForm.is_global_admin"
                    type="checkbox"
                    class="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                  />
                  <div>
                    <span class="text-xs font-bold text-slate-900 block">Grant Global Admin Privileges</span>
                    <span class="text-[11px] text-slate-500">Global admins have unrestricted access to all projects and user management.</span>
                  </div>
                </label>
              </div>

              <!-- Initial Project Access Matrix -->
              <div v-if="!createForm.is_global_admin && projects.length > 0" class="pt-3 border-t border-slate-100 space-y-3">
                <h4 class="text-xs font-bold uppercase tracking-wider text-slate-700">Assign Project Roles</h4>
                <div class="divide-y divide-slate-100 border border-slate-200 rounded-xl overflow-hidden max-h-48 overflow-y-auto">
                  <div
                    v-for="p in createForm.project_access"
                    :key="p.project_id"
                    class="p-3 flex items-center justify-between gap-3 bg-white text-xs"
                  >
                    <span class="font-bold text-slate-800">
                      {{ p.project_name }} <span class="font-mono text-slate-400 font-normal">({{ p.project_key }})</span>
                    </span>
                    <select
                      v-model="p.role"
                      class="py-1.5 px-3 text-xs font-medium rounded-lg border-slate-300 focus:border-indigo-500 focus:ring-indigo-500 bg-white shadow-xs"
                    >
                      <option value="">No Access</option>
                      <option v-for="r in available_roles" :key="r.value" :value="r.value">
                        {{ r.label }}
                      </option>
                    </select>
                  </div>
                </div>
              </div>
            </div>

            <div class="px-6 py-4 bg-slate-50 border-t border-slate-100 flex justify-end gap-3 rounded-b-2xl">
              <button
                type="button"
                class="px-4 py-2.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-xl hover:bg-slate-50 transition-colors"
                @click="showCreateModal = false"
              >
                Cancel
              </button>
              <button
                type="submit"
                :disabled="createForm.processing"
                class="px-4 py-2.5 text-xs font-bold text-white bg-indigo-600 rounded-xl shadow-xs hover:bg-indigo-700 disabled:opacity-50 transition-colors"
              >
                Create User
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Edit User Modal -->
    <div v-if="showEditModal && selectedUser" class="fixed inset-0 z-50 overflow-y-auto" role="dialog" aria-modal="true">
      <div class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm" @click="showEditModal = false"></div>
      <div class="flex min-h-full items-center justify-center p-4">
        <div class="relative w-full max-w-lg bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden text-left">
          <div class="px-6 py-4 border-b border-slate-100 bg-slate-50/60 flex items-center justify-between">
            <h3 class="text-base font-bold text-slate-900">Edit User: {{ selectedUser.username }}</h3>
            <button type="button" class="text-slate-400 hover:text-slate-600 p-1 rounded-lg" @click="showEditModal = false">
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <form @submit.prevent="submitEditUser">
            <div class="p-6 space-y-5">
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label class="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">Username *</label>
                  <input
                    v-model="editForm.username"
                    type="text"
                    required
                    class="w-full rounded-xl border-slate-300 shadow-xs text-sm px-3.5 py-2.5 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 bg-white"
                  />
                  <p v-if="editForm.errors.username" class="text-xs text-rose-600 mt-1.5 font-medium">{{ editForm.errors.username }}</p>
                </div>
                <div>
                  <label class="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">Email *</label>
                  <input
                    v-model="editForm.email"
                    type="email"
                    required
                    class="w-full rounded-xl border-slate-300 shadow-xs text-sm px-3.5 py-2.5 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 bg-white"
                  />
                  <p v-if="editForm.errors.email" class="text-xs text-rose-600 mt-1.5 font-medium">{{ editForm.errors.email }}</p>
                </div>
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label class="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">First Name</label>
                  <input
                    v-model="editForm.first_name"
                    type="text"
                    class="w-full rounded-xl border-slate-300 shadow-xs text-sm px-3.5 py-2.5 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 bg-white"
                  />
                </div>
                <div>
                  <label class="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">Last Name</label>
                  <input
                    v-model="editForm.last_name"
                    type="text"
                    class="w-full rounded-xl border-slate-300 shadow-xs text-sm px-3.5 py-2.5 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 bg-white"
                  />
                </div>
              </div>

              <div>
                <label class="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">New Password (leave empty to keep current)</label>
                <input
                  v-model="editForm.password"
                  type="password"
                  placeholder="••••••••"
                  class="w-full rounded-xl border-slate-300 shadow-xs text-sm px-3.5 py-2.5 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 bg-white"
                />
              </div>

              <!-- Global Role Toggle -->
              <div class="pt-2 border-t border-slate-100">
                <label class="flex items-center gap-3 cursor-pointer p-3.5 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-slate-50 transition-colors">
                  <input
                    v-model="editForm.is_global_admin"
                    type="checkbox"
                    class="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                  />
                  <div>
                    <span class="text-xs font-bold text-slate-900 block">Global Admin Privileges</span>
                    <span class="text-[11px] text-slate-500">Enable system-wide administration and project-wide access.</span>
                  </div>
                </label>
              </div>
            </div>

            <div class="px-6 py-4 bg-slate-50 border-t border-slate-100 flex justify-end gap-3 rounded-b-2xl">
              <button
                type="button"
                class="px-4 py-2.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-xl hover:bg-slate-50 transition-colors"
                @click="showEditModal = false"
              >
                Cancel
              </button>
              <button
                type="submit"
                :disabled="editForm.processing"
                class="px-4 py-2.5 text-xs font-bold text-white bg-indigo-600 rounded-xl shadow-xs hover:bg-indigo-700 disabled:opacity-50 transition-colors"
              >
                Save Changes
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Manage Project Access Matrix Modal -->
    <div v-if="showAccessModal && selectedUser" class="fixed inset-0 z-50 overflow-y-auto" role="dialog" aria-modal="true">
      <div class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm" @click="showAccessModal = false"></div>
      <div class="flex min-h-full items-center justify-center p-4">
        <div class="relative w-full max-w-xl bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden text-left">
          <div class="px-6 py-4 border-b border-slate-100 bg-slate-50/60 flex items-center justify-between">
            <div>
              <h3 class="text-base font-bold text-slate-900">Project Access: {{ selectedUser.username }}</h3>
              <p class="text-xs text-slate-500 mt-0.5">Configure individual project roles for this user.</p>
            </div>
            <button type="button" class="text-slate-400 hover:text-slate-600 p-1 rounded-lg" @click="showAccessModal = false">
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <form @submit.prevent="submitAccessModal">
            <div class="p-6 space-y-4 max-h-[60vh] overflow-y-auto">
              <div v-if="selectedUser.is_global_admin" class="p-3.5 bg-indigo-50 border border-indigo-100 rounded-xl text-xs text-indigo-800">
                <strong>Note:</strong> This user is a <strong>Global Admin</strong> and inherently has full admin privileges across all projects. You can still set explicit project roles below for auditing.
              </div>

              <div class="divide-y divide-slate-100 border border-slate-200 rounded-xl overflow-hidden">
                <div
                  v-for="p in accessForm.project_roles"
                  :key="p.project_id"
                  class="p-3.5 flex items-center justify-between gap-3 bg-white hover:bg-slate-50/60 transition-colors"
                >
                  <div class="min-w-0">
                    <p class="text-xs font-bold text-slate-900 truncate">{{ p.project_name }}</p>
                    <p class="text-[11px] font-mono text-slate-400">{{ p.project_key }}</p>
                  </div>

                  <select
                    v-model="p.role"
                    class="py-2 px-3 text-xs font-medium rounded-xl border-slate-300 shadow-xs focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 bg-white"
                  >
                    <option value="">No Access (Remove)</option>
                    <option v-for="r in available_roles" :key="r.value" :value="r.value">
                      {{ r.label }}
                    </option>
                  </select>
                </div>

                <div v-if="accessForm.project_roles.length === 0" class="p-6 text-center text-xs text-slate-400 italic">
                  No projects exist in the system yet.
                </div>
              </div>
            </div>

            <div class="px-6 py-4 bg-slate-50 border-t border-slate-100 flex justify-end gap-3 rounded-b-2xl">
              <button
                type="button"
                class="px-4 py-2.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-xl hover:bg-slate-50 transition-colors"
                @click="showAccessModal = false"
              >
                Cancel
              </button>
              <button
                type="submit"
                :disabled="accessForm.processing"
                class="px-4 py-2.5 text-xs font-bold text-white bg-indigo-600 rounded-xl shadow-xs hover:bg-indigo-700 disabled:opacity-50 transition-colors"
              >
                Save Project Access
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

  </AppLayout>
</template>
