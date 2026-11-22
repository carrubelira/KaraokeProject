<script lang="ts">
	/*
	 * The control (docs/web.md): a sidebar with the sections, the page, and the player bar at the
	 * foot. Every key goes through the command registry. A link pasted or a file dropped anywhere
	 * is analysed at once.
	 */
	import '../lib/ui/styles/fonts.css';
	import '../lib/ui/styles/app.css';
	import favicon from '#lib/assets/favicon.svg';
	import { goto } from '$app/navigation';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import { commands } from '#lib/commands/registry.svelte.js';
	import { isTyping } from '#lib/commands/keys.js';
	import PlayerBar from '#lib/console/PlayerBar.svelte';
	import Sidebar from '#lib/console/Sidebar.svelte';
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
	<title>{i18n.t.app.name}</title>
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
	<!-- A development test page for the lyrics, outside the control. -->
	{@render children()}
{:else}
	{#if !checked}
		<p class="boot muted">{i18n.t.common.loading}</p>
	{:else if !session}
		<Login onsession={start} />
	{:else}
		<div class="app">
			<Sidebar name={session.name} />
			<main class="content">
				{#if !live.connected}
					<p class="notice warn offline" role="status">{i18n.t.app.reconnecting}</p>
				{/if}
				{@render children()}
			</main>
			<PlayerBar />
		</div>
		<Palette />
		<Cheatsheet />
		{#if dragging}<div class="drop"><span>{i18n.t.app.dropHere}</span></div>{/if}
	{/if}
	<Toasts />
{/if}

<style>
	.boot {
		padding: 32px;
	}
	.app {
		/* Fixed to the window: only the page scrolls. */
		position: fixed;
		inset: 0;
		display: grid;
		grid-template-areas:
			'sidebar content'
			'player player';
		grid-template-columns: var(--sidebar-width) minmax(0, 1fr);
		grid-template-rows: minmax(0, 1fr) var(--player-height);
	}
	.app > :global(.sidebar) {
		grid-area: sidebar;
	}
	.app > :global(.player-bar) {
		grid-area: player;
	}
	.content {
		grid-area: content;
		overflow-y: auto;
		overflow-x: hidden;
	}
	.offline {
		margin: 16px 28px 0;
	}
	.drop {
		position: fixed;
		inset: 0;
		z-index: 80;
		display: grid;
		place-items: center;
		background: rgb(10 12 14 / 0.8);
		pointer-events: none;
	}
	.drop span {
		padding: 32px 48px;
		border: 2px dashed var(--accent);
		border-radius: 10px;
		background: var(--surface);
		font-size: 17px;
		font-weight: 500;
	}

	@media (max-width: 900px) {
		.app {
			grid-template-areas:
				'sidebar'
				'content'
				'player';
			grid-template-columns: minmax(0, 1fr);
			grid-template-rows: auto minmax(0, 1fr) auto;
		}
	}
</style>
