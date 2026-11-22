<script lang="ts">
	/**
	 * The strip across the top: which screen the console drives (and its tally), the server's
	 * clock, and the health of the system in one line. Everything is a way in: the counts open
	 * the section that explains them.
	 */
	import { onMount } from 'svelte';
	import { resolve } from '$app/paths';
	import { commands } from '#lib/commands/registry.svelte.js';
	import { live } from '#lib/control/live.svelte.js';
	import { i18n } from '#lib/i18n';
	import { choosePlayer, player } from '#lib/shell/actions.svelte.js';
	import Kbd from '#lib/shell/Kbd.svelte';
	import { now } from './now.svelte';
	import { tallyOf } from './on-air';

	const t = $derived(i18n.t);
	const state = $derived(live.state);
	const target = $derived(player());
	const workers = $derived(state.nodes.filter((n) => n.kind === 'worker'));
	const running = $derived(state.jobs.filter((j) => j.state === 'active').length);
	const review = $derived(state.jobs.filter((j) => j.state === 'review').length);
	const alerts = $derived(
		state.players.reduce((n, p) => n + (p.status.errors ?? []).length, 0) +
			state.jobs.filter((j) => j.state === 'failed').length
	);
	const time = $derived.by(() => {
		void now.value;
		return new Date(live.serverNow() * 1000).toLocaleTimeString(i18n.locale, {
			hour12: false
		});
	});

	const tallyText: Record<string, () => string> = {
		onair: () => t.strip.onAir,
		cue: () => t.strip.standby,
		info: () => t.strip.loading,
		warn: () => t.strip.standby,
		off: () => t.strip.noSignal
	};

	onMount(() => now.use());
</script>

<header class="strip">
	<div class="screens" role="radiogroup" aria-label={t.strip.screen}>
		{#each state.players as p (p.id)}
			{@const tally = tallyOf(p)}
			<button
				role="radio"
				aria-checked={p.id === target?.id}
				class="screen"
				class:chosen={p.id === target?.id}
				onclick={() => choosePlayer(p.id)}
			>
				<span class="c-tally {tally}">{p.name}</span>
			</button>
		{:else}
			<span class="label">{t.strip.noScreen}</span>
		{/each}
	</div>

	{#if target}
		{@const tally = tallyOf(target)}
		<div class="air {tally}" aria-live="polite">
			<span>{target.online ? tallyText[tally === 'off' ? 'cue' : tally]() : t.strip.noSignal}</span>
		</div>
	{/if}

	<div class="spacer"></div>

	<ul class="health">
		<li>
			<a href={resolve('/nodos')} class="c-tally {workers.some((w) => w.online) ? 'cue' : 'warn'}">
				{t.strip.workers(workers.filter((w) => w.online).length, workers.length)}
			</a>
		</li>
		{#if running}
			<li><a href={resolve('/traballos')} class="c-tally info">{t.strip.running(running)}</a></li>
		{/if}
		{#if review}
			<li><a href={resolve('/engadir')} class="c-tally warn">{t.strip.review(review)}</a></li>
		{/if}
		{#if alerts}
			<li><a href={resolve('/traballos')} class="c-tally onair">{t.strip.alerts(alerts)}</a></li>
		{/if}
		<li>
			<span class="c-tally {live.connected ? 'cue' : 'onair'}" title={t.strip.server}>
				{live.connected
					? live.latency !== null
						? t.strip.latency(Math.round(live.latency))
						: t.strip.online
					: t.strip.reconnecting}
			</span>
		</li>
	</ul>

	<time class="clock mono">{time}</time>
	<button class="c-btn ghost palette" onclick={() => (commands.paletteOpen = true)}>
		{t.cmd.palette}
		<Kbd keys="Mod+k" />
	</button>
</header>

<style>
	.strip {
		grid-area: strip;
		position: relative;
		z-index: 5;
		display: flex;
		align-items: center;
		gap: 16px;
		padding: 0 14px;
		background: rgb(4 6 9 / 0.72);
		border-bottom: 1px solid var(--line);
		min-width: 0;
	}
	.screens {
		display: flex;
		gap: 4px;
		min-width: 0;
		overflow-x: auto;
	}
	.screen {
		height: 32px;
		padding: 0 12px;
		border: 1px solid transparent;
		border-radius: var(--radius);
		background: transparent;
		cursor: pointer;
	}
	.screen:hover {
		background: rgb(150 175 205 / 0.06);
	}
	.screen.chosen {
		border-color: var(--line-strong);
		background: var(--panel-2);
	}
	.screen.chosen .c-tally {
		color: var(--text);
	}
	.air {
		display: grid;
		place-items: center;
		height: 28px;
		padding: 0 14px;
		border: 1px solid var(--line-strong);
		border-radius: 2px;
		font: 700 11px/1 var(--font-mono);
		text-transform: uppercase;
		letter-spacing: 0.22em;
		color: var(--faint);
	}
	.air.onair {
		background: var(--onair);
		border-color: var(--onair);
		color: #fff;
		box-shadow: 0 0 24px var(--onair-glow);
		animation: breathe 2.4s ease-in-out infinite;
	}
	.air.cue {
		color: var(--cue);
		border-color: rgb(36 227 143 / 0.5);
	}
	.air.warn {
		color: var(--warn);
		border-color: rgb(255 176 32 / 0.5);
	}
	.air.info {
		color: var(--info);
		border-color: rgb(60 200 255 / 0.5);
	}
	@keyframes breathe {
		50% {
			box-shadow: 0 0 8px var(--onair-glow);
		}
	}
	.spacer {
		flex: 1;
	}
	.health {
		display: flex;
		gap: 18px;
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.health a {
		text-decoration: none;
	}
	.clock {
		font-size: 15px;
		color: var(--text);
		letter-spacing: 0.04em;
	}
	@media (max-width: 1180px) {
		.health li:not(:last-child) {
			display: none;
		}
	}
	@media (max-width: 860px) {
		.palette,
		.clock,
		.health {
			display: none;
		}
	}
</style>
