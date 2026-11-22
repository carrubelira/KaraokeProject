<script lang="ts">
	/**
	 * The program monitor: what the chosen screen shows, as a confidence monitor would. The lyrics
	 * fill word by word at the player's position (from its last status, moved on locally), the
	 * line after waits below. It is a preview: the screen itself draws with its own clock.
	 */
	import type { Lyrics } from '#lib/contracts';
	import { api } from '#lib/control/api.js';
	import type { Content } from '#lib/control/types.js';
	import { i18n } from '#lib/i18n';
	import { clock } from '#lib/shell/format.js';
	import type { Tally } from './on-air';

	let {
		song,
		position,
		tally,
		singer
	}: { song: Content | null; position: number | null; tally: Tally; singer: string | null } =
		$props();

	// Plain (not reactive): a cache of promises nothing renders from.
	// eslint-disable-next-line svelte/prefer-svelte-reactivity
	const cache = new Map<string, Promise<Lyrics | null>>();
	let lyrics = $state<Lyrics | null>(null);

	$effect(() => {
		const key = song ? `${song.id}@${song.manifest}` : null;
		lyrics = null;
		if (!key || !song) return;
		let promise = cache.get(key);
		if (!promise) {
			promise = api.lyrics(song.id).catch(() => null);
			cache.set(key, promise);
		}
		let current = true;
		void promise.then((found) => {
			if (current) lyrics = found;
		});
		return () => {
			current = false;
		};
	});

	const at = $derived(position ?? 0);
	const lines = $derived((lyrics?.lines ?? []).filter((l) => l.role === 'lead'));
	const index = $derived.by(() => {
		const playing = lines.findIndex((l) => at >= l.start - 0.4 && at < l.end + 0.3);
		if (playing >= 0) return playing;
		const upcoming = lines.findIndex((l) => l.start > at);
		return upcoming >= 0 ? upcoming : lines.length - 1;
	});
	const line = $derived(lines[index] ?? null);
	const after = $derived(lines[index + 1] ?? null);

	function fill(start: number, end: number): number {
		if (at <= start) return 0;
		if (at >= end) return 1;
		return (at - start) / Math.max(0.05, end - start);
	}
</script>

<div class="monitor {tally}">
	<div class="frame">
		<div class="corner tl"></div>
		<div class="corner br"></div>
		<div class="safe"></div>
		{#if song}
			<div class="lyrics" aria-hidden={tally !== 'onair'}>
				{#if line}
					<p class="line">
						{#each line.words as word, w (w)}
							<span class="word" style:--fill={fill(word.start, word.end)}>
								<span class="base">{word.text}</span>
								<span class="lit" aria-hidden="true">{word.text}</span>
							</span>
						{/each}
					</p>
					{#if after}
						<p class="line next">{after.words.map((w) => w.text).join(' ')}</p>
					{/if}
				{:else if lyrics === null}
					<p class="title">{song.title}</p>
				{/if}
			</div>
			<div class="slate">
				<span class="mono">{clock(position)}</span>
				<span class="dim">{song.title}{song.artist ? ` · ${song.artist}` : ''}</span>
				{#if singer}<span class="c-tag info">♪ {singer}</span>{/if}
			</div>
		{:else}
			<div class="bars" aria-hidden="true">
				{#each ['#c0c0c0', '#c0c000', '#00c0c0', '#00c000', '#c000c0', '#c00000', '#0000c0'] as colour (colour)}
					<span style:background={colour}></span>
				{/each}
			</div>
			<p class="idle label">{i18n.t.deck.nothing}</p>
		{/if}
	</div>
</div>

<style>
	.monitor {
		position: relative;
		padding: 10px;
		background: #000;
		border: 1px solid var(--line-strong);
		border-radius: var(--radius);
	}
	.monitor.onair {
		border-color: var(--onair);
		box-shadow:
			0 0 0 3px rgb(255 58 70 / 0.18),
			0 0 60px -10px var(--onair-glow);
	}
	.monitor.cue {
		border-color: rgb(36 227 143 / 0.6);
	}
	.monitor.warn {
		border-color: rgb(255 176 32 / 0.6);
	}
	.frame {
		position: relative;
		aspect-ratio: 16 / 9;
		overflow: hidden;
		background:
			radial-gradient(ellipse at 50% 120%, rgb(255 201 77 / 0.09), transparent 60%),
			radial-gradient(ellipse at 50% -20%, rgb(60 200 255 / 0.06), transparent 50%), #020304;
		display: grid;
		place-items: center;
	}
	.safe {
		position: absolute;
		inset: 7% 7%;
		border: 1px dashed rgb(150 175 205 / 0.12);
		pointer-events: none;
	}
	.corner {
		position: absolute;
		width: 18px;
		height: 18px;
		border: 2px solid rgb(150 175 205 / 0.35);
	}
	.tl {
		top: 10px;
		left: 10px;
		border-right: 0;
		border-bottom: 0;
	}
	.br {
		right: 10px;
		bottom: 10px;
		border-left: 0;
		border-top: 0;
	}
	.lyrics {
		width: 86%;
		text-align: center;
	}
	.line {
		margin: 0;
		font: 700 clamp(18px, 2.4vw, 34px) / 1.25 var(--font-text);
		letter-spacing: -0.01em;
		text-wrap: balance;
	}
	.line.next {
		margin-top: 0.6em;
		font-size: clamp(14px, 1.6vw, 22px);
		color: rgb(232 237 243 / 0.35);
	}
	.word {
		position: relative;
		display: inline-block;
		margin: 0 0.14em;
	}
	.base {
		color: rgb(232 237 243 / 0.9);
	}
	.lit {
		position: absolute;
		inset: 0;
		color: var(--lyric);
		clip-path: inset(0 calc((1 - var(--fill)) * 100%) 0 0);
		text-shadow: 0 0 18px rgb(255 201 77 / 0.55);
	}
	.title {
		font: 600 28px var(--font-display);
		text-transform: uppercase;
		margin: 0;
	}
	.slate {
		position: absolute;
		left: 16px;
		right: 16px;
		bottom: 12px;
		display: flex;
		align-items: center;
		gap: 12px;
		font-size: 12px;
		white-space: nowrap;
		overflow: hidden;
	}
	.bars {
		position: absolute;
		inset: 0 0 30% 0;
		display: grid;
		grid-template-columns: repeat(7, 1fr);
		opacity: 0.18;
		filter: saturate(0.7);
	}
	.idle {
		position: relative;
		margin-top: 24%;
	}
</style>
