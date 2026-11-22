import { defineConfig } from '@playwright/test';

// Browser tests (`pnpm test:e2e`; they need `pnpm exec playwright install chromium --only-shell`).
// - lyrics: the lyrics component on /proba-letra (fixtures only), at fixed sizes.
// - control: the control UI against a real v4 server with a fake worker (e2e/control/serve.py),
//   driven from the keyboard.
const CONTROL = /control\/.*\.spec\.ts/;

export default defineConfig({
	testDir: 'e2e',
	fullyParallel: false,
	workers: 1,
	reporter: 'list',
	use: {
		baseURL: 'http://localhost:5181',
		locale: 'gl-ES',
		// A Chromium installed apart (PLAYWRIGHT_CHROMIUM=/path), when it is not Playwright's own.
		launchOptions: process.env.PLAYWRIGHT_CHROMIUM
			? { executablePath: process.env.PLAYWRIGHT_CHROMIUM }
			: {}
	},
	expect: { toHaveScreenshot: { maxDiffPixelRatio: 0.01 } },
	snapshotPathTemplate: '{testDir}/{testFilePath}-snapshots/{arg}-{platform}{ext}',
	projects: [
		{ name: 'lyrics', testIgnore: [CONTROL] },
		{ name: 'control', testMatch: CONTROL, use: { viewport: { width: 1440, height: 900 } } }
	],
	webServer: [
		{
			command: 'uv run --project .. python e2e/control/serve.py',
			url: 'http://127.0.0.1:8799/api/server',
			reuseExistingServer: false,
			timeout: 60_000
		},
		{
			command: 'pnpm exec vite dev --port 5181 --strictPort',
			url: 'http://localhost:5181/',
			reuseExistingServer: true,
			env: { KARAOKE_SERVER: 'http://127.0.0.1:8799' }
		}
	]
});
