import { createApp, h } from 'vue';
import { createInertiaApp } from '@inertiajs/vue3';
import './css/app.css';

createInertiaApp({
  resolve: name => {
    const pages = import.meta.glob('./Pages/**/*.vue', { eager: true });
    const page = pages[`./Pages/${name}.vue`];
    if (!page) {
      throw new Error(`Inertia page component "./Pages/${name}.vue" was not found.`);
    }
    return page.default || page;
  },
  setup({ el, App, props, plugin }) {
    createApp({ render: () => h(App, props) })
      .use(plugin)
      .mount(el);
  },
});
