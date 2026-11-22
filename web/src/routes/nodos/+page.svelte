<script lang="ts">
	/**
	 * Nodes: every worker and screen as a rack unit. Workers show their GPU, VRAM, CPU, RAM and
	 * temperature live (every heartbeat), what they are running and at which step; screens show
	 * their state, displays, sound outputs and whatever does not work on them. New nodes are
	 * enrolled from here, with the exact command to paste.
	 */
	import { onMount } from 'svelte';
	import { commands } from '#lib/commands/registry.svelte.js';
	import Icon from '#lib/console/Icon.svelte';
	import { onAir, tallyOf } from '#lib/console/on-air.js';
	import { api } from '#lib/control/api.js';
	import { live } from '#lib/control/live.svelte.js';
	import { toasts } from '#lib/control/toasts.svelte.js';
	import type { NodeView } from '#lib/control/types.js';
	import { i18n } from '#lib/i18n';
	import { fail } from '#lib/shell/actions.svelte.js';
	import { ago, megabytes } from '#lib/shell/format.js';

	const t = $derived(i18n.t);
	const workers = $derived(live.state.nodes.filter((n) => n.kind === 'worker'));
	const screens = $derived(live.state.players);
	let token = $state<{ kind: 'worker' | 'player'; token: string } | null>(null);
	let server = $state<{ fingerprint: string; version: string } | null>(null);

	function tasksOf(node: NodeView) {
		return node.running
			.map((id) => {
				const job = live.state.jobs.find((j) => j.tasks.some((x) => x.id === id));
				const task = job?.tasks.find((x) => x.id === id);
				return job && task ? { job, task } : null;
			})
			.filter((x) => x !== null);
	}

	function workerTally(node: NodeView): string {
		if (!node.online) return 'off';
		if (node.running.length) return 'info';
		return 'cue';
	}

	async function enrol(kind: 'worker' | 'player') {
		try {
			const made = await api.enrollment(kind);
			token = { kind, token: made.token };
			server ??= await api.server();
		} catch (error) {
			fail(error);
		}
	}

	async function revoke(node: { id: string; name: string }) {
		try {
			await api.revoke(node.id);
			toasts.show(t.nodes.revoked(node.name));
		} catch (error) {
			fail(error);
		}
	}

	const command = $derived.by(() => {
		if (!token || !server) return '';
		const base = location.origin;
		return token.kind === 'worker'
			? `karaoke-worker enroll ${base} ${token.token} --fingerprint ${server.fingerprint}`
			: `kp-player enroll ${base} ${token.token} --fingerprint ${server.fingerprint} --name sala`;
	});

	const pct = (v: number | null | undefined) => (v === null || v === undefined ? null : v / 100);

	onMount(() => {
		commands.scope = 'nodes';
	});
</script>

