import { vitePreprocess } from "@sveltejs/vite-plugin-svelte";

// TypeScript in Svelte-Bausteinen (lang="ts") über Vite; Runen überall. Hinweise zur Barrierefreiheit meldet svelte-check,
// im Bau bleiben sie still, bis die alten Bereiche neu gebaut sind (Etappen 3, 4 und 6).
export default {
  preprocess: vitePreprocess(),
  compilerOptions: { runes: true },
  onwarn(warning, handler) {
    if (warning.code.startsWith("a11y_")) return;
    handler(warning);
  },
};
