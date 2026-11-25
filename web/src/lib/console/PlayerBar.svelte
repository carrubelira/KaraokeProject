<script lang="ts">
	/**
	 * The player bar, at the foot of every page: the stage's state (is the audio up, how many
	 * screens are ready for the song cued), what is on and where, and the controls (previous,
	 * start or pause, next, stop), the key and the volume. The keyboard does the same from
	 * anywhere (Space, N, P, [ ], + −). Nothing plays until the operator starts it.
	 */
	import { onMount } from 'svelte';
	import { live } from '#lib/control/live.svelte.js';
	import { notReady, positionNow } from '#lib/control/state.js';
	import { i18n } from '#lib/i18n';
	import { transport } from '#lib/shell/actions.svelte.js';
	import { clock } from '#lib/shell/format.js';
	import Icon from './Icon.svelte';
	import { now } from './now.svelte';
	import { onStage, sessionTone } from './stage';

	const t = $derived(i18n.t);
	const session = $derived(live.state.session);
	const on = $derived(onStage(live.state));
	const playing = $derived(session.state === 'playing');
	const position = $derived.by(() => {
		void now.value;
		return positionNow(session, live.serverMicros());
	});
	const counted = $derived(live.state.screens.filter((s) => s.counts));
	const missing = $derived(notReady(live.state));
	const start = $derived(on.item?.start ?? 0);
	const length = $derived(on.song?.duration ?? null);
	const fraction = $derived(
		length && position !== null ? Math.min(1, Math.max(0, (position - start) / length)) : 0
	);
	const semitones = $derived(session.semitones);
	const volume = $derived(session.volume);
	const audioDown = $derived(live.state.audio.required && !live.state.audio.online);
	const disabled = $derived(!live.connected);

	function seek(event: MouseEvent & { currentTarget: HTMLElement }) {
		if (!length || disabled) return;
		const box = event.currentTarget.getBoundingClientRect();
		void transport.seek(start + ((event.clientX - box.left) / box.width) * length);
	}

	onMount(() => now.use());
</script>

