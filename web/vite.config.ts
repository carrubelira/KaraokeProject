import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vitest/config';
import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';

const ROOT = resolve(fileURLToPath(new URL('.', import.meta.url)), '..');
// `pnpm dev` talks to a real v4 server (`karaoke-server serve`), by default on this
// machine; WebSockets and Range go through the proxy as they are.
const SERVER = process.env.KARAOKE_SERVER ?? 'http://127.0.0.1:8765';

export default defineConfig({
	// The lyrics themes and fonts live in the Python package, outside web/.
	server: {
		fs: { allow: [ROOT] },
		proxy: { '/api': { target: SERVER, changeOrigin: false, ws: true, secure: false } }
	},
	plugins: [
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},
			adapter: adapter({ fallback: 'index.html' })
		})
	],
	test: {
		expect: { requireAssertions: true },
		projects: [
			{
				extends: './vite.config.ts',
				test: {
					name: 'server',
					environment: 'node',
					include: ['src/**/*.{test,spec}.{js,ts}'],
					exclude: ['src/**/*.svelte.{test,spec}.{js,ts}']
				}
			}
		]
	}
});
