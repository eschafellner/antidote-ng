<script setup>
import { onMounted } from 'vue';
import { router } from '@inertiajs/vue3';

const props = defineProps({
  project: {
    type: Object,
    required: true,
  },
});

onMounted(() => {
  router.visit(`/projects/${props.project.slug}/board/`);
});
</script>

<template>
  <div class="min-h-screen bg-slate-50 flex items-center justify-center text-slate-500 text-sm">
    Redirecting to board...
  </div>
</template>
