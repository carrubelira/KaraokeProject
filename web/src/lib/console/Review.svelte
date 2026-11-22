<script lang="ts">
	/**
	 * The operator's word on what a song is, once the analysis has run. The best guess is filled
	 * in; the other guesses are one click away, each with its source and how sure it is. The
	 * lyrics are chosen among those found (timed ones first), searched again, pasted, or left out
	 * to transcribe. Nothing heavy runs until "Process".
	 */
	import { api } from '#lib/control/api.js';
	import { live } from '#lib/control/live.svelte.js';
	import type { Analysis, Guess, Job, LyricsCandidate } from '#lib/control/types.js';
	import { i18n } from '#lib/i18n';
	import { fail, jobs, player } from '#lib/shell/actions.svelte.js';
	import { clock } from '#lib/shell/format.js';
	import { toasts } from '#lib/control/toasts.svelte.js';
	import Icon from './Icon.svelte';

	let { job }: { job: Job } = $props();
	const t = $derived(i18n.t);
	const LANGUAGES = ['gl', 'es', 'pt', 'en', 'ca', 'eu', 'fr', 'it', 'de'];

	const analysis = $derived(
		(job.tasks.find((x) => x.kind === 'analyze')?.data ?? {}) as Partial<Analysis>
	);
	const best = $derived(analysis.best ?? null);
	const candidates = $derived((analysis.candidates ?? []).filter((c) => c.title));

	// The form starts from the best guess (once: later analysis updates do not wipe edits).
	let title = $state('');
	let artist = $state('');
	let language = $state('gl');
	let cover = $state<string | null>(null);
	let filled = false;
	$effect(() => {
		if (filled || !best) return;
		filled = true;
		use(best);
		language = best.language ?? (job.params.language as string | undefined) ?? 'gl';
	});

	let found = $state<LyricsCandidate[]>([]);
	let searched = false;
	$effect(() => {
		const lyrics = analysis.lyrics ?? [];
		if (!searched) found = lyrics;
	});
	/** The lyrics chosen: an index in `found`, 'own' text, or 'none' (transcribe). */
	let choice = $state<number | 'own' | 'none'>(0);
	let own = $state('');
	let query = $state('');
	let searching = $state(false);
	let busy = $state(false);
	let open = $state<number | null>(null);

	$effect(() => {
		if (!found.length && choice !== 'own') choice = 'none';
	});

	function use(guess: Guess) {
		title = guess.title;
		artist = guess.artist ?? '';
		cover = guess.cover;
		if (guess.language) language = guess.language;
	}

	async function search() {
		searching = true;
		searched = true;
		try {
			found = await api.searchLyrics(query || `${artist} ${title}`.trim(), analysis.duration);
			choice = found.length ? 0 : 'none';
		} catch (error) {
			fail(error);
		} finally {
			searching = false;
		}
	}

	async function process(queue: boolean) {
		const lyrics =
			choice === 'none'
				? null
				: choice === 'own'
					? own.trim() || null
					: (found[choice]?.text ?? null);
		busy = true;
		try {
			const confirmed = await api.confirm(job.id, {
				title: title.trim(),
				artist: artist.trim() || null,
				language,
				lyrics,
				queue_on: queue ? (player()?.id ?? null) : null
			});
			live.state = {
				...live.state,
				jobs: live.state.jobs.map((j) => (j.id === job.id ? confirmed : j))
			};
			toasts.show(t.add.queued(confirmed.title));
		} catch (error) {
			fail(error);
		} finally {
			busy = false;
		}
	}

	const pct = (c: number) => Math.round(c * 100);
	const target = $derived(player());
</script>

