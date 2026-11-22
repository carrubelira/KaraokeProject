<script lang="ts">
	/*
	 * What a web screen shows (decision 011): the video (two elements taking turns), the lyrics
	 * over it, and between songs a waiting screen with who sings next and how the download goes.
	 * The runtime decides; this only draws its state.
	 */
	import { onMount } from 'svelte';
	import { i18n } from '#lib/i18n';
	import { DEFAULT_THEME, Lyrics, THEMES } from '#lib/lyrics';
	import type { ScreenRuntime } from './runtime.svelte';

	let { runtime, kiosk = false }: { runtime: ScreenRuntime; kiosk?: boolean } = $props();

	let first = $state<HTMLVideoElement>();
	let second = $state<HTMLVideoElement>();

	onMount(() => {
		if (first && second) runtime.attach(first, second);
	});

	const t = $derived(i18n.t.screen);
	const theme = $derived(THEMES[runtime.config.theme] ?? THEMES[DEFAULT_THEME]);
	const layout = $derived(runtime.config.layout);
	const showsVideo = $derived(layout === 'video-lyrics' || layout === 'video');
	const showsLyrics = $derived(layout === 'video-lyrics' || layout === 'lyrics');
	const session = $derived(runtime.model.session);
	const phase = $derived(runtime.model.state);
	const program = $derived(session?.current ?? null);
	const song = $derived(runtime.song);
	/** The song on screen is the session's (not the previous one while the next is looked up). */
	const onScreen = $derived(!!song && song.program.manifest === program?.manifest);
	/** Between songs: nothing on yet, or cued and waiting for the operator at its start. */
	const between = $derived(
		phase === 'connecting' ||
			phase === 'idle' ||
			phase === 'provisioning' ||
			(phase === 'syncing' && !onScreen) ||
			(phase === 'waiting' && session?.state !== 'playing' && session?.state !== 'paused')
	);
	const title = $derived(program ? runtime.titles[program.manifest] : undefined);
	const download = $derived(program ? runtime.progress[program.manifest] : undefined);
	const next = $derived(session?.upcoming[0] ?? null);
	const nextTitle = $derived(next ? runtime.titles[next.manifest] : undefined);

	function goFullscreen() {
		void document.documentElement.requestFullscreen?.().catch(() => {});
	}
</script>

<div class="screen" class:between>
	<video
		bind:this={first}
		muted
		playsinline
		preload="auto"
		class:shown={showsVideo && onScreen && runtime.active === 0 && !!song?.video}
	></video>
	<video
		bind:this={second}
		muted
		playsinline
		preload="auto"
		class:shown={showsVideo && onScreen && runtime.active === 1 && !!song?.video}
	></video>

	{#if showsLyrics && onScreen && song?.doc && !between}
		<div class="lyrics"><Lyrics doc={song.doc} {theme} clock={runtime.lyricsClock} /></div>
	{/if}

	{#if phase === 'error'}
		<div class="card error" role="alert">
			<p class="big">{t.error}</p>
			<p>{runtime.model.error}</p>
			<button type="button" onclick={() => location.reload()}>{t.reload}</button>
		</div>
	{:else if between}
		<div class="card" aria-live="polite">
			{#if phase === 'connecting'}
				<p class="big">{t.connecting}</p>
			{:else if !program}
				<p class="big">{t.nothing}</p>
				{#if next}
					<p class="next">{t.next}: {nextTitle?.title ?? '…'}</p>
				{/if}
			{:else}
				<p class="label">{t.upNow}</p>
				{#if program.item.singer}<p class="singer">{program.item.singer}</p>{/if}
				<p class="big">{title?.title ?? '…'}</p>
				{#if title?.artist}<p class="artist">{title.artist}</p>{/if}
				{#if phase === 'provisioning'}
					<div class="progress" aria-label={t.downloading}>
						<span style:width="{Math.round((download?.fraction ?? 0) * 100)}%"></span>
					</div>
					{#if runtime.model.error}<p class="warn">{runtime.model.error}</p>{/if}
				{:else if phase === 'syncing'}
					<p class="muted">{t.preparing}</p>
				{:else}
					<p class="muted">{t.ready}</p>
				{/if}
				{#if next}
					<p class="next">{t.next}: {nextTitle?.title ?? '…'}</p>
				{/if}
			{/if}
		</div>
	{/if}

	{#if phase === 'paused'}<p class="badge">{t.paused}</p>{/if}
	{#if !runtime.connected && phase !== 'connecting'}<p class="badge offline">{t.offline}</p>{/if}
	{#if !kiosk && !runtime.fullscreen && !runtime.preview}
		<button type="button" class="fullscreen" onclick={goFullscreen}>{t.fullscreen}</button>
	{/if}
</div>

<style>
	.screen {
		position: fixed;
		inset: 0;
		overflow: hidden;
		background: #000;
		color: #f4f1ea;
		font-family: 'IBM Plex Sans', system-ui, sans-serif;
		cursor: none;
	}
	video {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		object-fit: contain;
		visibility: hidden;
	}
	video.shown {
		visibility: visible;
	}
	.lyrics {
		position: absolute;
		inset: 0;
	}
	.card {
		position: absolute;
		inset: 0;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.6vmin;
		padding: 6vmin;
		text-align: center;
		background: radial-gradient(circle at 50% 40%, #1b2230, #07090d 70%);
	}
	.label {
		font-size: 2.4vmin;
		letter-spacing: 0.2em;
		text-transform: uppercase;
		color: #e8b04a;
	}
	.singer {
		font-size: 7vmin;
		font-weight: 700;
	}
	.big {
		font-size: 5vmin;
		font-weight: 600;
		text-wrap: balance;
	}
	.artist,
	.muted {
		font-size: 3vmin;
		color: #a9b0bc;
	}
	.next {
		position: absolute;
		bottom: 5vmin;
		font-size: 2.6vmin;
		color: #a9b0bc;
	}
	.warn {
		font-size: 2.2vmin;
		color: #e8b04a;
	}
	.progress {
		width: min(60vw, 900px);
		height: 1vmin;
		margin-top: 3vmin;
		border-radius: 1vmin;
		background: #2a3140;
		overflow: hidden;
	}
	.progress span {
		display: block;
		height: 100%;
		background: #e8b04a;
		transition: width 0.3s;
	}
	.error .big {
		color: #ff8a7a;
	}
	.badge {
		position: absolute;
		top: 3vmin;
		right: 3vmin;
		padding: 0.6vmin 1.6vmin;
		border-radius: 1vmin;
		background: rgb(0 0 0 / 0.6);
		font-size: 2.2vmin;
	}
	.badge.offline {
		top: auto;
		bottom: 3vmin;
		color: #e8b04a;
	}
	button {
		cursor: pointer;
		font: inherit;
	}
	.fullscreen {
		position: absolute;
		top: 3vmin;
		left: 3vmin;
		padding: 1vmin 2.4vmin;
		border: 1px solid #4a5263;
		border-radius: 1vmin;
		background: rgb(0 0 0 / 0.7);
		color: inherit;
		font-size: 2vmin;
	}
	.screen:not(.between) .fullscreen {
		opacity: 0.4;
	}
</style>
