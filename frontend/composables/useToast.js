import { reactive } from 'vue';

// Module-level state: one toast stack shared by all components (rendered in AppLayout)
const state = reactive({ items: [] });
let nextId = 1;

const remove = id => {
  const index = state.items.findIndex(t => t.id === id);
  if (index >= 0) state.items.splice(index, 1);
};

const push = ({ message, level = 'success', undoUrl = null, timeout = 6000 }) => {
  if (!message) return null;
  const id = nextId++;
  state.items.push({ id, message, level, undoUrl });
  if (timeout) setTimeout(() => remove(id), timeout);
  return id;
};

/**
 * Show the first message of an Inertia `errors` object as an error toast.
 */
const showErrors = errors => {
  const first = Object.values(errors || {})[0];
  push({ message: first || 'Something went wrong. Please try again.', level: 'error', timeout: 8000 });
};

export function useToast() {
  return { toasts: state.items, push, remove, showErrors };
}
