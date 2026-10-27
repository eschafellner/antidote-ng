<script setup>
import { computed } from 'vue';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

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

const escapeHtml = value =>
  String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');

// Custom renderer: raw HTML is escaped, every interpolated value is escaped,
// and only safe URL schemes are allowed.
const renderer = {
  html({ text }) {
    return escapeHtml(text);
  },
  link({ href, title, tokens }) {
    const cleanHref = href && /^(https?:\/\/|mailto:|\/)/i.test(href) ? href : '#';
    const titleAttr = title ? ` title="${escapeHtml(title)}"` : '';
    // Render link text via the inline parser so nested raw HTML passes through the html() renderer above
    const inner = this.parser.parseInline(tokens);
    return `<a href="${escapeHtml(cleanHref)}" target="_blank" rel="noopener noreferrer"${titleAttr} class="text-indigo-600 hover:text-indigo-800 underline">${inner}</a>`;
  },
  image({ href, title, text }) {
    const cleanHref = href && /^(https?:\/\/|\/)/i.test(href) ? href : '';
    const titleAttr = title ? ` title="${escapeHtml(title)}"` : '';
    return `<img src="${escapeHtml(cleanHref)}" alt="${escapeHtml(text)}"${titleAttr} class="max-w-full rounded-lg my-2 border border-slate-200" />`;
  },
};

marked.use({ renderer, gfm: true, breaks: true });

const renderedHtml = computed(() => {
  if (!props.content || !props.content.trim()) {
    return '';
  }
  // Defense in depth: sanitize the final HTML in addition to the escaping renderer
  return DOMPurify.sanitize(marked.parse(props.content), { ADD_ATTR: ['target'] });
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
