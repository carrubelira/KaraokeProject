<script lang="ts">
	/**
	 * The deck along the bottom, always there whatever section is open: what is on air on the
	 * chosen screen, where it is (click the line to jump), the transport, and the key and volume
	 * on two encoders. Every control is also a shortcut (Space, N, P, ←/→, [ ], + −).
	 */
	import { onMount } from 'svelte';
	import { live } from '#lib/control/live.svelte.js';
	import { positionNow } from '#lib/control/state.js';
	import { i18n } from '#lib/i18n';
	import { player, transport } from '#lib/shell/actions.svelte.js';
	import { clock } from '#lib/shell/format.js';
	import Encoder from './Encoder.svelte';
	import Icon from './Icon.svelte';
	import { now } from './now.svelte';
	import { onAir } from './on-air';

	const t = $derived(i18n.t);
	const target = $derived(player());
	const air = $derived(onAir(live.state, target));
	const duration = $derived(air.song?.duration ?? null);
	const position = $derived.by(() => {
		void now.value;
		return target ? positionNow(live.state, target, now.value) : null;
	});
	const fraction = $derived(duration && position !== null ? Math.min(1, position / duration) : 0);
	const playing = $derived(target?.status.state === 'playing');
	const semitones = $derived(target?.status.semitones ?? 0);
	const volume = $derived(target?.status.volume ?? 1);

	function seek(event: MouseEvent) {
		if (!duration) return;
		const box = (event.currentTarget as HTMLElement).getBoundingClientRect();
		void transport.seek(((event.clientX - box.left) / box.width) * duration);
	}

	onMount(() => now.use());
</script>

<footer class="deck" class:onair={air.tally === 'onair'} aria-label={t.groups.transport}>
	<div class="buttons">
		<button class="c-btn icon ghost" onclick={transport.previous} aria-label={t.cmd.previous}>
			<Icon name="previous" />
		</button>
		<button
			class="c-btn icon take"
			class:playing
			onclick={transport.toggle}
			aria-label={playing ? t.cmd.pause : t.cmd.play}
			disabled={!target?.online}
		>
			<Icon name={playing ? 'pause' : 'play'} size={22} />
		</button>
		<button class="c-btn icon ghost" onclick={transport.next} aria-label={t.cmd.next}>
			<Icon name="next" />
		</button>
	</div>

	<div class="program">
		<div class="titles">
			{#if air.song}
				<span class="c-tally {air.tally}"
					>{air.tally === 'onair' ? t.strip.onAir : t.deck.cued}</span
				>
				<strong class="title">{air.song.title}</strong>
				<span class="dim artist">{air.song.artist ?? ''}</span>
				{#if air.item?.singer}<span class="c-tag info"><span>♪</span>{air.item.singer}</span>{/if}
			{:else}
				<span class="c-tally off">{target?.online === false ? t.deck.offline : t.deck.nothing}</span
				>
			{/if}
		</div>
		<div class="timeline">
			<span class="mono time">{clock(position)}</span>
			<button
				class="line"
				onclick={seek}
				aria-label={`${clock(position)} / ${clock(duration)}`}
				disabled={!duration}
				style:--value={fraction}
			>
				<span class="fill"></span>
				<span class="head"></span>
			</button>
			<span class="mono time dim"
				>{duration !== null && position !== null
					? t.deck.remaining(clock(duration - position))
					: clock(duration)}</span
			>
		</div>
	</div>

	<div class="next">
		<span class="label">{t.deck.upNext}</span>
		{#if air.next}
			<span class="next-title">{air.next.song?.title ?? air.next.item.content_id}</span>
			{#if air.next.item.singer}<span class="dim small">♪ {air.next.item.singer}</span>{/if}
		{:else}
			<span class="faint small">{t.deck.emptyQueue}</span>
		{/if}
	</div>

	<div class="encoders">
		<Encoder
			label={t.deck.key}
			value={semitones}
			min={-12}
			max={12}
			step={1}
			reset={0}
			text={semitones === 0 ? t.deck.original : t.deck.semitones(semitones)}
			onchange={(v) => void transport.pitch(v)}
		/>
		<Encoder
			label={t.deck.volume}
			value={volume}
			min={0}
			max={2}
			step={0.05}
			reset={1}
			text={`${Math.round(volume * 100)} %`}
			onchange={(v) => void transport.volume(v)}
		/>
	</div>
</footer>

<style>
	.deck {
		grid-area: deck;
		position: relative;
		z-index: 5;
		display: grid;
		grid-template-columns: auto minmax(0, 1fr) minmax(0, 220px) auto;
		align-items: center;
		gap: 22px;
		padding: 0 18px;
		background: linear-gradient(to top, rgb(3 5 7 / 0.96), rgb(6 8 11 / 0.86));
		border-top: 1px solid var(--line);
	}
	.deck.onair {
		border-top-color: rgb(255 58 70 / 0.55);
		box-shadow: 0 -12px 40px -24px var(--onair-glow);
	}
	.buttons {
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.take {
		width: 52px;
		height: 52px;
		border-radius: 50%;
		border-color: var(--line-strong);
	}
	.take.playing {
		background: var(--onair);
		border-color: var(--onair);
		color: #fff;
		box-shadow: 0 0 20px var(--onair-glow);
	}
	.program {
		display: flex;
		flex-direction: column;
		gap: 8px;
		min-width: 0;
	}
	.titles {
		display: flex;
		align-items: center;
		gap: 12px;
		min-width: 0;
		white-space: nowrap;
	}
	.title {
		font: 600 16px/1.2 var(--font-text);
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.artist {
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.timeline {
		display: flex;
		align-items: center;
		gap: 12px;
	}
	.time {
		font-size: 12px;
		min-width: 52px;
	}
	.time:last-child {
		text-align: right;
	}
	.line {
		--value: 0;
		position: relative;
		flex: 1;
		height: 18px;
		padding: 0;
		border: 0;
		background: transparent;
		cursor: pointer;
	}
	.line::before {
		content: '';
		position: absolute;
		left: 0;
		right: 0;
		top: 8px;
		height: 2px;
		background: var(--line-strong);
	}
	.fill {
		position: absolute;
		left: 0;
		top: 8px;
		height: 2px;
		width: calc(var(--value) * 100%);
		background: var(--lyric);
		box-shadow: 0 0 8px rgb(255 201 77 / 0.7);
	}
	.head {
		position: absolute;
		top: 3px;
		left: calc(var(--value) * 100%);
		width: 2px;
		height: 12px;
		margin-left: -1px;
		background: var(--text);
	}
	.line:disabled {
		cursor: default;
	}
	.next {
		display: flex;
		flex-direction: column;
		gap: 4px;
		min-width: 0;
		padding-left: 18px;
		border-left: 1px solid var(--line);
	}
	.next-title {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		font-size: 14px;
	}
	.small {
		font-size: 12px;
	}
	.encoders {
		display: flex;
		gap: 18px;
		padding-left: 18px;
		border-left: 1px solid var(--line);
	}

	@media (max-width: 1180px) {
		.next {
			display: none;
		}
		.deck {
			grid-template-columns: auto minmax(0, 1fr) auto;
		}
	}

	@media (max-width: 860px) {
		.deck {
			grid-template-columns: auto minmax(0, 1fr);
			grid-template-rows: auto auto;
			gap: 8px 14px;
			padding: 8px 12px 68px;
		}
		.encoders {
			grid-column: 1 / -1;
			justify-content: space-around;
			padding: 0;
			border: 0;
		}
	}
</style>
