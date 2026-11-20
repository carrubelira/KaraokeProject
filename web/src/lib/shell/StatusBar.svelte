<script lang="ts">
	/** Always there: what is playing, how long is left, the player and its outputs, the GPUs. */
	import { commands } from '#lib/commands/registry.svelte.js';
	import { live } from '#lib/control/live.svelte.js';
	import { positionNow } from '#lib/control/state.js';
	import { i18n } from '#lib/i18n';
	import { content, player, playlist } from './actions.svelte';
	import { clock, megabytes } from './format';

	let now = $state(performance.now());
	$effect(() => {
		const timer = setInterval(() => (now = performance.now()), 250);
		return () => clearInterval(timer);
	});

	const t = $derived(i18n.t);
	const target = $derived(player());
	const item = $derived(playlist()?.items.find((i) => i.id === target?.status.item_id));
	const song = $derived(item ? content(item.content_id) : undefined);
	const position = $derived(target ? positionNow(live.state, target, now) : null);
	const end = $derived(item?.end ?? song?.duration ?? null);
	const states = $derived<Record<string, string>>({
		playing: t.status.playing,
		paused: t.status.paused,
		loading: t.status.loading,
		waiting: t.status.waiting,
		idle: t.status.idle
	});
	const workers = $derived(live.state.nodes.filter((n) => n.kind === 'worker' && n.online));
	const outputs = $derived(target?.status.outputs.audio.length ?? 0);
	const lost = $derived(Boolean(target?.status.sync?.master_lost));
</script>

<footer class="status" aria-label="Estado">
	<span class="state" class:ctl-on={target?.status.state === 'playing'}>
		{target ? (states[target.status.state] ?? target.status.state) : t.status.noPlayer}
		{#if target && !target.online}<em>· {t.status.offline}</em>{/if}
	</span>
	{#if song}
		<span class="song"
			>{song.title}{#if song.artist}<span class="artist"> · {song.artist}</span>{/if}</span
		>
		<span class="time">{clock(position)} / {clock(end)}</span>
		{#if end !== null && position !== null}<span>{t.status.remaining(clock(end - position))}</span
			>{/if}
		<span>{t.status.key(target?.status.semitones ?? 0)}</span>
	{:else}
		<span class="song ctl-muted">{t.status.nothing}</span>
	{/if}
	<span class="spacer"></span>
	{#if lost}<span class="ctl-warn">⚠ {t.outputs.master}</span>{/if}
	{#if target}<span title={t.outputs.audio}>🔊 {outputs}</span>{/if}
	{#each workers as worker (worker.id)}
		{#if worker.telemetry.gpu_util !== null}
			<span title={worker.name}
				>{t.status.gpu(
					Math.round(worker.telemetry.gpu_util ?? 0),
					megabytes(worker.telemetry.vram_used_mb)
				)}</span
			>
		{/if}
	{/each}
	{#if commands.pending}<span class="pending">{t.cheatsheet.pending(commands.pending)}</span>{/if}
	{#if commands.lastRun}<span class="ctl-muted"
			>{t.status.lastCommand(commands.lastRun.ms.toFixed(0))}</span
		>{/if}
	<span class="dot" class:ctl-ok={live.connected} title={live.connected ? '' : t.app.reconnecting}
	></span>
</footer>

<style>
	.status {
		position: fixed;
		inset: auto 0 0 0;
		z-index: 20;
		display: flex;
		gap: var(--s-4);
		align-items: center;
		height: 2.4rem;
		padding: 0 var(--s-4);
		background: var(--fondo-2);
		border-top: 1px solid var(--raia);
		font-size: var(--t--1);
		color: var(--texto-2);
		white-space: nowrap;
		overflow: hidden;
	}
	.state.ctl-on {
		color: var(--ouro);
		font-weight: 700;
	}
	.song {
		color: var(--texto);
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.artist,
	.ctl-muted {
		color: var(--texto-3);
	}
	.time {
		font-family: var(--font-data);
	}
	.spacer {
		flex: 1;
	}
	.ctl-warn {
		color: var(--erro);
	}
	.pending {
		font-family: var(--font-data);
		color: var(--ceo);
	}
	.dot {
		width: 0.6rem;
		height: 0.6rem;
		border-radius: 50%;
		background: var(--erro);
	}
	.dot.ctl-ok {
		background: #5fe39b;
	}
</style>
