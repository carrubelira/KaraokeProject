<script lang="ts">
	/*
	 * The console (plan v4 §7, docs/web.md): a live 3D signal field behind a broadcast desk. The
	 * strip on top says which screen is driven and how the system is; the rail on the left opens
	 * the sections; the deck at the bottom keeps the transport at hand everywhere. Every key goes
	 * through the command registry. A link pasted or a file dropped anywhere is analysed at once.
	 */
	import '../lib/ui/styles/fonts.css';
	import '../lib/ui/styles/console.css';
	import favicon from '#lib/assets/favicon.svg';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import { commands } from '#lib/commands/registry.svelte.js';
	import { isTyping } from '#lib/commands/keys.js';
	import Deck from '#lib/console/Deck.svelte';
	import Rail from '#lib/console/Rail.svelte';
	import Scene from '#lib/console/scene/Scene.svelte';
	import Strip from '#lib/console/Strip.svelte';
	import { api, ApiError } from '#lib/control/api.js';
	import { live } from '#lib/control/live.svelte.js';
	import { toasts } from '#lib/control/toasts.svelte.js';
	import type { Session } from '#lib/control/types.js';
	import { i18n, initLocale } from '#lib/i18n';
	import Cheatsheet from '#lib/shell/Cheatsheet.svelte';
	import { registerGlobal } from '#lib/shell/global.js';
	import { intake, looksLikeLink } from '#lib/shell/intake.svelte.js';
	import Login from '#lib/shell/Login.svelte';
	import Palette from '#lib/shell/Palette.svelte';
	import { prefs } from '#lib/shell/prefs.svelte.js';
	import Toasts from '#lib/shell/Toasts.svelte';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();
	let session = $state<Session | null>(null);
	let checked = $state(false);
	let dragging = $state(false);

	initLocale();

	function start(found: Session) {
		session = found;
		prefs.load(found.preferences);
		live.start();
	}

	onMount(() => {
		const unregister = registerGlobal();
		api
			.session()
			.then(start)
			.catch((error: unknown) => {
				if (!(error instanceof ApiError && error.status === 401))
					toasts.show(String(error), 'error');
			})
			.finally(() => (checked = true));
		return () => {
			unregister();
			live.stop();
		};
	});

	function keydown(event: KeyboardEvent) {
		if (!session) return;
		commands.handle(event);
	}

	function paste(event: ClipboardEvent) {
		if (!session || isTyping(event.target)) return;
		const text = event.clipboardData?.getData('text') ?? '';
		if (looksLikeLink(text)) {
			event.preventDefault();
			toasts.show(i18n.t.app.pasted);
			void intake.link(text.trim()).then(() => goto(resolve('/engadir')));
		}
	}

	function drop(event: DragEvent) {
		event.preventDefault();
		dragging = false;
		if (session && event.dataTransfer?.files.length) {
			void goto(resolve('/engadir'));
			void intake.files(event.dataTransfer.files);
		}
	}
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>{i18n.t.app.name} · Karaoke</title>
</svelte:head>

<svelte:window
	onkeydown={keydown}
	onpaste={paste}
	ondragover={(e) => {
		if (session && e.dataTransfer?.types.includes('Files')) {
			e.preventDefault();
			dragging = true;
		}
	}}
	ondragleave={(e) => e.relatedTarget === null && (dragging = false)}
	ondrop={drop}
/>

{#if page.route.id === '/proba-letra'}
	<!-- A development test page for the lyrics, outside the console. -->
	{@render children()}
{:else}
	<Scene />
	{#if !checked}
		<p class="boot label">{i18n.t.common.loading}</p>
	{:else if !session}
		<Login onsession={start} />
	{:else}
		<div class="console">
			<Strip />
			<Rail />
			<main class="stage">{@render children()}</main>
			<Deck />
		</div>
		<Palette />
		<Cheatsheet />
		{#if !live.connected}<p class="offline c-tally onair" role="status">
				{i18n.t.app.reconnecting}
			</p>{/if}
		{#if dragging}<div class="drop"><span>{i18n.t.app.dropHere}</span></div>{/if}
	{/if}
	<Toasts />
{/if}

<style>
	.boot {
		position: relative;
		z-index: 1;
		padding: 32px;
	}
	.console {
		/* Fixed to the window: only the stage scrolls, never the page. */
		position: fixed;
		inset: 0;
		z-index: 1;
		display: grid;
		grid-template-areas:
			'rail strip'
			'rail stage'
			'rail deck';
		grid-template-columns: var(--rail) minmax(0, 1fr);
		grid-template-rows: var(--strip) minmax(0, 1fr) var(--deck);
	}
	.stage {
		grid-area: stage;
		overflow-y: auto;
		overflow-x: hidden;
		scrollbar-color: var(--line-strong) transparent;
	}
	.offline {
		position: fixed;
		top: calc(var(--strip) + 10px);
		left: 50%;
		transform: translateX(-50%);
		z-index: 30;
		margin: 0;
		padding: 8px 16px;
		background: var(--panel-solid);
		border: 1px solid var(--onair);
		border-radius: var(--radius);
	}
	.drop {
		position: fixed;
		inset: 0;
		z-index: 80;
		display: grid;
		place-items: center;
		background: rgb(3 5 7 / 0.82);
		pointer-events: none;
	}
	.drop span {
		padding: 40px 60px;
		border: 1px dashed var(--info);
		color: var(--info);
		font: 600 20px var(--font-display);
		text-transform: uppercase;
		box-shadow: 0 0 80px -20px var(--info-glow);
	}

	@media (max-width: 860px) {
		.console {
			grid-template-areas:
				'strip'
				'stage'
				'deck';
			grid-template-columns: minmax(0, 1fr);
			grid-template-rows: var(--strip) minmax(0, 1fr) calc(var(--deck) + 60px);
		}
	}
</style>
