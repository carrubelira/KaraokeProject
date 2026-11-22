<script lang="ts">
	/** Home: what is on, what comes next, what is being made and which machines are there. */
	import { resolve } from '$app/paths';
	import { BADGE, describeJob } from '#lib/control/describe.js';
	import { live } from '#lib/control/live.svelte.js';
	import { positionNow } from '#lib/control/state.js';
	import { i18n } from '#lib/i18n';
	import { content, player, playlist } from '#lib/shell/actions.svelte.js';
	import { clock, when } from '#lib/shell/format.js';

	const t = $derived(i18n.t);
	let now = $state(performance.now());
	$effect(() => {
		const timer = setInterval(() => (now = performance.now()), 500);
		return () => clearInterval(timer);
	});

	const target = $derived(player());
	const items = $derived(playlist()?.items ?? []);
	const index = $derived(items.findIndex((i) => i.id === target?.status.item_id));
	const current = $derived(index >= 0 ? items[index] : undefined);
	const song = $derived(current ? content(current.content_id) : undefined);
	const next = $derived(items[index + 1]);
	const nextSong = $derived(next ? content(next.content_id) : undefined);
	const position = $derived(target ? positionNow(live.state, target, now) : null);
	const end = $derived(current?.end ?? song?.duration ?? null);

	const running = $derived(
		live.state.jobs.filter((j) => j.state === 'active').map((j) => ({ job: j, s: describeJob(j) }))
	);
	const furthest = $derived(running.toSorted((a, b) => b.s.fraction - a.s.fraction)[0]);
	const failed = $derived(live.state.jobs.filter((j) => j.state === 'failed').length);
	const workers = $derived(live.state.nodes.filter((n) => n.kind === 'worker'));
	const players = $derived(live.state.nodes.filter((n) => n.kind === 'player'));
	const busy = $derived(workers.filter((n) => n.online && n.running.length).length);
	const recent = $derived(
		live.state.jobs.toSorted((a, b) => b.created_at.localeCompare(a.created_at)).slice(0, 5)
	);
</script>

<div class="ctl-page">
	<header class="ctl-page-head">
		<h1>{t.home.title}</h1>
		<span class="ctl-sub">{t.library.count(live.state.contents.length)}</span>
	</header>

	<div class="cards ctl-cards">
		<section class="ctl-panel">
			<div class="ctl-panel-head">
				<h2>{t.home.now}</h2>
				<a class="ctl-actions" href={resolve('/directo')}>{t.nav.live}</a>
			</div>
			<div class="ctl-panel-body">
				{#if song}
					<p class="big">{song.title}</p>
					<p class="ctl-muted">
						{song.artist ?? ''}{#if current?.singer}
							· {current.singer}{/if}
					</p>
					<p class="ctl-mono line">{clock(position)} / {clock(end)}</p>
				{:else}
					<p class="ctl-muted">{t.status.nothing}</p>
				{/if}
				<p class="ctl-muted small">{target?.name ?? t.status.noPlayer}</p>
			</div>
		</section>

		<section class="ctl-panel">
			<div class="ctl-panel-head"><h2>{t.home.next}</h2></div>
			<div class="ctl-panel-body">
				{#if nextSong}
					<p class="big">{nextSong.title}</p>
					<p class="ctl-muted">
						{nextSong.artist ?? ''}{#if next?.singer}
							· {next.singer}{/if}
					</p>
				{:else}
					<p class="ctl-muted">{t.home.nothingNext}</p>
				{/if}
				<p class="ctl-muted small">{t.home.inList(items.length)}</p>
			</div>
		</section>

		<section class="ctl-panel">
			<div class="ctl-panel-head">
				<h2>{t.home.jobs}</h2>
				<a class="ctl-actions" href={resolve('/cola')}>{t.nav.jobs}</a>
			</div>
			<div class="ctl-panel-body">
				<p class="big ctl-mono">{running.length}</p>
				{#if furthest}
					<p class="ctl-muted ellipsis">
						{furthest.job.title} · {furthest.s.step ? t.jobs.steps[furthest.s.step] : ''}
					</p>
				{:else}
					<p class="ctl-muted">{t.home.noJobs}</p>
				{/if}
				<p class="small" class:bad={failed} class:ctl-muted={!failed}>{t.home.failed(failed)}</p>
			</div>
		</section>

		<section class="ctl-panel">
			<div class="ctl-panel-head">
				<h2>{t.home.machines}</h2>
				<a class="ctl-actions" href={resolve('/equipos')}>{t.nav.machines}</a>
			</div>
			<div class="ctl-panel-body">
				<p class="big ctl-mono">
					{workers.filter((n) => n.online).length}<span class="ctl-muted"
						>&nbsp;/&nbsp;{workers.length}</span
					>
				</p>
				<p class="ctl-muted">{t.home.workersOnline(busy)}</p>
				<p class="ctl-muted small">
					{t.home.players(players.filter((n) => n.online).length, players.length)}
				</p>
			</div>
		</section>
	</div>

	<section class="ctl-panel recent">
		<div class="ctl-panel-head"><h2>{t.home.recent}</h2></div>
		{#if recent.length === 0}
			<p class="ctl-empty">{t.jobs.empty}</p>
		{:else}
			<table class="ctl-table">
				<thead>
					<tr>
						<th>{t.jobs.columns.title}</th>
						<th>{t.jobs.columns.state}</th>
						<th>{t.jobs.columns.step}</th>
						<th class="ctl-num">{t.jobs.columns.progress}</th>
						<th class="ctl-num">{t.jobs.columns.created}</th>
					</tr>
				</thead>
				<tbody>
					{#each recent as job (job.id)}
						{@const s = describeJob(job)}
						<tr>
							<td class="ctl-title">{job.title}</td>
							<td><span class="ctl-badge {BADGE[s.status]}">{t.jobs.status[s.status]}</span></td>
							<td>{s.step ? t.jobs.steps[s.step] : ''}</td>
							<td class="ctl-num">{Math.round(s.fraction * 100)} %</td>
							<td class="ctl-num ctl-muted">{when(job.created_at, i18n.locale)}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</section>
</div>

<style>
	.cards {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(15rem, 1fr));
		gap: var(--sp-4);
	}
	.ctl-panel-body {
		display: grid;
		gap: var(--sp-1);
		min-height: 7.5rem;
		align-content: start;
	}
	.big {
		font-size: var(--fs-xl);
		font-weight: 600;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.ellipsis {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.small {
		margin-top: auto;
		font-size: var(--fs-s);
	}
	.bad {
		color: #f1a5a3;
	}
	.line {
		color: var(--text-2);
	}
	a.ctl-actions {
		font-size: var(--fs-s);
	}
	.recent {
		margin-top: var(--sp-4);
	}
</style>
