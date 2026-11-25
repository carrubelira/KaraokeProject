<script lang="ts">
	/**
	 * A preview of the chosen screen's lyrics: they fill word by word at the player's position
	 * (from its last status, moved on locally), the line after waits below. Only a preview: the
	 * screen itself draws with its own clock.
	 */
	import type { Lyrics } from '#lib/contracts';
	import { api } from '#lib/control/api.js';
	import type { Content } from '#lib/control/types.js';
	import { i18n } from '#lib/i18n';

	let { song, position }: { song: Content | null; position: number | null } = $props();

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

<div class="monitor" aria-label={i18n.t.playback.lyrics}>
	{#if song}
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
		{:else}
			<p class="title">{song.title}</p>
		{/if}
	{:else}
		<p class="idle">{i18n.t.player.nothing}</p>
	{/if}
</div>

<style>
	.monitor {
		display: flex;
		flex-direction: column;
		justify-content: center;
		gap: 10px;
		aspect-ratio: 16 / 9;
		padding: 6%;
		border-radius: var(--radius);
		background: #0c0d0f;
		border: 1px solid var(--border);
		text-align: center;
		overflow: hidden;
	}
	.line {
		font-size: clamp(16px, 1.9vw, 26px);
		font-weight: 600;
		line-height: 1.3;
		text-wrap: balance;
	}
	.line.next {
		font-size: clamp(13px, 1.3vw, 18px);
		font-weight: 500;
		color: var(--faint);
	}
	.word {
		position: relative;
		display: inline-block;
		margin: 0 0.13em;
	}
	.base {
		color: var(--text);
	}
	.lit {
		position: absolute;
		inset: 0;
		color: var(--accent-strong);
		clip-path: inset(0 calc((1 - var(--fill)) * 100%) 0 0);
	}
	.title {
		font-size: 20px;
		font-weight: 600;
	}
	.idle {
		color: var(--faint);
	}
</style>
