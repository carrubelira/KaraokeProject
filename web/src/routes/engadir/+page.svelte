<script lang="ts">
	/**
	 * Add: one field. Paste a link (or drop a file) and the song is analysed at once: which song
	 * it is (the page, its sound fingerprint, MusicBrainz) and its lyrics. Below, what is being
	 * analysed, live, and what waits for the operator's review.
	 */
	import { onMount } from 'svelte';
	import { commands } from '#lib/commands/registry.svelte.js';
	import Analysing from '#lib/console/Analysing.svelte';
	import Icon from '#lib/console/Icon.svelte';
	import Review from '#lib/console/Review.svelte';
	import { live } from '#lib/control/live.svelte.js';
	import type { Job } from '#lib/control/types.js';
	import { i18n } from '#lib/i18n';
	import { intake, looksLikeLink } from '#lib/shell/intake.svelte.js';
	import { prefs } from '#lib/shell/prefs.svelte.js';

	const t = $derived(i18n.t);
	let url = $state('');
	let sending = $state(false);
	let picker: HTMLInputElement | undefined = $state();
	let field: HTMLInputElement | undefined = $state();

	const creating = (j: Job) => j.kind === 'create';
	const analysing = $derived(
		live.state.jobs.filter(
			(j) =>
				creating(j) &&
				(j.state === 'active' || j.state === 'failed') &&
				j.tasks.some((x) => (x.kind === 'fetch' || x.kind === 'analyze') && x.state !== 'done')
		)
	);
	const reviewing = $derived(live.state.jobs.filter((j) => creating(j) && j.state === 'review'));
	const valid = $derived(looksLikeLink(url));

	async function analyse(event?: SubmitEvent) {
		event?.preventDefault();
		if (!valid) return;
		sending = true;
		const job = await intake.link(url.trim());
		sending = false;
		if (job) url = '';
	}

	onMount(() => {
		commands.scope = 'add';
		field?.focus();
	});
</script>

<div class="c-page add">
	<section class="c-panel hero">
		<form class="intake" onsubmit={analyse}>
			<div class="head">
				<span class="label">{t.add.link}</span>
				<h1>{t.add.title}</h1>
				<p class="dim">{t.add.lead}</p>
			</div>
			<div class="bar" class:valid>
				<Icon name="link" size={22} />
				<input
					bind:this={field}
					bind:value={url}
					type="url"
					inputmode="url"
					placeholder={t.add.placeholder}
					aria-label={t.add.link}
					data-search
				/>
				<button class="c-btn primary big" type="submit" disabled={!valid || sending}>
					{t.add.analyse}
				</button>
			</div>
			<div class="below">
				<button type="button" class="c-btn ghost" onclick={() => picker?.click()}>
					<Icon name="file" size={16} />
					{t.add.chooseFile}
				</button>
				<span class="faint">{t.add.orFile}</span>
				<input
					bind:this={picker}
					class="sr-only"
					type="file"
					accept="audio/*,video/*"
					multiple
					onchange={(e) => {
						void intake.files([...(e.currentTarget.files ?? [])]);
						e.currentTarget.value = '';
					}}
				/>
				<span class="spacer"></span>
				<label class="c-check">
					<input
						type="checkbox"
						checked={prefs.value.autoConfirm}
						onchange={(e) => prefs.set('autoConfirm', e.currentTarget.checked)}
					/>
					{t.add.autoConfirm}
				</label>
			</div>
			{#each intake.uploads as upload (upload)}
				<div class="upload">
					<span class="mono small"
						>{t.add.uploading(upload.file.name, Math.round(upload.fraction * 100))}</span
					>
					<div class="c-progress" style:--value={upload.fraction}></div>
				</div>
			{/each}
		</form>
	</section>

	{#if reviewing.length}
		<div class="reviews">
			{#each reviewing as job (job.id)}
				<Review {job} />
			{/each}
		</div>
	{/if}

	<section class="c-panel">
		<header class="c-panel-head">
			<h2>{t.add.inProgress}</h2>
			<span class="spacer"></span>
			<span class="label">{analysing.length}</span>
		</header>
		{#each analysing as job (job.id)}
			<Analysing {job} />
		{:else}
			<p class="c-empty">{t.add.nothing}</p>
		{/each}
	</section>
</div>

<style>
	.hero {
		overflow: hidden;
	}
	.hero::before {
		border-color: var(--lyric);
	}
	.intake {
		display: grid;
		gap: 18px;
		padding: clamp(18px, 3vw, 34px);
		background:
			radial-gradient(ellipse 60% 120% at 100% 0%, rgb(255 201 77 / 0.08), transparent 60%),
			radial-gradient(ellipse 50% 100% at 0% 100%, rgb(60 200 255 / 0.06), transparent 60%);
	}
	h1 {
		margin: 6px 0 8px;
		font: 700 clamp(28px, 4vw, 46px) / 1 var(--font-display);
		text-transform: uppercase;
		letter-spacing: -0.02em;
	}
	.head p {
		margin: 0;
		max-width: 60ch;
	}
	.bar {
		display: flex;
		align-items: center;
		gap: 14px;
		padding: 8px 8px 8px 18px;
		border: 1px solid var(--line-strong);
		background: rgb(2 3 5 / 0.8);
		border-radius: var(--radius);
		color: var(--faint);
		transition:
			border-color 0.2s,
			box-shadow 0.2s;
	}
	.bar:focus-within {
		border-color: var(--info);
		box-shadow: 0 0 0 4px rgb(60 200 255 / 0.1);
	}
	.bar.valid {
		color: var(--cue);
		border-color: rgb(36 227 143 / 0.6);
	}
	.bar input {
		flex: 1;
		min-width: 0;
		height: 52px;
		border: 0;
		background: transparent;
		font: 500 clamp(15px, 1.6vw, 20px) var(--font-mono);
		color: var(--text);
		outline: none;
	}
	.below {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 12px;
		font-size: 13px;
	}
	.spacer {
		flex: 1;
	}
	.upload {
		display: grid;
		gap: 6px;
	}
	.small {
		font-size: 12px;
	}
	.reviews {
		display: grid;
		gap: var(--gap);
	}
</style>
