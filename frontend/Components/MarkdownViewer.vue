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

// Custom renderer to sanitize raw HTML tags and unsafe URLs in Markdown input
const renderer = {
  html({ text }) {
    // Escape raw HTML tags to prevent XSS attacks
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  },
  link({ href, title, text }) {
    // Block dangerous schemes like javascript:
    const cleanHref = href && /^(https?:\/\/|mailto:|\/)/i.test(href) ? href : '#';
    const titleAttr = title ? ` title="${title}"` : '';
    return `<a href="${cleanHref}" target="_blank" rel="noopener noreferrer"${titleAttr} class="text-indigo-600 hover:text-indigo-800 underline">${text}</a>`;
  },
  image({ href, title, text }) {
    // Block dangerous schemes like javascript:
    const cleanHref = href && /^(https?:\/\/|data:image\/|\/)/i.test(href) ? href : '';
    const titleAttr = title ? ` title="${title}"` : '';
    return `<img src="${cleanHref}" alt="${text}"${titleAttr} class="max-w-full rounded-lg my-2 border border-slate-200" />`;
  },
};

marked.use({ renderer, gfm: true, breaks: true });

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
