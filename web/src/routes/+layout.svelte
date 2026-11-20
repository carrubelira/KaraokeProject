<script lang="ts">
	/*
	 * The control UI (plan v4 §7): sign-in, the top bar, the status bar, the command palette, the
	 * cheat sheet and notices around every section; every key goes through the command registry.
	 * Files dropped anywhere and links pasted anywhere become karaokes.
	 */
	import '../lib/ui/styles/tokens.css';
	import '../lib/ui/styles/fonts.css';
	import '../lib/ui/styles/base.css';
	import '../lib/ui/styles/control.css';
	import favicon from '#lib/assets/favicon.svg';
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import { commands } from '#lib/commands/registry.svelte.js';
	import { isTyping } from '#lib/commands/keys.js';
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
	import StatusBar from '#lib/shell/StatusBar.svelte';
	import Toasts from '#lib/shell/Toasts.svelte';
	import TopBar from '#lib/shell/TopBar.svelte';
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
			void intake.link(text.trim());
		}
	}

	function drop(event: DragEvent) {
		event.preventDefault();
		dragging = false;
		if (session && event.dataTransfer?.files.length) void intake.files(event.dataTransfer.files);
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
		if (e.dataTransfer?.types.includes('Files')) {
			e.preventDefault();
			dragging = true;
		}
	}}
	ondragleave={(e) => e.relatedTarget === null && (dragging = false)}
	ondrop={drop}
/>

{#if page.route.id === '/proba-letra'}
	<!-- A development test page for the lyrics, outside the control UI. -->
	{@render children()}
{:else if !checked}
	<p class="boot">{i18n.t.common.loading}</p>
{:else if !session}
	<Login onsession={start} />
{:else}
	<TopBar />
	<main class="app">{@render children()}</main>
	<StatusBar />
	<Palette />
	<Cheatsheet />
	{#if !live.connected}<p class="offline" role="status">{i18n.t.app.reconnecting}</p>{/if}
	{#if dragging}<div class="drop">{i18n.t.app.dropHere}</div>{/if}
{/if}
<Toasts />

<style>
	.boot {
		padding: var(--s-6);
		color: var(--texto-3);
	}
	.app {
		padding-bottom: 2.6rem;
	}
	.offline {
		position: fixed;
		top: 3.4rem;
		left: 50%;
		transform: translateX(-50%);
		z-index: 30;
		margin: 0;
		padding: var(--s-1) var(--s-4);
		border-radius: var(--radius-pill);
		background: var(--erro);
		color: var(--fondo);
		font-weight: 700;
	}
	.drop {
		position: fixed;
		inset: 0;
		z-index: 60;
		display: grid;
		place-items: center;
		background: rgb(4 7 12 / 0.8);
		border: 3px dashed var(--ceo);
		color: var(--ceo);
		font-size: var(--t-3);
		pointer-events: none;
	}
</style>
