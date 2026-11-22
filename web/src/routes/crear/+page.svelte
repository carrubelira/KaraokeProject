<script lang="ts">
	/** Create: files or a link, lyrics pasted or found on LRCLIB, and the uploads going up. */
	import { api } from '#lib/control/api.js';
	import type { Candidate } from '#lib/control/types.js';
	import { i18n } from '#lib/i18n';
	import { fail } from '#lib/shell/actions.svelte.js';
	import { intake, looksLikeLink } from '#lib/shell/intake.svelte.js';
	import Kbd from '#lib/shell/Kbd.svelte';

	const t = $derived(i18n.t);
	let files = $state<File[]>([]);
	let url = $state('');
	let lyrics = $state('');
	let title = $state('');
	let artist = $state('');
	let lrclib = $state(false);
	let candidates = $state<Candidate[]>([]);
	let searching = $state(false);
	const LANGUAGES = ['gl', 'es', 'pt', 'en', 'ca', 'eu', 'fr', 'it', 'de'];

	async function search() {
		searching = true;
		try {
			candidates = await api.searchLyrics(`${artist} ${title}`.trim() || url);
		} catch (error) {
			fail(error);
		} finally {
			searching = false;
		}
	}

	async function submit(event?: SubmitEvent) {
		event?.preventDefault();
		const options = { lyrics, lrclib: lrclib && !lyrics, language: intake.language, title, artist };
		if (looksLikeLink(url)) await intake.link(url.trim(), options);
		if (files.length) await intake.files(files, options);
		files = [];
		url = '';
		lyrics = '';
		title = '';
		artist = '';
		candidates = [];
	}
</script>

<div class="ctl-page">
	<header class="ctl-page-head">
		<h1>{t.create.title}</h1>
		<span class="ctl-sub">{t.create.drop}</span>
	</header>
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<form
		class="ctl-columns"
		onsubmit={submit}
		onkeydown={(e) => e.key === 'Enter' && (e.ctrlKey || e.metaKey) && submit()}
	>
		<section class="ctl-panel">
			<div class="ctl-panel-head"><h2>{t.create.source}</h2></div>
			<div class="ctl-panel-body ctl-form">
				<label class="ctl-field">
					<span>{t.create.url}</span>
					<input
						class="ctl-input"
						type="url"
						bind:value={url}
						placeholder="https://…"
						data-search
					/>
				</label>
				<label class="ctl-field">
					<span>{t.create.file}</span>
					<input
						type="file"
						multiple
						accept="audio/*,video/*"
						onchange={(e) => (files = [...(e.currentTarget.files ?? [])])}
					/>
					<span class="ctl-help">{t.create.fileHelp}</span>
				</label>
				<div class="two">
					<label class="ctl-field"
						><span>{t.create.title_}</span><input class="ctl-input" bind:value={title} /></label
					>
					<label class="ctl-field"
						><span>{t.create.artist}</span><input class="ctl-input" bind:value={artist} /></label
					>
				</div>
				<label class="ctl-field">
					<span>{t.create.language}</span>
					<select class="ctl-select" bind:value={intake.language}>
						{#each LANGUAGES as l (l)}<option value={l}>{l}</option>{/each}
					</select>
				</label>
				<label class="ctl-check"
					><input type="checkbox" bind:checked={lrclib} /> {t.create.lrclibAuto}</label
				>
				<div>
					<button
						class="ctl-btn ctl-primary"
						type="submit"
						disabled={!files.length && !looksLikeLink(url)}
						>{t.create.submit} <Kbd keys="Mod+Enter" /></button
					>
				</div>
			</div>
		</section>

		<section class="ctl-panel">
			<div class="ctl-panel-head">
				<h2>{t.create.lyrics}</h2>
				<div class="ctl-actions">
					<button
						class="ctl-btn"
						type="button"
						onclick={search}
						disabled={searching || (!title && !artist)}>{t.create.lrclib}</button
					>
				</div>
			</div>
			<div class="ctl-panel-body ctl-form">
				<label class="ctl-field">
					<span class="visually-hidden">{t.create.lyrics}</span>
					<textarea class="ctl-textarea" rows="14" bind:value={lyrics}></textarea>
					<span class="ctl-help">{t.create.lyricsHint}</span>
				</label>
			</div>
			{#if candidates.length}
				<table class="ctl-table" aria-label={t.create.candidates}>
					<thead>
						<tr>
							<th>{t.create.candidates}</th>
							<th>{t.create.timing}</th>
							<th class="ctl-num">{t.create.difference}</th>
							<th></th>
						</tr>
					</thead>
					<tbody>
						{#each candidates as c (c.id)}
							<tr>
								<td class="ctl-title"
									>{c.title}<span class="ctl-muted ctl-after">
										· {c.artist}{#if c.album}
											· {c.album}{/if}</span
									></td
								>
								<td
									>{#if c.synced}<span class="ctl-badge ctl-ok">{t.create.synced}</span>{/if}</td
								>
								<td class="ctl-num"
									>{c.duration_gap !== null ? t.create.gap(String(c.duration_gap)) : ''}</td
								>
								<td class="ctl-shrink"
									><button class="ctl-btn" type="button" onclick={() => (lyrics = c.text)}
										>{t.create.use}</button
									></td
								>
							</tr>
						{/each}
					</tbody>
				</table>
			{/if}
		</section>
	</form>
	{#if intake.uploads.length}
		<section class="ctl-panel uploads">
			<div class="ctl-panel-head"><h2>{t.create.uploads}</h2></div>
			<table class="ctl-table">
				<tbody>
					{#each intake.uploads as upload (upload.file.name + upload.file.size)}
						<tr>
							<td class="ctl-title">{upload.file.name}</td>
							<td>
								<div class="ctl-progress">
									<div class="ctl-track">
										<span style:width={`${Math.round(upload.fraction * 100)}%`}></span>
									</div>
									<span class="ctl-pct">{Math.round(upload.fraction * 100)} %</span>
								</div>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</section>
	{/if}
</div>

<style>
	.two {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--sp-3);
	}
	.uploads {
		margin-top: var(--sp-4);
	}
</style>
