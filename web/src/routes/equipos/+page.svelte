<script lang="ts">
	/**
	 * Devices: the computers that make the karaokes and the screens that play them, each one a
	 * row. Processing computers show their GPU, its memory, CPU, memory and temperature (every
	 * heartbeat) and what they are making; screens show what they play, their monitors and sound
	 * outputs and whatever does not work on them. New ones are added from here, with the exact
	 * command to paste.
	 */
	import { onMount } from 'svelte';
	import { commands } from '#lib/commands/registry.svelte.js';
	import Icon from '#lib/console/Icon.svelte';
	import { onScreen, toneOf } from '#lib/console/screen.js';
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
			toasts.show(t.devices.revoked(node.name));
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

	const ratio = (used: number | null | undefined, total: number | null | undefined) =>
		used === null || used === undefined || !total ? null : used / total;

	onMount(() => {
		commands.scope = 'nodes';
	});
</script>

<div class="page">
	<header class="page-header">
		<div>
			<h1>{t.devices.title}</h1>
			<p class="description">{t.devices.description}</p>
		</div>
	</header>

	{#if token}
		<section class="panel">
			<header class="panel-header">
				<h2>{t.devices.token}</h2>
				<div class="actions">
					<button class="btn subtle icon" aria-label={t.common.close} onclick={() => (token = null)}
						><Icon name="close" size={16} /></button
					>
				</div>
			</header>
			<div class="panel-body enrol">
				<p class="muted">{token.kind === 'worker' ? t.devices.howWorker : t.devices.howPlayer}</p>
				<div class="code-row">
					<code class="code">{command || token.token}</code>
					<button
						class="btn"
						onclick={() =>
							navigator.clipboard.writeText(command).then(() => toasts.show(t.common.copied))}
					>
						{t.common.copy}
					</button>
				</div>
				{#if server}
					<p class="faint small">
						{t.devices.fingerprint}: <span class="mono">{server.fingerprint}</span>
					</p>
				{/if}
			</div>
		</section>
	{/if}

	<section class="panel">
		<header class="panel-header">
			<h2>{t.devices.workers}</h2>
			<span class="muted small">{workers.filter((w) => w.online).length} / {workers.length}</span>
			<div class="actions">
				<button class="btn" onclick={() => enrol('worker')}>
					<Icon name="add" size={16} />
					{t.cmd.enrolWorker}
				</button>
			</div>
		</header>
		{#if workers.length}
			<table class="table workers">
				<thead>
					<tr>
						<th>{t.devices.name}</th>
						<th>{t.devices.status}</th>
						<th>{t.devices.gpu}</th>
						<th>{t.devices.vram}</th>
						<th>{t.devices.cpu}</th>
						<th>{t.devices.ram}</th>
						<th>{t.devices.current}</th>
						<th><span class="sr-only">{t.common.more}</span></th>
					</tr>
				</thead>
				<tbody>
					{#each workers as node (node.id)}
						{@const gpu = node.capabilities.gpus[0]}
						{@const tel = node.telemetry}
						{@const running = tasksOf(node)}
						<tr class:off={!node.online}>
							<td>
								<div class="name">
									<strong>{node.name}</strong>
									<span class="muted small">{node.capabilities.os} · {gpu?.name ?? 'CPU'}</span>
								</div>
							</td>
							<td>
								{#if !node.online}
									<span class="badge plain">{t.devices.disconnected}</span>
									<div class="faint small">{t.devices.lastSeen(ago(node.last_seen))}</div>
								{:else if running.length}
									<span class="badge info">{t.devices.working}</span>
								{:else}
									<span class="badge ok">{t.devices.free}</span>
								{/if}
							</td>
							<td>
								{@render meter(
									ratio(tel.gpu_util, 100),
									tel.gpu_util !== null ? `${Math.round(tel.gpu_util)} %` : '—',
									tel.gpu_temp_c !== null ? t.devices.temp(tel.gpu_temp_c) : null
								)}
							</td>
							<td>
								{@render meter(
									ratio(tel.vram_used_mb, gpu?.vram_total_mb),
									t.devices.of(megabytes(tel.vram_used_mb), megabytes(gpu?.vram_total_mb)),
									null
								)}
							</td>
							<td>
								{@render meter(
									ratio(tel.cpu_util, 100),
									tel.cpu_util !== null ? `${Math.round(tel.cpu_util)} %` : '—',
									null
								)}
							</td>
							<td>
								{@render meter(
									ratio(tel.ram_used_mb, tel.ram_total_mb),
									t.devices.of(megabytes(tel.ram_used_mb), megabytes(tel.ram_total_mb)),
									null
								)}
							</td>
							<td class="current">
								{#each running as { job, task } (task.id)}
									<div class="truncate">{job.title}</div>
									<div class="muted small truncate">
										{t.jobs.kinds[task.kind]}{task.stage
											? ` · ${t.jobs.stages[task.stage] ?? task.stage}`
											: ''}{task.fraction !== null ? ` · ${Math.round(task.fraction * 100)} %` : ''}
									</div>
								{:else}
									{#if node.busy_playing}
										<span class="warn-text small">{t.devices.busyPlaying}</span>
									{:else}
										<span class="faint">—</span>
									{/if}
								{/each}
							</td>
							<td class="row-actions">
								<button class="btn subtle danger" onclick={() => revoke(node)}>
									{t.devices.revoke}
								</button>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{:else}
			<div class="empty"><p>{t.devices.emptyWorkers}</p></div>
		{/if}
	</section>

	<section class="panel">
		<header class="panel-header">
			<h2>{t.devices.screens}</h2>
			<span class="muted small">{screens.filter((p) => p.online).length} / {screens.length}</span>
			<div class="actions">
				<button class="btn" onclick={() => enrol('player')}>
					<Icon name="add" size={16} />
					{t.cmd.enrolPlayer}
				</button>
			</div>
		</header>
		{#if screens.length}
			<table class="table">
				<thead>
					<tr>
						<th>{t.devices.name}</th>
						<th>{t.devices.status}</th>
						<th>{t.devices.song}</th>
						<th>{t.devices.outputs}</th>
						<th><span class="sr-only">{t.common.more}</span></th>
					</tr>
				</thead>
				<tbody>
					{#each screens as p (p.id)}
						{@const on = onScreen(live.state, p)}
						{@const downloads = p.status.cache.filter((c) => c.state !== 'ready')}
						<tr class:off={!p.online}>
							<td><strong>{p.name}</strong></td>
							<td>
								<span class="badge {toneOf(p)}">
									{p.online ? t.player.states[p.status.state] : t.devices.disconnected}
								</span>
							</td>
							<td>
								{#if on.song}
									<div class="truncate">{on.song.title}</div>
									<div class="muted small truncate">{on.song.artist ?? ''}</div>
								{:else}
									<span class="faint">—</span>
								{/if}
								{#each downloads as c (c.content_id)}
									<div class="small muted">
										{t.playback.cache[c.state]} ·
										{live.state.contents.find((x) => x.id === c.content_id)?.title ?? c.content_id}
										{c.state === 'downloading' ? `${Math.round(c.fraction * 100)} %` : ''}
									</div>
								{/each}
							</td>
							<td>
								<div class="muted">
									{t.devices.displays(p.status.outputs.displays.length)} ·
									{t.devices.soundOutputs(p.status.outputs.audio.length)}
								</div>
								{#each p.status.errors ?? [] as error, i (i)}
									<div class="warn-text small">
										{t.playerErrors[error.code] ?? error.code}{error.device
											? ` · ${error.device}`
											: ''}
									</div>
								{/each}
							</td>
							<td class="row-actions">
								<button class="btn subtle danger" onclick={() => revoke(p)}>
									{t.devices.revoke}
								</button>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{:else}
			<div class="empty"><p>{t.devices.emptyScreens}</p></div>
		{/if}
	</section>
</div>

{#snippet meter(value: number | null, text: string, extra: string | null)}
	<div class="meter">
		<span class="mono small">{text}{extra ? ` · ${extra}` : ''}</span>
		<div class="progress" class:high={value !== null && value > 0.85}>
			<span style:width="{(value ?? 0) * 100}%"></span>
		</div>
	</div>
{/snippet}

<style>
	.enrol {
		display: grid;
		gap: 10px;
	}
	.code-row {
		display: flex;
		gap: 8px;
		align-items: stretch;
	}
	.code {
		flex: 1;
		min-width: 0;
		padding: 8px 12px;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: var(--bg);
		font: 12.5px/1.5 var(--mono);
		overflow-wrap: anywhere;
	}
	.name {
		display: flex;
		flex-direction: column;
	}
	tr.off td {
		color: var(--faint);
	}
	tr.off .meter {
		visibility: hidden;
	}
	.meter {
		display: grid;
		gap: 4px;
		min-width: 96px;
	}
	.progress.high > span {
		background: var(--warn);
	}
	.current {
		max-width: 260px;
	}
	.warn-text {
		color: var(--warn);
	}
	.row-actions {
		width: 1%;
	}
	@media (max-width: 1100px) {
		.workers th:nth-child(4),
		.workers td:nth-child(4),
		.workers th:nth-child(6),
		.workers td:nth-child(6) {
			display: none;
		}
	}
</style>
