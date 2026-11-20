import type { KnipConfig } from 'knip';

// Dead code check for the web app (part of `pnpm lint`). SvelteKit 3 has no svelte.config.js, so
// the entry points are listed here: routes, the dev scripts and the tests.
const config: KnipConfig = {
	entry: [
		'src/routes/**/+{page,layout,error}{,.server}.{ts,svelte}',
		'dev/**/*.{ts,mjs}',
		'e2e/**/*.{ts,mjs}',
		'scripts/**/*.mjs',
		'src/**/*.test.ts'
	],
	project: ['src/**/*.{ts,svelte}', 'dev/**/*.{ts,mjs}', 'e2e/**/*.{ts,mjs}', 'scripts/**/*.mjs'],
	// Generated from the schemas: every contract, used or not yet.
	ignore: ['src/lib/contracts/generated/**', 'src/lib/control/generated/**'],
	// SvelteKit's virtual modules exist only inside its build.
	ignoreUnresolved: [/^\$app\//],
	// A type or constant exported next to the code that uses it is documentation, not dead code.
	ignoreExportsUsedInFile: true
};

export default config;
