<script lang="ts">
	/** Home: the night globe and what the system is doing, one key away from every section. */
	import { resolve } from '$app/paths';
	import GlobeAnchor from '#lib/globe/GlobeAnchor.svelte';
	import Stage from '#lib/globe/Stage.svelte';
	import { stage } from '#lib/globe/stage.svelte.js';
	import { PEOPLE } from '#lib/globe/galicia.js';
	import { live } from '#lib/control/live.svelte.js';
	import { jobProgress } from '#lib/control/state.js';
	import { i18n } from '#lib/i18n';
	import { SECTIONS } from '#lib/shell/global.js';
	import Kbd from '#lib/shell/Kbd.svelte';

	const t = $derived(i18n.t);
	const active = $derived(live.state.jobs.filter((j) => j.state === 'active'));
	const online = $derived(live.state.nodes.filter((n) => n.online));
	$effect(() => {
		stage.mood = active.length ? 'scan' : 'calm';
		stage.progress = active.length ? jobProgress(active[0]) : null;
	});
</script>

<Stage />
<div class="home">
	<div class="globe">
		<GlobeAnchor
			label={t.globe.label(new Intl.NumberFormat(i18n.locale).format(PEOPLE))}
			names
			turnable
		/>
	</div>
	<nav class="menu ctl-box" aria-label={t.nav.home}>
		{#each SECTIONS.filter((s) => s.id !== 'home') as section (section.id)}
			<a href={resolve(section.path)}><span>{section.label()}</span><Kbd keys={section.key} /></a>
		{/each}
		<p class="ctl-muted">
			{t.library.count(live.state.contents.length)} · {active.length}
			{t.queue.states.active.toLowerCase()} ·
			{online.length}
			{t.workers.online.toLowerCase()}
		</p>
		<p class="ctl-muted credits">{t.globe.credits}</p>
	</nav>
</div>

<style>
	.home {
		display: grid;
		grid-template-columns: minmax(0, 1.6fr) minmax(18rem, 1fr);
		gap: var(--s-5);
		align-items: center;
		min-height: calc(100vh - 6rem);
		padding: var(--s-4) var(--s-6);
	}
	.globe {
		aspect-ratio: 1;
		max-height: calc(100vh - 8rem);
	}
	.menu {
		display: grid;
		gap: var(--s-1);
		background: var(--panel);
		backdrop-filter: blur(6px);
	}
	.menu a {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: var(--s-2) var(--s-3);
		border-radius: var(--radius-control);
		color: var(--texto);
		text-decoration: none;
		font-size: var(--t-1);
	}
	.menu a:hover,
	.menu a:focus-visible {
		background: var(--ceo-fondo);
	}
	.credits {
		font-size: var(--t--1);
	}
	@media (max-width: 60em) {
		.home {
			grid-template-columns: 1fr;
		}
	}
</style>
