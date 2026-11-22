<script lang="ts">
	/** The control's icons: one stroke weight, a 20 px grid, drawn here so they all match. */
	export type IconName =
		| 'home'
		| 'live'
		| 'library'
		| 'create'
		| 'jobs'
		| 'machines'
		| 'outputs'
		| 'settings'
		| 'close'
		| 'play'
		| 'pause'
		| 'previous'
		| 'next'
		| 'back'
		| 'forward'
		| 'plus'
		| 'copy';

	let { name, size = 18 }: { name: IconName; size?: number } = $props();

	const PATHS: Record<IconName, string> = {
		home: 'M3 9.5 10 4l7 5.5V16a1 1 0 0 1-1 1h-3.5v-4.5h-5V17H4a1 1 0 0 1-1-1z',
		live: 'M10 12.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5M5.8 14.2a6 6 0 0 1 0-8.4M14.2 5.8a6 6 0 0 1 0 8.4M3.3 16.7a9.5 9.5 0 0 1 0-13.4M16.7 3.3a9.5 9.5 0 0 1 0 13.4',
		library:
			'M4 4.5h12M4 8.5h12M4 12.5h6M14 11v5.5M14 16.5a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0M14 11l3 1',
		create: 'M10 4v12M4 10h12',
		jobs: 'M3.5 5h13M3.5 10h13M3.5 15h8M14.5 13.5l1.5 1.5 3-3',
		machines:
			'M3.5 4h13a.5.5 0 0 1 .5.5v4a.5.5 0 0 1-.5.5h-13a.5.5 0 0 1-.5-.5v-4a.5.5 0 0 1 .5-.5M3.5 11h13a.5.5 0 0 1 .5.5v4a.5.5 0 0 1-.5.5h-13a.5.5 0 0 1-.5-.5v-4a.5.5 0 0 1 .5-.5M6 6.5h.01M6 13.5h.01',
		outputs: 'M4 7.5h3l4-3.5v12l-4-3.5H4zM14 7a4 4 0 0 1 0 6M16 5a7 7 0 0 1 0 10',
		settings: 'M4 5h7M15 5h1M4 10h2M10 10h6M4 15h9M17 15h-1M13 3.5v3M8 8.5v3M15 13.5v3',
		close: 'M5 5l10 10M15 5 5 15',
		play: 'M6.5 4.5v11l9-5.5z',
		pause: 'M6.5 4.5v11M13.5 4.5v11',
		previous: 'M5 4.5v11M15 4.5v11l-8-5.5z',
		next: 'M15 4.5v11M5 4.5v11l8-5.5z',
		back: 'M9 5 4 10l5 5M4 10h12',
		forward: 'M11 5l5 5-5 5M16 10H4',
		plus: 'M10 4v12M4 10h12',
		copy: 'M7 7h9v9H7zM4 13V4h9'
	};
</script>

<svg
	class="icon"
	width={size}
	height={size}
	viewBox="0 0 20 20"
	fill="none"
	stroke="currentColor"
	stroke-width="1.5"
	stroke-linecap="round"
	stroke-linejoin="round"
	aria-hidden="true"><path d={PATHS[name]} /></svg
>

<style>
	.icon {
		flex: none;
	}
</style>
