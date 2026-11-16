export default {
  compilerOptions: {
    runes: true
  },
  onwarn(warning, handler) {
    if (warning.code.startsWith('a11y_')) return;
    handler(warning);
  }
};
