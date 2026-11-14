/** @type {import('vite').UserConfig} */
export default {
  plugins: [],
  base: '/static/',
  build: {
    outDir: '../src/brandly_cli/web/static',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8765',
      '/ws': {
        target: 'http://127.0.0.1:8765',
        ws: true,
      },
    },
  },
};
