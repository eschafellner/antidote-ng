<script setup>
import { ref, computed } from 'vue';
import { Link, usePage, router } from '@inertiajs/vue3';
import UserAvatar from './UserAvatar.vue';
import CreateIssueModal from './CreateIssueModal.vue';

const props = defineProps({
  project: {
    type: Object,
    default: null,
  },
  members: {
    type: Array,
    default: () => [],
  },
});

const page = usePage();
const currentUser = computed(() => page.props.auth?.user);

const showCreateModal = ref(false);
const showUserDropdown = ref(false);
const mobileMenuOpen = ref(false);

const logout = () => {
  router.post('/logout/');
};

const currentPath = computed(() => page.url);
const isBoardActive = computed(() => currentPath.value.includes('/board'));
const isIssuesActive = computed(() => currentPath.value.includes('/issues') && !isBoardActive.value);
const isSettingsActive = computed(() => currentPath.value.includes('/settings'));
const isUsersActive = computed(() => currentPath.value.includes('/users'));
</script>

<template>
  <div class="min-h-screen bg-slate-50 flex flex-col">
    <!-- Top Navigation Bar -->
    <header class="sticky top-0 z-40 bg-white border-b border-slate-200/80 shadow-xs">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between h-14">
          <!-- Left side: Brand logo & Project breadcrumb -->
          <div class="flex items-center gap-4">
            <Link href="/projects/" class="flex items-center gap-2 font-bold text-slate-900 tracking-tight group">
              <div class="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-sm group-hover:bg-indigo-700 transition-colors">
                <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                </svg>
              </div>
              <span class="text-base font-extrabold bg-gradient-to-r from-slate-900 to-slate-700 bg-clip-text text-transparent">
                Antidote
              </span>
            </Link>

            <!-- Global Admin User Management Link (when outside project context) -->
            <Link
              v-if="!project && currentUser?.is_global_admin"
              href="/users/"
              :class="[
                'ml-2 px-3 py-1.5 text-xs font-semibold rounded-md transition-colors flex items-center gap-1.5',
                isUsersActive
                  ? 'bg-indigo-50 text-indigo-700 font-bold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100',
              ]"
            >
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
              User Management
            </Link>

            <!-- Project Breadcrumb & Subnav (when inside a project) -->
            <template v-if="project">
              <span class="text-slate-300 font-light">/</span>
              <div class="flex items-center gap-2">
                <span class="font-semibold text-slate-900 text-sm">
                  {{ project.name }}
                </span>
                <span class="text-xs font-mono font-medium px-1.5 py-0.5 bg-slate-100 text-slate-600 rounded border border-slate-200">
                  {{ project.key }}
                </span>
              </div>
            </template>
          </div>

          <!-- Project Nav Tabs (Center/Left desktop) -->
          <nav v-if="project" class="hidden md:flex items-center space-x-1 pl-6">
            <Link
              :href="`/projects/${project.slug}/board/`"
              :class="[
                'px-3 py-1.5 text-xs font-semibold rounded-md transition-colors flex items-center gap-1.5',
                isBoardActive
                  ? 'bg-indigo-50 text-indigo-700 font-bold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100',
              ]"
            >
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
              </svg>
              Kanban Board
            </Link>

            <Link
              :href="`/projects/${project.slug}/issues/`"
              :class="[
                'px-3 py-1.5 text-xs font-semibold rounded-md transition-colors flex items-center gap-1.5',
                isIssuesActive
                  ? 'bg-indigo-50 text-indigo-700 font-bold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100',
              ]"
            >
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
              </svg>
              List / Backlog
            </Link>

            <Link
              v-if="currentUser?.is_global_admin || project.is_owner || project.user_role === 'admin'"
              :href="`/projects/${project.slug}/settings/`"
              :class="[
                'px-3 py-1.5 text-xs font-semibold rounded-md transition-colors flex items-center gap-1.5',
                isSettingsActive
                  ? 'bg-indigo-50 text-indigo-700 font-bold'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100',
              ]"
            >
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              Settings & Members
            </Link>
          </nav>

          <!-- Right side: Create button & User dropdown -->
          <div class="flex items-center gap-3">
            <button
              v-if="project && (currentUser?.is_global_admin || project.can_create_issue !== false)"
              type="button"
              class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-indigo-600 rounded-lg shadow-xs hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
              @click="showCreateModal = true"
            >
              <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4" />
              </svg>
              New Issue
            </button>

            <!-- User Menu -->
            <div class="relative">
              <button
                type="button"
                class="flex items-center gap-2 p-1 rounded-full hover:ring-2 hover:ring-indigo-500/30 transition-all"
                @click="showUserDropdown = !showUserDropdown"
              >
                <UserAvatar :user="currentUser" size="md" />
              </button>

              <!-- Dropdown menu -->
              <div
                v-if="showUserDropdown"
                class="origin-top-right absolute right-0 mt-2 w-52 rounded-xl shadow-xl bg-white border border-slate-200 py-1.5 z-50 text-sm focus:outline-none"
                @click="showUserDropdown = false"
              >
                <div class="px-4 py-2 border-b border-slate-100">
                  <p class="font-semibold text-slate-900 truncate">
                    {{ currentUser?.username }}
                  </p>
                  <p class="text-xs text-slate-500 truncate">
                    {{ currentUser?.email }}
                  </p>
                  <span
                    v-if="currentUser?.is_global_admin"
                    class="mt-1 inline-block text-[10px] font-bold uppercase tracking-wider text-indigo-700 bg-indigo-50 px-1.5 py-0.2 rounded border border-indigo-100"
                  >
                    Global Admin
                  </span>
                </div>

                <Link
                  href="/projects/"
                  class="block px-4 py-2 text-slate-700 hover:bg-slate-50 transition-colors"
                >
                  All Projects
                </Link>

                <Link
                  v-if="currentUser?.is_global_admin"
                  href="/users/"
                  class="block px-4 py-2 text-indigo-600 hover:bg-indigo-50 font-medium transition-colors"
                >
                  User Management
                </Link>

                <button
                  type="button"
                  class="w-full text-left px-4 py-2 text-rose-600 hover:bg-rose-50 font-medium transition-colors border-t border-slate-100 mt-1"
                  @click="logout"
                >
                  Log Out
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </header>


    <!-- Main Content Area -->
    <main class="flex-1 flex flex-col">
      <slot />
    </main>

    <!-- Create Issue Modal (if project is active) -->
    <CreateIssueModal
      v-if="project"
      :show="showCreateModal"
      :project-slug="project.slug"
      :members="members"
      @close="showCreateModal = false"
    />
  </div>
</template>
