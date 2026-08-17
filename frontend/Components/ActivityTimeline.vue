<script setup>
import UserAvatar from './UserAvatar.vue';

defineProps({
  activities: {
    type: Array,
    default: () => [],
  },
});

const formatTime = dateStr => {
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
  <div class="space-y-4">
    <div v-if="activities.length > 0" class="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
      <div
        v-for="act in activities"
        :key="act.id"
        class="relative flex items-start gap-3 text-xs"
      >
        <!-- Timeline node dot -->
        <div class="absolute -left-6 top-1 w-5 h-5 rounded-full bg-white border-2 border-indigo-500 flex items-center justify-center">
          <div class="w-1.5 h-1.5 rounded-full bg-indigo-600"></div>
        </div>

        <div class="min-w-0 flex-1 bg-white p-3 rounded-lg border border-slate-200/80 shadow-2xs">
          <div class="flex items-center justify-between gap-2 mb-1">
            <span class="font-bold text-slate-900">
              {{ act.actor ? (act.actor.first_name ? `${act.actor.first_name} ${act.actor.last_name}` : act.actor.username) : 'System' }}
            </span>
            <span class="text-[11px] text-slate-400">
              {{ formatTime(act.created_at) }}
            </span>
          </div>

          <!-- Action Description -->
          <div class="text-slate-600">
            <template v-if="act.action === 'created'">
              created this issue
            </template>
            <template v-else-if="act.action === 'status_changed'">
              changed status from
              <span class="font-semibold text-slate-800 uppercase text-[11px] px-1.5 py-0.5 bg-slate-100 rounded">{{ act.old_value }}</span>
              to
              <span class="font-semibold text-indigo-700 uppercase text-[11px] px-1.5 py-0.5 bg-indigo-50 rounded">{{ act.new_value }}</span>
            </template>
            <template v-else-if="act.action === 'priority_changed'">
              changed priority from
              <span class="font-semibold text-slate-800 uppercase text-[11px] px-1.5 py-0.5 bg-slate-100 rounded">{{ act.old_value }}</span>
              to
              <span class="font-semibold text-orange-700 uppercase text-[11px] px-1.5 py-0.5 bg-orange-50 rounded">{{ act.new_value }}</span>
            </template>
            <template v-else-if="act.action === 'assignee_changed'">
              changed assignee from
              <strong class="text-slate-800">{{ act.old_value }}</strong> to <strong class="text-slate-800">{{ act.new_value }}</strong>
            </template>
            <template v-else-if="act.action === 'attachment_added'">
              attached file <code class="font-mono text-[11px] text-slate-800 bg-slate-100 px-1 py-0.5 rounded">{{ act.new_value }}</code>
            </template>
            <template v-else-if="act.action === 'attachment_removed'">
              removed attachment <code class="font-mono text-[11px] text-slate-800 bg-slate-100 px-1 py-0.5 rounded">{{ act.old_value }}</code>
            </template>
            <template v-else-if="act.action === 'comment_added'">
              added a comment
            </template>
            <template v-else-if="act.action === 'soft_deleted'">
              soft-deleted this issue
            </template>
            <template v-else-if="act.action === 'restored'">
              restored this issue
            </template>
            <template v-else>
              updated <code class="font-mono text-slate-700">{{ act.field_changed }}</code>
            </template>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="text-xs text-slate-400 italic py-2">
      No activity recorded yet.
    </div>
  </div>
</template>
