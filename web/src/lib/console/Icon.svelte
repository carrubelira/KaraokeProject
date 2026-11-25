<script lang="ts" module>
	/** Line icons used across the control (24×24, 1.6 stroke): one place for every glyph. */
	const PATHS = {
		playback: 'M4 6h16v12H4zM10 9.5v5l4-2.5z',
		add: 'M12 5v14M5 12h14',
		jobs: 'M4 6h10M4 12h16M4 18h7M17 4l3 2-3 2M15 16l3 2-3 2',
		library: 'M5 4v16M9 4v16M13 5l5 15M3 20h18',
		devices:
			'M6 6m-2 0a2 2 0 1 0 4 0 2 2 0 1 0-4 0M18 6m-2 0a2 2 0 1 0 4 0 2 2 0 1 0-4 0M12 18m-2 0a2 2 0 1 0 4 0 2 2 0 1 0-4 0M8 6h8M7 8l4 8M17 8l-4 8',
		outputs: 'M4 9v6h4l5 4V5L8 9zM17 9a4 4 0 0 1 0 6M19.5 6.5a8 8 0 0 1 0 11',
		settings:
			'M4 7h9M17 7h3M4 17h3M11 17h9M15 7m-2 0a2 2 0 1 0 4 0 2 2 0 1 0-4 0M9 17m-2 0a2 2 0 1 0 4 0 2 2 0 1 0-4 0',
		play: 'M8 5l11 7-11 7z',
		pause: 'M7 5h3v14H7zM14 5h3v14h-3z',
		next: 'M6 5l9 7-9 7zM17 5v14',
		previous: 'M18 5l-9 7 9 7zM7 5v14',
		stop: 'M6 6h12v12H6z',
		search: 'M10.5 10.5m-6 0a6 6 0 1 0 12 0 6 6 0 1 0-12 0M15 15l5 5',
		up: 'M6 15l6-6 6 6',
		down: 'M6 9l6 6 6-6',
		close: 'M6 6l12 12M18 6L6 18',
		retry: 'M4 12a8 8 0 0 1 14-5.3M20 4v5h-5M20 12a8 8 0 0 1-14 5.3M4 20v-5h5',
		link: 'M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1',
		file: 'M7 3h7l5 5v13H7zM14 3v5h5',
		check: 'M5 12l5 5L20 7',
		warn: 'M12 4l9 16H3zM12 10v4M12 17v.5',
		log: 'M5 5h14M5 9h14M5 13h9M5 17h11',
		edit: 'M4 20h4L19 9l-4-4L4 16zM13.5 6.5l4 4',
		export: 'M12 4v11M7 10l5 5 5-5M5 20h14',
		trash: 'M5 7h14M10 7V4h4v3M7 7l1 13h8l1-13',
		grip: 'M9 6h.01M15 6h.01M9 12h.01M15 12h.01M9 18h.01M15 18h.01',
		mic: 'M12 4a3 3 0 0 0-3 3v5a3 3 0 0 0 6 0V7a3 3 0 0 0-3-3M6 11a6 6 0 0 0 12 0M12 17v3',
		gpu: 'M4 7h16v10H4zM8 7V4M12 7V4M16 7V4M8 17v3M12 17v3M16 17v3M8 10h8v4H8z',
		screen: 'M3 5h18v12H3zM8 21h8',
		bolt: 'M13 3L5 13h6l-1 8 8-10h-6z',
		volume: 'M4 9v6h4l5 4V5L8 9z',
		logout: 'M10 4H5v16h5M14 8l4 4-4 4M18 12H9',
		chevron: 'M9 6l6 6-6 6'
	} as const;
	export type IconName = keyof typeof PATHS;
</script>

<script lang="ts">
	let { name, size = 18, label }: { name: IconName; size?: number; label?: string } = $props();
</script>

<svg
	width={size}
	height={size}
	viewBox="0 0 24 24"
	fill="none"
	stroke="currentColor"
	stroke-width="1.6"
	stroke-linecap="round"
	stroke-linejoin="round"
	role={label ? 'img' : undefined}
	aria-label={label}
	aria-hidden={label ? undefined : 'true'}
>
	<path d={PATHS[name]} />
</svg>
