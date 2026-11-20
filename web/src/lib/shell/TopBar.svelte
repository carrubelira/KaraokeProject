<script lang="ts">
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { commands } from '#lib/commands/registry.svelte.js';
	import { live } from '#lib/control/live.svelte.js';
	import { i18n } from '#lib/i18n';
	import { SECTIONS } from './global';
	import Kbd from './Kbd.svelte';

	const working = $derived(live.state.jobs.filter((j) => j.state === 'active').length);
</script>

<header class="top">
	<a class="brand" href={resolve('/')}>Karaoke</a>
	<nav aria-label={i18n.t.nav.label}>
		{#each SECTIONS as section (section.id)}
			{#if section.id !== 'home'}
				<a
					href={resolve(section.path)}
					aria-current={page.url.pathname === section.path ? 'page' : undefined}
					title={section.key}
				>
					{section.label()}
					{#if section.id === 'queue' && working}<span class="badge">{working}</span>{/if}
				</a>
			{/if}
		{/each}
	</nav>
	<button class="palette" onclick={() => (commands.paletteOpen = true)}>
		{i18n.t.cmd.palette}
		<Kbd keys="Mod+k" />
	</button>
</header>

<style>
	.top {
		position: sticky;
		top: 0;
		z-index: 20;
		display: flex;
		align-items: center;
		gap: var(--s-4);
		height: 3.2rem;
		padding: 0 var(--s-4);
		background: color-mix(in srgb, var(--fondo-2) 92%, transparent);
		border-bottom: 1px solid var(--raia);
		backdrop-filter: blur(8px);
	}
	.brand {
		font-family: var(--font-display);
		font-weight: 700;
		color: var(--ouro);
		text-decoration: none;
	}
	nav {
		display: flex;
		gap: var(--s-1);
		overflow-x: auto;
	}
	nav a {
		padding: var(--s-1) var(--s-3);
		border-radius: var(--radius-pill);
		color: var(--texto-2);
		text-decoration: none;
		white-space: nowrap;
	}
	nav a[aria-current='page'] {
		background: var(--ceo-fondo);
		color: var(--ceo);
	}
	nav a:focus-visible {
		outline: 2px solid var(--ceo);
	}
	.badge {
		margin-left: var(--s-1);
		padding: 0 0.4em;
		border-radius: 1em;
		background: var(--ouro);
		color: var(--fondo);
		font-size: 0.8em;
		font-weight: 700;
	}
	.palette {
		margin-left: auto;
		display: flex;
		gap: var(--s-2);
		align-items: center;
		padding: var(--s-1) var(--s-3);
		border: 1px solid var(--raia-forte);
		border-radius: var(--radius-pill);
		background: transparent;
		color: var(--texto-2);
		font: inherit;
		cursor: pointer;
	}
</style>
