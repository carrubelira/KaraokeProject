<script lang="ts">
	/** Always there: what is playing, how long is left, the key, the player and the GPUs. */
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
	const lost = $derived(Boolean(target?.status.sync?.master_lost));
	const badge = $derived(
		!target?.online ? 'ctl-bad' : target.status.state === 'playing' ? 'ctl-ok' : ''
	);
</script>

<footer class="status" aria-label={t.status.label}>
	<span class="ctl-badge {badge}">
		{target ? (states[target.status.state] ?? target.status.state) : t.status.noPlayer}
		{#if target && !target.online}· {t.status.offline}{/if}
	</span>
	{#if song}
		<span class="song"
			>{song.title}{#if song.artist}<span class="ctl-muted ctl-after">· {song.artist}</span
				>{/if}</span
		>
		<span class="ctl-mono">{clock(position)} / {clock(end)}</span>
		<span class="ctl-muted">{t.status.key(target?.status.semitones ?? 0)}</span>
	{:else}
		<span class="song ctl-muted">{t.status.nothing}</span>
	{/if}
	<span class="spacer"></span>
	{#if commands.pending}<span class="ctl-mono pending"
			>{t.cheatsheet.pending(commands.pending)}</span
		>{/if}
	{#if lost}<span class="ctl-badge ctl-warn">{t.status.masterLost}</span>{/if}
	{#if target}<span class="ctl-muted">{target.name}</span>{/if}
	{#each workers as worker (worker.id)}
		{#if worker.telemetry.gpu_util !== null}
			<span class="ctl-mono ctl-muted" title={worker.name}
				>{t.status.gpu(
					Math.round(worker.telemetry.gpu_util ?? 0),
					megabytes(worker.telemetry.vram_used_mb)
				)}</span
			>
		{/if}
	{/each}
</footer>

<style>
	.status {
		position: fixed;
		inset: auto 0 0 0;
		z-index: 20;
		display: flex;
		gap: var(--sp-4);
		align-items: center;
		height: var(--statusbar);
		padding: 0 var(--sp-4);
		background: var(--surface);
		border-top: 1px solid var(--border);
		font-size: var(--fs-s);
		color: var(--text-2);
		white-space: nowrap;
		overflow: hidden;
	}
	.song {
		color: var(--text);
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.spacer {
		flex: 1;
	}
	.pending {
		color: var(--accent-text);
	}
</style>
