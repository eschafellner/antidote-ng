<script setup>
import { computed } from 'vue';
import { marked } from 'marked';

const props = defineProps({
  content: {
    type: String,
    default: '',
  },
  placeholder: {
    type: String,
    default: 'No content provided.',
  },
});

// Configure marked options for clean GitHub-flavored markdown
marked.setOptions({
  gfm: true,
  breaks: true,
});

const renderedHtml = computed(() => {
  if (!props.content || !props.content.trim()) {
    return '';
  }
  return marked.parse(props.content);
});
</script>

<template>
  <div
    v-if="renderedHtml"
    class="prose prose-sm prose-slate max-w-none leading-relaxed break-words"
    v-html="renderedHtml"
  ></div>
  <p v-else class="text-xs text-slate-400 italic">
    {{ placeholder }}
  </p>
</template>
