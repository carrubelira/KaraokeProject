<script lang="ts">
	/**
	 * The sections, down the left edge like the source buttons of a switcher. Each one carries a
	 * live count when something there wants the operator: songs to review, jobs running, nodes
	 * that went quiet.
	 */
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	import { commands } from '#lib/commands/registry.svelte.js';
	import { label } from '#lib/commands/keys.js';
	import { live } from '#lib/control/live.svelte.js';
	import { i18n } from '#lib/i18n';
	import { SECTIONS } from '#lib/shell/global.js';
	import Icon from './Icon.svelte';

	const state = $derived(live.state);
	const badges = $derived<Record<string, { n: number; tone: 'warn' | 'info' | 'onair' } | null>>({
		add: count(state.jobs.filter((j) => j.state === 'review').length, 'warn'),
		jobs:
			count(state.jobs.filter((j) => j.state === 'failed').length, 'onair') ??
			count(state.jobs.filter((j) => j.state === 'active').length, 'info'),
		nodes: count(
			state.nodes.filter((n) => !n.online).length +
				state.players.filter((p) => (p.status.errors ?? []).length).length,
			'onair'
		)
	});

	function count(n: number, tone: 'warn' | 'info' | 'onair') {
		return n ? { n, tone } : null;
	}

	function active(path: string): boolean {
		const here = page.url.pathname;
		return path === '/' ? here === '/' : here.startsWith(path);
	}

	const keyOf = (id: string) => {
		const command = commands.find(`go.${id}`);
		const keys = command ? commands.keysOf(command) : [];
		return keys[0] ? label(keys[0]) : '';
	};
</script>

<nav class="rail" aria-label={i18n.t.nav.label}>
	<a class="mark" href={resolve('/')} aria-label={i18n.t.app.name}>
		<span class="disc" class:live={live.connected}></span>
	</a>
	<ul>
		{#each SECTIONS as section (section.id)}
			{@const badge = badges[section.id]}
			<li>
				<a
					href={resolve(section.path)}
					class:active={active(section.path)}
					aria-current={active(section.path) ? 'page' : undefined}
					title={`${section.label()} · ${keyOf(section.id)}`}
				>
					<Icon name={section.icon} size={20} />
					<span class="name">{section.label()}</span>
					{#if badge}<span class="badge {badge.tone}">{badge.n}</span>{/if}
				</a>
			</li>
		{/each}
	</ul>
</nav>

<style>
	.rail {
		grid-area: rail;
		position: relative;
		z-index: 5;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 10px;
		padding: 10px 0;
		background: rgb(4 6 9 / 0.78);
		border-right: 1px solid var(--line);
	}
	.mark {
		display: grid;
		place-items: center;
		width: 44px;
		height: 44px;
		margin-bottom: 6px;
	}
	.disc {
		width: 18px;
		height: 18px;
		border-radius: 50%;
		border: 2px solid var(--faint);
		transition: all 0.4s;
	}
	.disc.live {
		border-color: var(--lyric);
		box-shadow:
			0 0 14px rgb(255 201 77 / 0.5),
			inset 0 0 6px rgb(255 201 77 / 0.6);
	}
	ul {
		display: flex;
		flex-direction: column;
		gap: 4px;
		margin: 0;
		padding: 0;
		list-style: none;
		width: 100%;
	}
	a:not(.mark) {
		position: relative;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 5px;
		padding: 10px 4px 8px;
		color: var(--faint);
		text-decoration: none;
		transition: color 0.15s;
	}
	a:not(.mark):hover {
		color: var(--text);
	}
	a.active {
		color: var(--text);
	}
	a.active::before {
		content: '';
		position: absolute;
		left: 0;
		top: 8px;
		bottom: 8px;
		width: 2px;
		background: var(--lyric);
		box-shadow: 0 0 10px rgb(255 201 77 / 0.6);
	}
	.name {
		font: 500 9px/1 var(--font-mono);
		text-transform: uppercase;
		letter-spacing: 0.1em;
	}
	.badge {
		position: absolute;
		top: 4px;
		right: 12px;
		min-width: 17px;
		height: 17px;
		padding: 0 4px;
		border-radius: 9px;
		font: 600 10px/17px var(--font-mono);
		text-align: center;
		color: var(--void);
	}
	.badge.warn {
		background: var(--warn);
	}
	.badge.info {
		background: var(--info);
	}
	.badge.onair {
		background: var(--onair);
		color: #fff;
	}

	@media (max-width: 860px) {
		.name {
			display: none;
		}
		.badge {
			right: 4px;
		}
		.rail {
			z-index: 6;
			position: fixed;
			left: 0;
			right: 0;
			bottom: 0;
			flex-direction: row;
			height: 60px;
			padding: 0 6px;
			border-right: 0;
			border-top: 1px solid var(--line);
		}
		.mark {
			display: none;
		}
		ul {
			flex-direction: row;
			justify-content: space-around;
		}
		a.active::before {
			left: 25%;
			right: 25%;
			top: 0;
			bottom: auto;
			width: auto;
			height: 2px;
		}
	}
</style>