<article class="panel review">
	<header class="panel-header">
		<span class="badge warn">{t.jobs.states.review}</span>
		<h2 class="job truncate">{job.title}</h2>
		<div class="actions">
			<button class="btn subtle" onclick={() => jobs.act([job.id], 'cancel')}>
				{t.add.discard}
			</button>
		</div>
	</header>

	<div class="body">
		<aside class="who">
			<div class="cover" style:background-image={cover ? `url("${cover}")` : undefined}>
				{#if !cover}<Icon name="mic" size={42} />{/if}
			</div>
			<p class="print {analysis.fingerprint === 'ok' ? 'ok' : ''}">
				<Icon name={analysis.fingerprint === 'ok' ? 'check' : 'warn'} size={14} />
				{t.add.fingerprint[analysis.fingerprint ?? 'skipped']}
			</p>
			{#if candidates.length > 1}
				<h3 class="muted small">{t.add.candidates}</h3>
				<ul class="guesses">
					{#each candidates as guess, i (i)}
						<li>
							<button
								class:chosen={guess.title === title && (guess.artist ?? '') === artist}
								onclick={() => use(guess)}
							>
								<span class="g-title">{guess.title}</span>
								<span class="muted small"
									>{guess.artist ?? '—'}{guess.year ? ` · ${guess.year}` : ''}</span
								>
								<span class="meta">
									<span class="faint small">{t.add.sources[guess.source] ?? guess.source}</span>
									<span class="progress ok"
										><span style:width="{pct(guess.confidence)}%"></span></span
									>
									<span class="mono small muted">{t.add.confidence(pct(guess.confidence))}</span>
								</span>
							</button>
						</li>
					{/each}
				</ul>
			{/if}
		</aside>

		<form class="form" onsubmit={(e) => (e.preventDefault(), void process(false))}>
			<div>
				<h3>{t.add.reviewTitle}</h3>
				<p class="muted lead">{t.add.reviewLead}</p>
			</div>
			<div class="fields">
				<label class="form-row wide">
					<span>{t.add.songTitle}</span>
					<input class="field big" bind:value={title} required maxlength="200" />
				</label>
				<label class="form-row">
					<span>{t.add.artist}</span>
					<input class="field" bind:value={artist} maxlength="200" />
				</label>
				<label class="form-row">
					<span>{t.add.language}</span>
					<select class="field" bind:value={language}>
						{#each LANGUAGES as code (code)}
							<option value={code}>{t.languages[code]}</option>
						{/each}
					</select>
				</label>
			</div>

			<fieldset class="lyrics">
				<legend>{t.add.lyrics} · {t.add.lyricsFound(found.length)}</legend>
				<div class="search">
					<input
						class="field"
						bind:value={query}
						placeholder={`${artist} ${title}`.trim()}
						aria-label={t.add.lyricsSearch}
						onkeydown={(e) => e.key === 'Enter' && (e.preventDefault(), void search())}
					/>
					<button type="button" class="btn" onclick={search} disabled={searching}>
						<Icon name="search" size={16} />
						{t.add.lyricsSearch}
					</button>
				</div>
				<ul class="options">
					{#each found as lyric, i (lyric.id)}
						<li class:chosen={choice === i}>
							<label>
								<input
									type="radio"
									name={`lyrics-${job.id}`}
									checked={choice === i}
									onchange={() => (choice = i)}
								/>
								<span class="o-title">{lyric.artist} — {lyric.title}</span>
								{#if lyric.synced}<span class="badge ok plain">{t.add.synced}</span>{/if}
								{#if lyric.duration_gap !== null}
									<span class="badge plain {Math.abs(lyric.duration_gap) > 5 ? 'warn' : ''}"
										>{t.add.gap(lyric.duration_gap.toFixed(1))}</span
									>
								{/if}
								<span class="mono muted small">{clock(lyric.duration)}</span>
								<button
									type="button"
									class="btn subtle peek"
									onclick={(e) => (e.preventDefault(), (open = open === i ? null : i))}
									aria-expanded={open === i}>{t.add.show}</button
								>
							</label>
							{#if open === i}<pre class="text">{lyric.text}</pre>{/if}
						</li>
					{/each}
					<li class:chosen={choice === 'own'}>
						<label>
							<input
								type="radio"
								name={`lyrics-${job.id}`}
								checked={choice === 'own'}
								onchange={() => (choice = 'own')}
							/>
							<span class="o-title">{t.add.lyricsOwn}</span>
						</label>
						{#if choice === 'own'}
							<textarea class="field" rows="8" bind:value={own} aria-label={t.add.lyricsOwn}
							></textarea>
						{/if}
					</li>
					<li class:chosen={choice === 'none'}>
						<label>
							<input
								type="radio"
								name={`lyrics-${job.id}`}
								checked={choice === 'none'}
								onchange={() => (choice = 'none')}
							/>
							<span class="o-title">{t.add.lyricsNone}</span>
						</label>
					</li>
				</ul>
			</fieldset>

			<div class="go">
				<button type="submit" class="btn primary large" disabled={busy || !title.trim()}>
					{t.add.process}
				</button>
				{#if target}
					<button
						type="button"
						class="btn large"
						disabled={busy || !title.trim()}
						onclick={() => process(true)}
					>
						{t.add.processTo(target.name)}
					</button>
				{/if}
			</div>
		</form>
	</div>
</article>

<style>
	.job {
		min-width: 0;
		font-size: 14px;
		font-weight: 500;
	}
	.body {
		display: grid;
		grid-template-columns: 260px minmax(0, 1fr);
	}
	.who {
		display: flex;
		flex-direction: column;
		gap: 12px;
		padding: 16px;
		border-right: 1px solid var(--border);
	}
	.cover {
		display: grid;
		place-items: center;
		aspect-ratio: 1;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: var(--surface-2) center / cover no-repeat;
		color: var(--faint);
	}
	.print {
		display: flex;
		gap: 8px;
		font-size: 13px;
		color: var(--warn);
	}
	.print.ok {
		color: var(--ok);
	}
	.guesses {
		display: grid;
		gap: 6px;
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.guesses button {
		display: grid;
		gap: 2px;
		width: 100%;
		padding: 8px 10px;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: transparent;
		text-align: left;
		cursor: pointer;
	}
	.guesses button:hover {
		background: var(--surface-2);
	}
	.guesses button.chosen {
		border-color: var(--accent);
		background: var(--accent-soft);
	}
	.g-title {
		font-weight: 500;
	}
	.meta {
		display: grid;
		grid-template-columns: auto 1fr auto;
		gap: 8px;
		align-items: center;
		margin-top: 4px;
	}
	.form {
		display: grid;
		gap: 18px;
		padding: 16px 20px 20px;
		min-width: 0;
	}
	h3 {
		font-size: 15px;
	}
	.lead {
		margin-top: 2px;
	}
	.fields {
		display: grid;
		grid-template-columns: minmax(0, 1fr) 220px;
		gap: 12px;
	}
	.fields .wide {
		grid-column: 1 / -1;
	}
	.field.big {
		height: 40px;
		font-size: 16px;
		font-weight: 500;
	}
	.lyrics {
		display: grid;
		gap: 10px;
		min-width: 0;
		margin: 0;
		padding: 0;
		border: 0;
	}
	legend {
		margin-bottom: 8px;
		color: var(--muted);
		font-size: 13px;
	}
	.search {
		display: flex;
		gap: 8px;
	}
	.options {
		display: grid;
		margin: 0;
		padding: 0;
		list-style: none;
		max-height: 360px;
		overflow-y: auto;
		overflow-x: hidden;
		border: 1px solid var(--border);
		border-radius: var(--radius);
	}
	.options li + li {
		border-top: 1px solid var(--border);
	}
	.options li.chosen {
		background: var(--accent-soft);
	}
	.options label {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 10px;
		padding: 8px 12px;
		cursor: pointer;
	}
	.o-title {
		flex: 1 1 12rem;
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.peek {
		height: 26px;
		padding: 0 8px;
	}
	.text {
		margin: 0;
		padding: 4px 14px 14px 36px;
		color: var(--muted);
		font: inherit;
		white-space: pre-wrap;
		max-height: 220px;
		overflow-y: auto;
	}
	.options textarea {
		margin: 0 12px 12px;
		width: calc(100% - 24px);
	}
	.go {
		display: flex;
		flex-wrap: wrap;
		gap: 10px;
	}
	@media (max-width: 980px) {
		.body {
			grid-template-columns: minmax(0, 1fr);
		}
		.who {
			border-right: 0;
			border-bottom: 1px solid var(--border);
		}
		.cover {
			max-width: 160px;
		}
		.fields {
			grid-template-columns: minmax(0, 1fr);
		}
	}
</style>