<div class="c-page">
	<div class="c-page-head">
		<h1>{t.nodes.title}</h1>
		<span class="spacer"></span>
		<button class="c-btn" onclick={() => enrol('worker')}
			><Icon name="gpu" size={16} /> {t.cmd.enrolWorker}</button
		>
		<button class="c-btn" onclick={() => enrol('player')}
			><Icon name="screen" size={16} /> {t.cmd.enrolPlayer}</button
		>
	</div>

	{#if token}
		<section class="c-panel is-cue">
			<header class="c-panel-head">
				<h2>{t.nodes.token}</h2>
				<span class="spacer"></span>
				<button class="c-btn icon ghost" aria-label={t.common.close} onclick={() => (token = null)}
					><Icon name="close" size={16} /></button
				>
			</header>
			<div class="c-panel-body enrol">
				<span class="label">{token.kind === 'worker' ? t.nodes.howWorker : t.nodes.howPlayer}</span>
				<code class="c-code">{command || token.token}</code>
				<button
					class="c-btn"
					onclick={() =>
						navigator.clipboard.writeText(command).then(() => toasts.show(t.common.copied))}
				>
					{t.common.copy}
				</button>
			</div>
		</section>
	{/if}

	<div class="columns">
		<section class="c-panel">
			<header class="c-panel-head">
				<Icon name="gpu" size={16} />
				<h2>{t.nodes.workers}</h2>
				<span class="spacer"></span>
				<span class="label">{workers.filter((w) => w.online).length}/{workers.length}</span>
			</header>
			{#each workers as node (node.id)}
				{@const gpu = node.capabilities.gpus[0]}
				{@const tel = node.telemetry}
				<article class="rack" class:off={!node.online}>
					<header>
						<span class="c-tally {workerTally(node)}"
							>{node.online
								? node.running.length
									? t.nodes.running(node.running.length)
									: t.nodes.idle
								: t.nodes.offline}</span
						>
						<strong>{node.name}</strong>
						<span class="dim small">{node.capabilities.os} · {gpu?.name ?? 'CPU'}</span>
						<span class="spacer"></span>
						{#if !node.online}<span class="faint small mono"
								>{t.nodes.lastSeen(ago(node.last_seen))}</span
							>{/if}
						<button class="c-btn ghost danger-text" onclick={() => revoke(node)}
							>{t.nodes.revoke}</button
						>
					</header>
					<div class="meters">
						{@render meter(
							t.nodes.gpu,
							pct(tel.gpu_util),
							tel.gpu_util !== null ? `${Math.round(tel.gpu_util)} %` : '—'
						)}
						{@render meter(
							t.nodes.vram,
							gpu && tel.vram_used_mb !== null ? tel.vram_used_mb / gpu.vram_total_mb : null,
							t.nodes.of(megabytes(tel.vram_used_mb), megabytes(gpu?.vram_total_mb))
						)}
						{@render meter(
							t.nodes.cpu,
							pct(tel.cpu_util),
							tel.cpu_util !== null ? `${Math.round(tel.cpu_util)} %` : '—'
						)}
						{@render meter(
							t.nodes.ram,
							tel.ram_used_mb !== null && tel.ram_total_mb
								? tel.ram_used_mb / tel.ram_total_mb
								: null,
							t.nodes.of(megabytes(tel.ram_used_mb), megabytes(tel.ram_total_mb))
						)}
						<div class="temp">
							<span class="label">°C</span>
							<span class="mono" class:hot={(tel.gpu_temp_c ?? 0) > 80}
								>{tel.gpu_temp_c !== null ? t.nodes.temp(tel.gpu_temp_c) : '—'}</span
							>
						</div>
					</div>
					{#each tasksOf(node) as { job, task } (task.id)}
						<div class="running">
							<span class="c-tally info"></span>
							<span class="r-title">{job.title}</span>
							<span class="dim"
								>{t.jobs.kinds[task.kind]} · {task.stage
									? (t.jobs.stages[task.stage] ?? task.stage)
									: t.jobs.tasks[task.state]}{task.step ? ` · ${task.step}` : ''}</span
							>
							{#if task.fraction !== null}<span class="c-meter info" style:--value={task.fraction}
								></span>{/if}
						</div>
					{/each}
					{#if node.busy_playing}<p class="note warn">{t.nodes.busyPlaying}</p>{/if}
					<footer class="caps">
						<span class="label">{t.nodes.takes}</span>
						{#each node.capabilities.tasks as kind (kind)}<span class="c-tag"
								>{t.jobs.kinds[kind as keyof typeof t.jobs.kinds] ?? kind}</span
							>{/each}
					</footer>
				</article>
			{:else}
				<p class="c-empty">{t.nodes.emptyWorkers}</p>
			{/each}
		</section>

		<section class="c-panel">
			<header class="c-panel-head">
				<Icon name="screen" size={16} />
				<h2>{t.nodes.players}</h2>
				<span class="spacer"></span>
				<span class="label">{screens.filter((p) => p.online).length}/{screens.length}</span>
			</header>
			{#each screens as p (p.id)}
				{@const air = onAir(live.state, p)}
				{@const tally = tallyOf(p)}
				<article class="rack" class:off={!p.online}>
					<header>
						<span class="c-tally {tally}"
							>{p.online ? t.strip[tally === 'onair' ? 'onAir' : 'standby'] : t.nodes.offline}</span
						>
						<strong>{p.name}</strong>
						<span class="dim small"
							>{t.nodes.displays(p.status.outputs.displays.length)} · {t.nodes.outputs(
								p.status.outputs.audio.length
							)}</span
						>
						<span class="spacer"></span>
						<button class="c-btn ghost danger-text" onclick={() => revoke(p)}
							>{t.nodes.revoke}</button
						>
					</header>
					{#if air.song}
						<div class="running">
							<span class="c-tally {tally}"></span>
							<span class="r-title">{air.song.title}</span>
							<span class="dim">{air.song.artist ?? ''}</span>
						</div>
					{/if}
					{#each p.status.errors ?? [] as error, i (i)}
						<p class="note warn">
							<Icon name="warn" size={14} />
							{t.playerErrors[error.code] ?? error.code}
							<span class="mono faint">{error.device ?? ''}</span>
						</p>
					{/each}
					{#each p.status.cache.filter((c) => c.state !== 'ready') as c (c.content_id)}
						<div class="running">
							<span class="dim"
								>{live.state.contents.find((x) => x.id === c.content_id)?.title ??
									c.content_id}</span
							>
							<span class="c-tag {c.state === 'failed' ? 'onair' : 'info'}"
								>{t.live.cache[c.state]}</span
							>
							<span class="c-meter info" style:--value={c.fraction}></span>
						</div>
					{/each}
				</article>
			{:else}
				<p class="c-empty">{t.nodes.emptyPlayers}</p>
			{/each}
		</section>
	</div>
</div>

{#snippet meter(name: string, value: number | null, text: string)}
	<div class="meter">
		<span class="label">{name}</span>
		<span
			class="c-meter {value !== null && value > 0.85
				? 'hot'
				: value !== null && value > 0.65
					? 'warn'
					: ''}"
			style:--value={value ?? 0}
		></span>
		<span class="mono small">{text}</span>
	</div>
{/snippet}

<style>
	.columns {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
		gap: var(--gap);
		align-items: start;
	}
	.enrol {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr) auto;
		gap: 12px;
		align-items: center;
	}
	.rack {
		display: grid;
		gap: 12px;
		padding: 14px;
		border-bottom: 1px solid var(--line);
	}
	.rack:last-child {
		border-bottom: 0;
	}
	.rack.off {
		opacity: 0.55;
	}
	.rack header {
		display: flex;
		align-items: center;
		gap: 12px;
		flex-wrap: wrap;
	}
	.small {
		font-size: 12px;
	}
	.spacer {
		flex: 1;
	}
	.danger-text:hover:not(:disabled) {
		color: var(--onair);
	}
	.meters {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr)) auto;
		gap: 14px;
	}
	.meter,
	.temp {
		display: grid;
		gap: 6px;
		min-width: 0;
	}
	.meter .mono {
		color: var(--dim);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.hot {
		color: var(--onair);
	}
	.running {
		display: grid;
		grid-template-columns: auto minmax(0, 1fr) auto;
		grid-template-areas: 'lamp title what' 'meter meter meter';
		gap: 6px 10px;
		align-items: center;
		padding: 8px 10px;
		background: rgb(60 200 255 / 0.04);
		border: 1px solid rgb(60 200 255 / 0.15);
		font-size: 13px;
	}
	.running .c-meter {
		grid-area: meter;
	}
	.r-title {
		font-weight: 600;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.note {
		display: flex;
		align-items: center;
		gap: 8px;
		margin: 0;
		font-size: 13px;
	}
	.note.warn {
		color: var(--warn);
	}
	.caps {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px;
	}
	@media (max-width: 640px) {
		.meters {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
		.enrol {
			grid-template-columns: minmax(0, 1fr);
		}
	}
</style>
