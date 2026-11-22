<script lang="ts">
	/**
	 * Devices: the computers that make the karaokes and the screens that show them, each one a
	 * row. Processing computers show their GPU, its memory, CPU, memory and temperature (every
	 * heartbeat) and what they are making; new ones are added from here, with the exact command
	 * to paste. Screens are any browser on the LAN that opens /pantalla (decision 011): each shows
	 * its state, how well it keeps time and what it downloads, and here it is named and told
	 * what to show.
	 */
	import { onMount } from 'svelte';
	import { commands } from '#lib/commands/registry.svelte.js';
	import Icon from '#lib/console/Icon.svelte';
	import { screenName, screenTone } from '#lib/console/stage.js';
	import type { ScreenConfig } from '#lib/contracts';
	import { api } from '#lib/control/api.js';
	import { live } from '#lib/control/live.svelte.js';
	import { toasts } from '#lib/control/toasts.svelte.js';
	import type { NodeView, ScreenView } from '#lib/control/types.js';
	import { i18n } from '#lib/i18n';
	import { fail } from '#lib/shell/actions.svelte.js';
	import { ago, megabytes } from '#lib/shell/format.js';

	const t = $derived(i18n.t);
	const workers = $derived(live.state.nodes.filter((n) => n.kind === 'worker'));
	const screens = $derived(live.state.screens);
	const THEMES = ['clasico', 'moderno', 'contraste'];
	let token = $state<string | null>(null);

	function tasksOf(node: NodeView) {
		return node.running
			.map((id) => {
				const job = live.state.jobs.find((j) => j.tasks.some((x) => x.id === id));
				const task = job?.tasks.find((x) => x.id === id);
				return job && task ? { job, task } : null;
			})
			.filter((x) => x !== null);
	}

	async function enrol() {
		try {
			token = (await api.enrollment()).token;
		} catch (error) {
			fail(error);
		}
	}

	async function configure(screen: ScreenView, change: Partial<ScreenConfig>) {
		try {
			await api.setScreen(screen.id, { ...screen.config, ...change });
		} catch (error) {
			fail(error);
		}
	}

	async function forget(screen: ScreenView) {
		try {
			await api.forgetScreen(screen.id);
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

	const command = $derived(token ? `karaoke-worker enroll ${location.origin} ${token}` : '');
	const screenUrl = $derived(`${location.origin}/pantalla`);

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
				<p class="muted">{t.devices.howWorker}</p>
				<div class="code-row">
					<code class="code">{command}</code>
					<button
						class="btn"
						onclick={() =>
							navigator.clipboard.writeText(command).then(() => toasts.show(t.common.copied))}
					>
						{t.common.copy}
					</button>
				</div>
			</div>
		</section>
	{/if}

	<section class="panel">
		<header class="panel-header">
			<h2>{t.devices.workers}</h2>
			<span class="muted small">{workers.filter((w) => w.online).length} / {workers.length}</span>
			<div class="actions">
				<button class="btn" onclick={enrol}>
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
			<span class="muted small">{screens.filter((x) => x.online).length} / {screens.length}</span>
		</header>
		<div class="panel-body enrol">
			<p class="muted">{t.devices.howScreen}</p>
			<div class="code-row">
				<code class="code">{screenUrl}</code>
				<button
					class="btn"
					onclick={() =>
						navigator.clipboard.writeText(screenUrl).then(() => toasts.show(t.common.copied))}
				>
					{t.common.copy}
				</button>
			</div>
		</div>
		{#if screens.length}
			<table class="table">
				<thead>
					<tr>
						<th>{t.devices.name}</th>
						<th>{t.devices.status}</th>
						<th>{t.devices.sync}</th>
						<th>{t.outputs.shows}</th>
						<th>{t.outputs.theme}</th>
						<th>{t.outputs.calibration}</th>
						<th>{t.devices.maxHeight}</th>
						<th><span class="sr-only">{t.common.more}</span></th>
					</tr>
				</thead>
				<tbody>
					{#each screens as screen (screen.id)}
						{@const status = screen.status}
						{@const downloads = (status?.cache ?? []).filter((c) => c.state !== 'ready')}
						<tr class:off={!screen.online}>
							<td>
								<input
									class="field name"
									value={screen.config.name ?? ''}
									placeholder={screen.id}
									aria-label={t.devices.name}
									onchange={(e) => configure(screen, { name: e.currentTarget.value || null })}
								/>
								<div class="faint small mono truncate">
									{screen.hello ? `${screen.hello.width}×${screen.hello.height}` : ''}
									{screen.hello?.preview ? ` · ${t.devices.preview}` : ''}
								</div>
							</td>
							<td>
								<span class="badge {screenTone(screen)}">
									{screen.online && status ? t.screenStates[status.state] : t.devices.disconnected}
								</span>
								{#each status?.flags ?? [] as flag (flag)}
									{#if flag !== 'fullscreen'}
										<div class="warn-text small">{t.screenFlags[flag]}</div>
									{/if}
								{/each}
								{#if status?.error}<div class="warn-text small">{status.error}</div>{/if}
								{#each downloads as c (c.manifest)}
									<div class="small muted">
										{t.playback.cache[c.state]} ·
										{live.state.contents.find((x) => x.id === c.content_id)?.title ?? c.content_id}
										{c.state === 'downloading' ? `${Math.round(c.fraction * 100)} %` : ''}
									</div>
								{/each}
							</td>
							<td class="mono small muted">
								{#if status && status.sync.error_ms !== null}
									±{status.sync.error_ms.toFixed(1)} ms
								{/if}
								{#if status?.sync.rtt_ms}<div>RTT {status.sync.rtt_ms.toFixed(1)} ms</div>{/if}
							</td>
							<td>
								<select
									class="field"
									value={screen.config.layout}
									aria-label={`${t.outputs.shows}: ${screenName(screen)}`}
									onchange={(e) =>
										configure(screen, {
											layout: e.currentTarget.value as ScreenConfig['layout']
										})}
								>
									{#each Object.entries(t.outputs.layout) as [value, name] (value)}
										<option {value}>{name}</option>
									{/each}
								</select>
							</td>
							<td>
								<select
									class="field"
									value={screen.config.theme}
									aria-label={`${t.outputs.theme}: ${screenName(screen)}`}
									onchange={(e) => configure(screen, { theme: e.currentTarget.value })}
								>
									{#each THEMES as theme (theme)}<option value={theme}>{theme}</option>{/each}
								</select>
							</td>
							<td>
								<input
									class="field num"
									type="number"
									step="1"
									value={screen.config.display_ms}
									aria-label={`${t.outputs.calibration}: ${screenName(screen)}`}
									onchange={(e) =>
										configure(screen, { display_ms: Number(e.currentTarget.value) || 0 })}
								/>
							</td>
							<td>
								<select
									class="field"
									value={String(screen.config.video_max_height ?? '')}
									aria-label={`${t.devices.maxHeight}: ${screenName(screen)}`}
									onchange={(e) =>
										configure(screen, {
											video_max_height: e.currentTarget.value ? Number(e.currentTarget.value) : null
										})}
								>
									<option value="">—</option>
									<option value="720">720p</option>
									<option value="1080">1080p</option>
								</select>
							</td>
							<td class="row-actions">
								{#if !screen.online}
									<button class="btn subtle danger" onclick={() => forget(screen)}>
										{t.devices.forget}
									</button>
								{/if}
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
	.name {
		width: 11rem;
		height: 30px;
	}
	.num {
		width: 5rem;
		height: 30px;
		font: 12.5px var(--mono);
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
