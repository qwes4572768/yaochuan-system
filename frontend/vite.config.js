import path from 'path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            '@': path.resolve(__dirname, './src'),
        },
    },
    server: {
        host: true,
        port: 5173,
        allowedHosts: true,
        proxy: {
            '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
            '/uploads': { target: 'http://127.0.0.1:8000', changeOrigin: true },
        },
    },
});
