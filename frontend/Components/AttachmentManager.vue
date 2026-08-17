<script setup>
import { ref } from 'vue';
import { useForm, router } from '@inertiajs/vue3';

const props = defineProps({
  projectSlug: {
    type: String,
    required: true,
  },
  issueKey: {
    type: String,
    required: true,
  },
  attachments: {
    type: Array,
    default: () => [],
  },
  canUpload: {
    type: Boolean,
    default: true,
  },
});

const isDragging = ref(false);
const uploadError = ref('');
const fileInputRef = ref(null);

const form = useForm({
  file: null,
});

const allowedExtensions = ['pdf', 'txt', 'md', 'csv', 'json', 'docx', 'xlsx', 'zip', 'log', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'];
const maxSizeBytes = 10 * 1024 * 1024; // 10MB

const validateAndUpload = file => {
  uploadError.value = '';
  if (!file) return;

  const ext = file.name.split('.').pop().toLowerCase();
  if (!allowedExtensions.includes(ext)) {
    uploadError.value = `File type '.${ext}' is not allowed. Supported: ${allowedExtensions.join(', ')}`;
    return;
  }

  if (file.size > maxSizeBytes) {
    uploadError.value = `File exceeds max allowed size of 10 MB.`;
    return;
  }

  form.file = file;
  form.post(`/projects/${props.projectSlug}/issues/${props.issueKey}/attachments/`, {
    preserveScroll: true,
    forceFormData: true,
    onSuccess: () => {
      form.reset();
      if (fileInputRef.value) fileInputRef.value.value = '';
    },
    onError: errors => {
      uploadError.value = errors.file || 'Failed to upload file.';
    },
  });
};

const handleDrop = e => {
  isDragging.value = false;
  const files = e.dataTransfer?.files;
  if (files && files.length > 0) {
    validateAndUpload(files[0]);
  }
};

const handleFileInputChange = e => {
  const files = e.target.files;
  if (files && files.length > 0) {
    validateAndUpload(files[0]);
  }
};

const deleteAttachment = attachmentId => {
  if (confirm('Are you sure you want to delete this attachment?')) {
    router.post(
      `/projects/${props.projectSlug}/issues/${props.issueKey}/attachments/${attachmentId}/delete/`,
      {},
      { preserveScroll: true }
    );
  }
};

const formatSize = bytes => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
};

const isImage = filename => {
  const ext = filename.split('.').pop().toLowerCase();
  return ['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(ext);
};
</script>

<template>
  <div class="space-y-4">
    <!-- Drag & Drop Upload Zone (if user can upload) -->
    <div
      v-if="canUpload"
      :class="[
        'relative rounded-xl border-2 border-dashed p-4 text-center transition-all cursor-pointer',
        isDragging
          ? 'border-indigo-500 bg-indigo-50/60'
          : 'border-slate-300 hover:border-indigo-400 bg-slate-50/40 hover:bg-slate-50',
      ]"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="handleDrop"
      @click="fileInputRef?.click()"
    >
      <input
        ref="fileInputRef"
        type="file"
        class="hidden"
        @change="handleFileInputChange"
      />

      <div class="flex flex-col items-center justify-center gap-1.5 text-xs text-slate-500">
        <div class="w-8 h-8 rounded-full bg-white shadow-2xs flex items-center justify-center text-indigo-600">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
          </svg>
        </div>
        <p class="font-medium text-slate-700">
          <span class="text-indigo-600 font-semibold">Click to upload</span> or drag and drop
        </p>
        <p class="text-[11px] text-slate-400">
          PNG, JPG, PDF, ZIP, DOCX, CSV up to 10MB
        </p>
      </div>

      <!-- Uploading spinner -->
      <div
        v-if="form.processing"
        class="absolute inset-0 bg-white/80 backdrop-blur-xs flex items-center justify-center rounded-xl"
      >
        <span class="text-xs font-semibold text-indigo-600 flex items-center gap-2">
          <svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          Uploading...
        </span>
      </div>
    </div>

    <!-- Error notice -->
    <p v-if="uploadError" class="text-xs text-rose-600 font-medium">
      {{ uploadError }}
    </p>

    <!-- Attachments Grid -->
    <div v-if="attachments.length > 0" class="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <div
        v-for="att in attachments"
        :key="att.id"
        class="group relative flex items-center gap-3 p-2.5 rounded-lg border border-slate-200 bg-white hover:border-slate-300 shadow-2xs transition-all"
      >
        <!-- Thumbnail or Icon -->
        <div class="w-12 h-12 rounded-md bg-slate-100 flex-shrink-0 flex items-center justify-center overflow-hidden border border-slate-200/60">
          <img
            v-if="isImage(att.filename)"
            :src="att.url"
            :alt="att.filename"
            class="w-full h-full object-cover"
          />
          <svg v-else class="w-6 h-6 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>

        <!-- Meta -->
        <div class="min-w-0 flex-1">
          <a
            :href="att.url"
            target="_blank"
            rel="noopener noreferrer"
            class="text-xs font-semibold text-slate-900 hover:text-indigo-600 truncate block transition-colors"
            :title="att.filename"
          >
            {{ att.filename }}
          </a>
          <p class="text-[11px] text-slate-400 mt-0.5">
            {{ formatSize(att.file_size) }} &bull; by {{ att.uploaded_by.username }}
          </p>
        </div>

        <!-- Actions -->
        <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <a
            :href="att.url"
            target="_blank"
            download
            class="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-100"
            title="Download"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
          </a>
          <button
            v-if="att.can_delete"
            type="button"
            class="p-1 rounded text-slate-400 hover:text-rose-600 hover:bg-rose-50"
            title="Delete attachment"
            @click="deleteAttachment(att.id)"
          >
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>
    </div>
    <div v-else-if="!canUpload" class="text-xs text-slate-400 italic">
      No attachments uploaded.
    </div>
  </div>
</template>
