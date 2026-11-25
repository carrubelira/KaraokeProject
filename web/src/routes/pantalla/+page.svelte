<script lang="ts">
	/*
	 * A screen (decision 011): open it in any browser on the LAN, or in the Tauri kiosk with
	 * `?kiosk` (no full-screen button) and `?screen=<id>` (one per monitor). `?preview` is a screen
	 * the stage shows but never waits for.
	 */
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import Screen from '#lib/screen/Screen.svelte';
	import { ScreenRuntime } from '#lib/screen/runtime.svelte.js';

	const params = page.url.searchParams;
	const runtime = new ScreenRuntime({ preview: params.has('preview') });
	const kiosk = params.has('kiosk');

	onMount(() => {
		void runtime.start();
		return () => runtime.stop();
	});
</script>

<svelte:head>
	<title>Karaoke</title>
</svelte:head>

<Screen {runtime} {kiosk} />
