<script setup>
import { ref } from 'vue';
import MarkdownViewer from './MarkdownViewer.vue';

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  placeholder: {
    type: String,
    default: 'Write your description or comment in Markdown...',
  },
  rows: {
    type: Number,
    default: 4,
  },
});

const emit = defineEmits(['update:modelValue']);

const activeTab = ref('write'); // 'write' | 'preview'
const textareaRef = ref(null);

const insertSnippet = (prefix, suffix = '') => {
  const textarea = textareaRef.value;
  if (!textarea) return;

  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const text = props.modelValue;
  const selected = text.substring(start, end) || 'text';
  const replacement = `${prefix}${selected}${suffix}`;

  const updated = text.substring(0, start) + replacement + text.substring(end);
  emit('update:modelValue', updated);

  setTimeout(() => {
    textarea.focus();
    textarea.setSelectionRange(
      start + prefix.length,
      start + prefix.length + selected.length
    );
  }, 0);
};
</script>

<template>
  <div class="rounded-xl border border-slate-300 focus-within:border-indigo-500 focus-within:ring-1 focus-within:ring-indigo-500 bg-white overflow-hidden shadow-2xs transition-all">
    <!-- Editor Header & Toolbar -->
    <div class="flex items-center justify-between px-3 py-1.5 bg-slate-50/80 border-b border-slate-200/80 text-xs">
      <!-- Write / Preview Tabs -->
      <div class="flex items-center gap-1">
        <button
          type="button"
          :class="[
            'px-2.5 py-1 rounded-md font-semibold transition-colors',
            activeTab === 'write'
              ? 'bg-white text-slate-900 shadow-2xs border border-slate-200'
              : 'text-slate-500 hover:text-slate-700 hover:bg-slate-100',
          ]"
          @click="activeTab = 'write'"
        >
          Write
        </button>
        <button
          type="button"
          :class="[
            'px-2.5 py-1 rounded-md font-semibold transition-colors',
            activeTab === 'preview'
              ? 'bg-white text-slate-900 shadow-2xs border border-slate-200'
              : 'text-slate-500 hover:text-slate-700 hover:bg-slate-100',
          ]"
          @click="activeTab = 'preview'"
        >
          Preview
        </button>
      </div>

      <!-- Formatting Shortcuts (Visible in write mode) -->
      <div v-if="activeTab === 'write'" class="flex items-center gap-1 text-slate-500">
        <button
          type="button"
          class="p-1 hover:bg-slate-200/60 rounded font-bold"
          title="Bold (**text**)"
          @click="insertSnippet('**', '**')"
        >
          B
        </button>
        <button
          type="button"
          class="p-1 hover:bg-slate-200/60 rounded italic font-serif"
          title="Italic (*text*)"
          @click="insertSnippet('*', '*')"
        >
          I
        </button>
        <button
          type="button"
          class="p-1 hover:bg-slate-200/60 rounded font-mono text-[11px]"
          title="Code (`code`)"
          @click="insertSnippet('`', '`')"
        >
          &lt;/&gt;
        </button>
        <button
          type="button"
          class="p-1 hover:bg-slate-200/60 rounded text-[11px]"
          title="Quote (> quote)"
          @click="insertSnippet('> ')"
        >
          &ldquo;&rdquo;
        </button>
        <button
          type="button"
          class="p-1 hover:bg-slate-200/60 rounded text-[11px]"
          title="List (- item)"
          @click="insertSnippet('- ')"
        >
          &bull;&mdash;
        </button>
      </div>
    </div>

    <!-- Write Mode: Textarea -->
    <div v-show="activeTab === 'write'" class="p-2">
      <textarea
        ref="textareaRef"
        :value="modelValue"
        :rows="rows"
        :placeholder="placeholder"
        class="w-full border-0 focus:ring-0 text-sm text-slate-900 placeholder:text-slate-400 font-mono text-xs resize-y"
        @input="emit('update:modelValue', $event.target.value)"
      ></textarea>
    </div>

    <!-- Preview Mode -->
    <div v-show="activeTab === 'preview'" class="p-3.5 min-h-[100px] bg-slate-50/30">
      <MarkdownViewer :content="modelValue" placeholder="Nothing to preview yet." />
    </div>
  </div>
</template>
