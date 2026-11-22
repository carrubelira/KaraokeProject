<script lang="ts">
	/**
	 * The sidebar: the sections, in words, with their shortcut on hover; at the foot, whether the
	 * server answers and who is signed in. Galicia's coastline sits faintly behind it.
	 */
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import { api } from '#lib/control/api.js';
	import { live } from '#lib/control/live.svelte.js';
	import { i18n } from '#lib/i18n';
	import { SECTIONS } from '#lib/shell/global.js';
	import Coast from '#lib/ui/Coast.svelte';
	import Icon from './Icon.svelte';

	let { name }: { name: string } = $props();
	const t = $derived(i18n.t);

	const counts = $derived({
		jobs: live.state.jobs.filter((j) => j.state === 'active' || j.state === 'review').length,
		review: live.state.jobs.filter((j) => j.state === 'review').length,
		failed: live.state.jobs.filter((j) => j.state === 'failed').length
	});

	function current(path: string): boolean {
		const here = page.url.pathname.replace(/\/$/, '') || '/';
		return path === '/' ? here === '/' : here.startsWith(path);
	}

	async function signOut() {
		await api.signOut().catch(() => {});
		location.reload();
	}
</script>

<aside class="sidebar">
	<Coast class="sidebar-coast" />
	<div class="brand">
		<span class="mark" aria-hidden="true"></span>
		<span>
			<strong>{t.app.name}</strong>
			<span class="faint small">{t.app.signInLead}</span>
		</span>
	</div>

	<nav aria-label={t.nav.label}>
		{#each SECTIONS as section (section.id)}
			<a
				href={resolve(section.path)}
				aria-current={current(section.path) ? 'page' : undefined}
				title={`${section.label()} · ${section.key}`}
			>
				<Icon name={section.icon} size={18} />
				<span>{section.label()}</span>
				{#if section.id === 'jobs' && counts.failed}
					<span class="count error">{counts.failed}</span>
				{:else if section.id === 'jobs' && counts.review}
					<span class="count warn">{counts.review}</span>
				{:else if section.id === 'jobs' && counts.jobs}
					<span class="count">{counts.jobs}</span>
				{/if}
			</a>
		{/each}
	</nav>

	<footer>
		<p class="status" class:off={!live.connected}>
			<span class="dot" aria-hidden="true"></span>
			{live.connected ? t.server.connected : t.server.reconnecting}
		</p>
		<div class="who">
			<span class="truncate">{name}</span>
			<button
				class="btn subtle icon"
				title={t.app.signOut}
				aria-label={t.app.signOut}
				onclick={signOut}
			>
				<Icon name="logout" size={16} />
			</button>
		</div>
	</footer>
</aside>

<style>
	.sidebar {
		position: relative;
		display: flex;
		flex-direction: column;
		gap: 8px;
		height: 100%;
		padding: 16px 12px 12px;
		background: var(--sidebar);
		border-right: 1px solid var(--border);
		overflow: hidden;
	}
	.sidebar :global(.sidebar-coast) {
		position: absolute;
		left: 16px;
		bottom: 90px;
		width: calc(100% - 32px);
		color: var(--accent);
		opacity: 0.22;
	}
	.brand {
		position: relative;
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 2px 8px 14px;
	}
	.brand > span:last-child {
		display: flex;
		flex-direction: column;
		line-height: 1.25;
	}
	.brand strong {
		font-size: 15px;
		font-weight: 600;
	}
	.mark {
		width: 26px;
		height: 26px;
		border-radius: 5px;
		background:
			linear-gradient(135deg, transparent 0 42%, var(--accent) 42% 58%, transparent 58%),
			var(--surface-2);
		border: 1px solid var(--border-strong);
	}
	nav {
		position: relative;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	nav a {
		display: flex;
		align-items: center;
		gap: 10px;
		height: 36px;
		padding: 0 10px;
		border-radius: var(--radius);
		color: var(--muted);
		font-weight: 500;
	}
	nav a:hover {
		background: var(--hover);
		color: var(--text);
		text-decoration: none;
	}
	nav a[aria-current='page'] {
		background: var(--accent-soft);
		color: var(--text);
	}
	nav a[aria-current='page'] :global(svg) {
		color: var(--accent-strong);
	}
	.count {
		margin-left: auto;
		min-width: 20px;
		padding: 0 6px;
		border-radius: 10px;
		background: var(--surface-2);
		color: var(--muted);
		font-size: 12px;
		text-align: center;
	}
	.count.warn {
		background: var(--warn-soft);
		color: var(--warn);
	}
	.count.error {
		background: var(--error-soft);
		color: var(--error);
	}
	footer {
		position: relative;
		margin-top: auto;
		display: flex;
		flex-direction: column;
		gap: 6px;
		padding: 10px 8px 0;
		border-top: 1px solid var(--border);
	}
	.status {
		display: flex;
		align-items: center;
		gap: 8px;
		color: var(--muted);
		font-size: 12.5px;
	}
	.dot {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		background: var(--ok);
	}
	.status.off {
		color: var(--warn);
	}
	.status.off .dot {
		background: var(--warn);
	}
	.who {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		min-width: 0;
	}

	/* On a phone: one row of sections on top, scrolled sideways. */
	@media (max-width: 900px) {
		.sidebar {
			flex-direction: row;
			height: auto;
			padding: 6px 8px;
			border-right: 0;
			border-bottom: 1px solid var(--border);
		}
		.sidebar :global(.sidebar-coast),
		.brand,
		footer {
			display: none;
		}
		nav {
			flex-direction: row;
			overflow-x: auto;
		}
		nav a {
			flex: none;
			height: 34px;
		}
	}
</style>
