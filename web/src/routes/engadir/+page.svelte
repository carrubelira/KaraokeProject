<script lang="ts">
	/**
	 * Add song: paste a link (or upload or drop a file) and the song is analysed at once: which
	 * song it is (the page, its sound fingerprint, MusicBrainz) and its lyrics. Below, what waits
	 * for the operator's review and what is still being analysed.
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

<div class="page">
	<header class="page-header">
		<div>
			<h1>{t.add.title}</h1>
			<p class="description">{t.add.lead}</p>
		</div>
	</header>

	<section class="panel">
		<form class="panel-body intake" onsubmit={analyse}>
			<label class="form-row">
				<span>{t.add.link}</span>
				<div class="bar">
					<input
						bind:this={field}
						bind:value={url}
						class="field"
						type="url"
						inputmode="url"
						placeholder={t.add.placeholder}
						data-search
					/>
					<button class="btn primary" type="submit" disabled={!valid || sending}>
						{t.add.analyse}
					</button>
				</div>
			</label>
			<div class="below">
				<button type="button" class="btn" onclick={() => picker?.click()}>
					<Icon name="file" size={16} />
					{t.add.chooseFile}
				</button>
				<span class="muted small">{t.add.orFile}</span>
				<input
					bind:this={picker}
					class="sr-only"
					type="file"
					accept="audio/*,video/*"
					multiple
					tabindex="-1"
					aria-hidden="true"
					onchange={(e) => {
						void intake.files([...(e.currentTarget.files ?? [])]);
						e.currentTarget.value = '';
					}}
				/>
				<label class="check auto">
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
					<span class="small muted">
						{t.add.uploading(upload.file.name, Math.round(upload.fraction * 100))}
					</span>
					<div class="progress"><span style:width="{upload.fraction * 100}%"></span></div>
				</div>
			{/each}
		</form>
	</section>

	{#if reviewing.length}
		<h2 class="section-title">{t.add.toReview}</h2>
		{#each reviewing as job (job.id)}
			<Review {job} />
		{/each}
	{/if}

	<section class="panel">
		<header class="panel-header">
			<h2>{t.add.inProgress}</h2>
			<span class="muted small">{analysing.length}</span>
		</header>
		{#each analysing as job (job.id)}
			<Analysing {job} />
		{:else}
			<div class="empty"><p>{t.add.nothing}</p></div>
		{/each}
	</section>
</div>

<style>
	.intake {
		display: grid;
		gap: 14px;
	}
	.bar {
		display: flex;
		gap: 8px;
	}
	.bar .field {
		height: 40px;
		font-size: 15px;
	}
	.bar .btn {
		height: 40px;
		padding: 0 20px;
	}
	.below {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 12px;
	}
	.auto {
		margin-left: auto;
		color: var(--muted);
	}
	.upload {
		display: grid;
		gap: 6px;
	}
	.section-title {
		margin-bottom: -8px;
	}
</style>
