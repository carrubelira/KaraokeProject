<script lang="ts">
	/** The fixed sidebar: every section in three groups, its key, and who is connected to what. */
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { live } from '#lib/control/live.svelte.js';
	import { i18n } from '#lib/i18n';
	import Coast from './Coast.svelte';
	import { SECTIONS } from './global';
	import Icon from './Icon.svelte';
	import Kbd from './Kbd.svelte';

	let { operator }: { operator: string } = $props();

	const t = $derived(i18n.t);
	const GROUPS = ['session', 'content', 'system'] as const;
	const home = SECTIONS[0];
	const active = (path: string) =>
		path === '/' ? page.url.pathname === '/' : page.url.pathname.startsWith(path);
</script>

{#snippet link(section: (typeof SECTIONS)[number])}
	<a
		href={resolve(section.path)}
		class:active={active(section.path)}
		aria-current={active(section.path) ? 'page' : undefined}
	>
		<Icon name={section.icon} />
		<span class="label">{section.label()}</span>
		<span class="key"><Kbd keys={section.key} /></span>
	</a>
{/snippet}

<nav class="sidebar" aria-label={t.nav.label}>
	<div class="product">
		<span class="name">{t.app.product}</span>
		<span class="ctl-muted">{t.app.productSub}</span>
	</div>
	<div class="links">
		{@render link(home)}
		{#each GROUPS as group (group)}
			<p class="group">{t.nav.groups[group]}</p>
			{#each SECTIONS.filter((s) => s.group === group) as section (section.id)}
				{@render link(section)}
			{/each}
		{/each}
	</div>
	<div class="coast"><Coast /></div>
	<div class="foot">
		<p class="ctl-badge" class:ctl-ok={live.connected} class:ctl-bad={!live.connected}>
			{live.connected ? t.app.connected : t.app.disconnected}
		</p>
		<p class="ctl-muted operator">{operator}</p>
	</div>
</nav>

<style>
	.sidebar {
		position: fixed;
		z-index: 10;
		top: 0;
		left: 0;
		bottom: var(--statusbar);
		width: var(--sidebar);
		display: flex;
		flex-direction: column;
		background: var(--surface);
		border-right: 1px solid var(--border);
	}
	.product {
		display: grid;
		padding: var(--sp-4) var(--sp-4) var(--sp-3);
		border-bottom: 1px solid var(--border);
	}
	.name {
		font-size: var(--fs-l);
		font-weight: 600;
	}
	.product .ctl-muted {
		font-size: var(--fs-s);
	}
	.links {
		display: grid;
		gap: 1px;
		padding: var(--sp-3) var(--sp-2);
		overflow-y: auto;
	}
	.group {
		margin: var(--sp-4) var(--sp-3) var(--sp-1);
		font-size: var(--fs-s);
		font-weight: 500;
		color: var(--text-3);
	}
	a {
		display: flex;
		align-items: center;
		gap: var(--sp-3);
		height: 2.1rem;
		padding: 0 var(--sp-3);
		border-radius: var(--radius);
		color: var(--text-2);
		text-decoration: none;
	}
	a:hover {
		background: var(--surface-hover);
		color: var(--text);
	}
	a.active {
		background: var(--accent-bg);
		color: var(--text);
		font-weight: 500;
	}
	a.active :global(.icon) {
		color: var(--accent-text);
	}
	.label {
		flex: 1;
	}
	.key :global(.kbd) {
		border: 0;
		padding: 0;
		min-width: 0;
		font-size: 0.72rem;
		font-weight: 400;
		color: var(--text-3);
	}
	a.active .key :global(.kbd) {
		color: var(--text-2);
	}
	.coast {
		flex: 1;
		min-height: 6rem;
		padding: var(--sp-4) var(--sp-5);
	}
	.foot {
		display: grid;
		gap: var(--sp-1);
		padding: var(--sp-3) var(--sp-4);
		border-top: 1px solid var(--border);
		font-size: var(--fs-s);
	}
	.operator {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
</style>