<footer class="player-bar" aria-label={t.groups.playback}>
	<div class="screen" role="status">
		<span class="badge {sessionTone(live.state)}">
			{audioDown ? t.player.audioDown : t.player.states[session.state]}
		</span>
		{#if counted.length}
			<span class="small" class:muted={!missing.length} class:warn-text={missing.length > 0}>
				{t.player.screensReady(counted.length - missing.length, counted.length)}
			</span>
		{/if}
	</div>

	<div class="now">
		<div class="song">
			{#if on.song}
				<strong class="truncate">{on.song.title}</strong>
				<span class="muted truncate">
					{on.song.artist ?? ''}{on.item?.singer ? ` · ${on.item.singer}` : ''}
				</span>
			{:else}
				<span class="muted">{t.player.nothing}</span>
			{/if}
			{#if on.next?.song}
				<span class="faint truncate next">{t.player.next}: {on.next.song.title}</span>
			{/if}
		</div>
		<div class="timeline">
			<span class="mono small muted">{clock(position === null ? null : position - start)}</span>
			<button
				class="track"
				aria-label={t.cmd.forward}
				disabled={!length || disabled}
				onclick={seek}
			>
				<span style:width="{fraction * 100}%"></span>
			</button>
			<span class="mono small muted">{clock(length)}</span>
		</div>
	</div>

	<div class="transport">
		<button
			class="btn subtle icon"
			{disabled}
			onclick={transport.previous}
			title={t.cmd.previous}
			aria-label={t.cmd.previous}
		>
			<Icon name="previous" />
		</button>
		<button
			class="btn primary icon play"
			{disabled}
			onclick={transport.toggle}
			title={t.cmd.toggle}
			aria-label={playing ? t.cmd.pause : t.cmd.start}
		>
			<Icon name={playing ? 'pause' : 'play'} />
		</button>
		<button
			class="btn subtle icon"
			{disabled}
			onclick={transport.next}
			title={t.cmd.next}
			aria-label={t.cmd.next}
		>
			<Icon name="next" />
		</button>
		<button
			class="btn subtle icon"
			{disabled}
			onclick={transport.stop}
			title={t.cmd.stop}
			aria-label={t.cmd.stop}
		>
			<Icon name="stop" size={16} />
		</button>
	</div>

	<div class="levels">
		<div class="key" role="group" aria-label={t.player.key}>
			<span class="muted small">{t.player.key}</span>
			<button
				class="btn subtle icon step"
				{disabled}
				onclick={() => transport.pitchBy(-1)}
				aria-label={t.cmd.pitchDown}
				title={t.cmd.pitchDown}>−</button
			>
			<button class="mono value" {disabled} onclick={transport.pitchReset} title={t.cmd.pitchReset}>
				{t.player.semitones(semitones)}
			</button>
			<button
				class="btn subtle icon step"
				{disabled}
				onclick={() => transport.pitchBy(1)}
				aria-label={t.cmd.pitchUp}
				title={t.cmd.pitchUp}>+</button
			>
		</div>
		<label class="volume" title={t.player.volume}>
			<Icon name="volume" size={16} />
			<span class="sr-only">{t.player.volume}</span>
			<input
				type="range"
				min="0"
				max="1.5"
				step="0.05"
				value={volume}
				{disabled}
				onchange={(e) => transport.volume(Number(e.currentTarget.value))}
			/>
			<span class="mono small muted pct">{Math.round(volume * 100)}</span>
		</label>
	</div>
</footer>

<style>
	.player-bar {
		display: grid;
		grid-template-columns: minmax(200px, 260px) minmax(0, 1fr) auto auto;
		align-items: center;
		gap: 24px;
		height: 100%;
		padding: 0 16px;
		background: var(--sidebar);
		border-top: 1px solid var(--border);
	}
	.screen {
		display: flex;
		align-items: center;
		gap: 8px;
		min-width: 0;
	}
	.screen {
		flex-wrap: wrap;
	}
	.warn-text {
		color: var(--warn);
	}
	.now {
		display: flex;
		flex-direction: column;
		gap: 2px;
		min-width: 0;
	}
	.song {
		display: flex;
		align-items: baseline;
		gap: 10px;
		min-width: 0;
	}
	.song .next {
		margin-left: auto;
		font-size: 12.5px;
	}
	.timeline {
		display: grid;
		grid-template-columns: 44px 1fr 44px;
		align-items: center;
		gap: 8px;
	}
	.timeline > span:last-child {
		text-align: right;
	}
	.track {
		position: relative;
		height: 14px;
		padding: 0;
		border: 0;
		background: none;
		cursor: pointer;
	}
	.track::before {
		content: '';
		position: absolute;
		inset: 5px 0;
		border-radius: 2px;
		background: var(--surface-2);
	}
	.track span {
		position: absolute;
		left: 0;
		top: 5px;
		height: 4px;
		border-radius: 2px;
		background: var(--accent);
	}
	.track:disabled {
		cursor: default;
	}
	.transport {
		display: flex;
		align-items: center;
		gap: 4px;
	}
	.play {
		width: 38px;
		height: 38px;
		border-radius: 50%;
	}
	.levels {
		display: flex;
		align-items: center;
		gap: 20px;
	}
	.key {
		display: flex;
		align-items: center;
		gap: 2px;
	}
	.key > span {
		margin-right: 6px;
	}
	.step {
		width: 26px;
		height: 26px;
		font-size: 16px;
	}
	.value {
		min-width: 32px;
		height: 26px;
		border: 1px solid var(--border);
		border-radius: 4px;
		background: var(--bg);
		cursor: pointer;
	}
	.volume {
		display: flex;
		align-items: center;
		gap: 8px;
		color: var(--muted);
	}
	.volume input {
		width: 110px;
		accent-color: var(--accent);
	}
	.pct {
		width: 28px;
		text-align: right;
	}

	@media (max-width: 1200px) {
		.song .next,
		.key > span {
			display: none;
		}
	}
	@media (max-width: 900px) {
		.player-bar {
			grid-template-columns: minmax(0, 1fr) auto;
			gap: 6px 12px;
			padding: 8px 12px;
		}
		.now {
			grid-column: 1 / -1;
			order: -1;
		}
		.levels {
			display: none;
		}
	}
</style>
