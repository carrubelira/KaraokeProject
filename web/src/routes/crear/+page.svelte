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
	<div class="ctl-page-head">
		<h1>{t.create.title}</h1>
		<span class="ctl-muted">{t.create.drop}</span>
	</div>
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<form
		class="ctl-grid-2"
		onsubmit={submit}
		onkeydown={(e) => e.key === 'Enter' && (e.ctrlKey || e.metaKey) && submit()}
	>
		<div class="ctl-box col">
			<label
				>{t.create.file}<input
					class="ctl-field"
					type="file"
					multiple
					accept="audio/*,video/*"
					onchange={(e) => (files = [...(e.currentTarget.files ?? [])])}
				/></label
			>
			<label
				>{t.create.url}<input
					class="ctl-field"
					type="url"
					bind:value={url}
					placeholder="https://…"
					data-search
				/></label
			>
			<div class="two">
				<label>{t.create.title_}<input class="ctl-field" bind:value={title} /></label>
				<label>{t.create.artist}<input class="ctl-field" bind:value={artist} /></label>
			</div>
			<label
				>{t.create.language}
				<select class="ctl-field" bind:value={intake.language}>
					{#each LANGUAGES as l (l)}<option value={l}>{l}</option>{/each}
				</select>
			</label>
			<label class="check"><input type="checkbox" bind:checked={lrclib} /> {t.create.lrclib}</label>
			<button
				class="ctl-btn ctl-primary"
				type="submit"
				disabled={!files.length && !looksLikeLink(url)}
				>{t.create.submit} <Kbd keys="Mod+Enter" /></button
			>
		</div>
		<div class="ctl-box col">
			<label
				>{t.create.lyrics}<textarea class="ctl-field" rows="14" bind:value={lyrics}
				></textarea></label
			>
			<p class="ctl-muted">{t.create.lyricsHint}</p>
			<button
				class="ctl-btn"
				type="button"
				onclick={search}
				disabled={searching || (!title && !artist)}>{t.create.lrclib}</button
			>
			{#if candidates.length}
				<h2>{t.create.candidates}</h2>
				<ul class="ctl-rows">
					{#each candidates as c (c.id)}
						<li class="ctl-row candidate">
							<span
								><strong>{c.title}</strong> · {c.artist}{#if c.album}<span class="ctl-muted">
										· {c.album}</span
									>{/if}</span
							>
							<span class="ctl-muted"
								>{#if c.synced}<span class="ctl-pill ctl-ok">{t.create.synced}</span>{/if}
								{c.duration_gap !== null ? t.create.gap(String(c.duration_gap)) : ''}</span
							>
							<button class="ctl-btn" type="button" onclick={() => (lyrics = c.text)}
								>{t.create.use}</button
							>
						</li>
					{/each}
				</ul>
			{/if}
		</div>
	</form>
	{#if intake.uploads.length}
		<section class="ctl-box uploads">
			{#each intake.uploads as upload (upload.file.name + upload.file.size)}
				<p>{upload.file.name} · {t.create.uploading(Math.round(upload.fraction * 100))}</p>
				<div class="ctl-bar">
					<span style:width={`${Math.round(upload.fraction * 100)}%`}></span>
				</div>
			{/each}
		</section>
	{/if}
</div>

<style>
	.col {
		display: grid;
		gap: var(--s-3);
		align-content: start;
	}
	label {
		display: grid;
		gap: var(--s-1);
		color: var(--texto-2);
	}
	.check {
		display: flex;
		align-items: center;
		gap: var(--s-2);
	}
	.two {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--s-3);
	}
	textarea {
		font-family: var(--font-text);
		resize: vertical;
	}
	.candidate {
		grid-template-columns: 1fr auto auto;
	}
	.uploads {
		margin-top: var(--s-4);
	}
</style>
