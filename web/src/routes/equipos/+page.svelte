<script lang="ts">
	/** Machines: the ones that process songs (GPU, memory, task) and the players, and enrolling. */
	import { onMount } from 'svelte';
	import { commands } from '#lib/commands/registry.svelte.js';
	import { api } from '#lib/control/api.js';
	import { live } from '#lib/control/live.svelte.js';
	import type { NodeView } from '#lib/control/types.js';
	import { toasts } from '#lib/control/toasts.svelte.js';
	import { i18n } from '#lib/i18n';
	import { fail } from '#lib/shell/actions.svelte.js';
	import Dialog from '#lib/shell/Dialog.svelte';
	import { megabytes } from '#lib/shell/format.js';
	import Kbd from '#lib/shell/Kbd.svelte';

	const t = $derived(i18n.t);
	const workers = $derived(live.state.nodes.filter((n) => n.kind === 'worker'));
	const players = $derived(live.state.nodes.filter((n) => n.kind === 'player'));
	let adding = $state(false);
	let kind = $state<'worker' | 'player'>('worker');
	let token = $state<string | null>(null);
	const command = $derived(
		token
			? `${kind === 'worker' ? 'karaoke-worker' : 'kp-player'} enroll ${location.origin} ${token}`
			: ''
	);

	async function enrol(which: 'worker' | 'player') {
		kind = which;
		adding = true;
		token = null;
		try {
			token = (await api.enrollment(which)).token;
		} catch (error) {
			fail(error);
		}
	}

	function copy(text: string) {
		void navigator.clipboard?.writeText(text).then(() => toasts.show(t.common.copied));
	}

	function revoke(node: NodeView) {
		api
			.revoke(node.id)
			.then(() => live.refreshNodes())
			.catch(fail);
	}

	const task = (node: NodeView) => {
		const id = node.running[0];
		if (!id) return '';
		const job = live.state.jobs.find((j) => j.tasks.some((k) => k.id === id));
		return job?.title ?? t.machines.busy;
	};

	onMount(() => {
		commands.scope = 'workers';
		const group = () => t.groups.machines;
		return commands.register(
			{
				id: 'workers.enrolWorker',
				title: () => t.cmd.enrolWorker,
				group,
				scope: 'workers',
				keys: ['w'],
				run: () => enrol('worker')
			},
			{
				id: 'workers.enrolPlayer',
				title: () => t.cmd.enrolPlayer,
				group,
				scope: 'workers',
				keys: ['Shift+w'],
				run: () => enrol('player')
			}
		);
	});
</script>

{#snippet state(node: NodeView)}
	<span class="ctl-badge {node.online ? 'ctl-ok' : 'ctl-bad'}"
		>{node.online ? t.machines.connected : t.machines.disconnected}</span
	>
{/snippet}

<div class="ctl-page">
	<header class="ctl-page-head">
		<h1>{t.machines.title}</h1>
		<span class="ctl-sub"
			>{t.machines.summary(
				live.state.nodes.filter((n) => n.online).length,
				live.state.nodes.length
			)}</span
		>
		<div class="ctl-actions">
			<button class="ctl-btn ctl-primary" onclick={() => enrol('worker')}
				>{t.machines.add} <Kbd keys="w" /></button
			>
		</div>
	</header>

	<section class="ctl-panel">
		<div class="ctl-panel-head">
			<h2>{t.machines.workers}</h2>
			<span class="ctl-muted">{t.machines.workersHelp}</span>
		</div>
		{#if workers.length === 0}
			<p class="ctl-empty">{t.machines.noWorkers}</p>
		{:else}
			<table class="ctl-table">
				<thead>
					<tr>
						<th>{t.machines.columns.name}</th>
						<th>{t.machines.columns.state}</th>
						<th>{t.machines.columns.gpu}</th>
						<th class="ctl-num">{t.machines.columns.vram}</th>
						<th class="ctl-num">{t.machines.columns.use}</th>
						<th class="ctl-num">{t.machines.columns.temp}</th>
						<th>{t.machines.columns.task}</th>
						<th></th>
					</tr>
				</thead>
				<tbody>
					{#each workers as node (node.id)}
						{@const gpu = node.capabilities.gpus[0]}
						<tr>
							<td class="ctl-title"
								>{node.name}<span class="ctl-muted ctl-after"> · {node.capabilities.os}</span></td
							>
							<td>{@render state(node)}</td>
							<td>{gpu?.name ?? t.machines.noGpu}</td>
							<td class="ctl-num"
								>{gpu
									? `${megabytes(node.telemetry.vram_used_mb)} / ${megabytes(gpu.vram_total_mb)}`
									: ''}</td
							>
							<td class="ctl-num"
								>{node.telemetry.gpu_util !== null
									? `${Math.round(node.telemetry.gpu_util)} %`
									: ''}</td
							>
							<td class="ctl-num"
								>{node.telemetry.gpu_temp_c !== null
									? `${Math.round(node.telemetry.gpu_temp_c)} °C`
									: ''}</td
							>
							<td class="ctl-title">
								{#if node.busy_playing}<span class="ctl-badge ctl-warn"
										>{t.machines.busyPlaying}</span
									>{:else}{task(node)}{/if}
							</td>
							<td class="ctl-shrink"
								><button class="ctl-btn ctl-quiet ctl-danger" onclick={() => revoke(node)}
									>{t.machines.revoke}</button
								></td
							>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</section>

	<section class="ctl-panel">
		<div class="ctl-panel-head">
			<h2>{t.machines.players}</h2>
			<span class="ctl-muted">{t.machines.playersHelp}</span>
			<div class="ctl-actions">
				<button class="ctl-btn" onclick={() => enrol('player')}
					>{t.machines.addPlayer} <Kbd keys="Shift+w" /></button
				>
			</div>
		</div>
		{#if players.length === 0}
			<p class="ctl-empty">{t.machines.noPlayers}</p>
		{:else}
			<table class="ctl-table">
				<thead>
					<tr>
						<th>{t.machines.columns.name}</th>
						<th>{t.machines.columns.state}</th>
						<th>{t.machines.columns.system}</th>
						<th class="ctl-num">{t.machines.columns.displays}</th>
						<th class="ctl-num">{t.machines.columns.audio}</th>
						<th></th>
					</tr>
				</thead>
				<tbody>
					{#each players as node (node.id)}
						{@const view = live.state.players.find((p) => p.id === node.id)}
						<tr>
							<td class="ctl-title">{node.name}</td>
							<td>{@render state(node)}</td>
							<td>{node.capabilities.os}</td>
							<td class="ctl-num">{view?.status.outputs.displays.length ?? '—'}</td>
							<td class="ctl-num">{view?.status.outputs.audio.length ?? '—'}</td>
							<td class="ctl-shrink"
								><button class="ctl-btn ctl-quiet ctl-danger" onclick={() => revoke(node)}
									>{t.machines.revoke}</button
								></td
							>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</section>
</div>

{#if adding}
	<Dialog
		title={kind === 'worker' ? t.machines.add : t.machines.addPlayer}
		onclose={() => (adding = false)}
	>
		<div class="ctl-form">
			<div class="ctl-seg" role="group" aria-label={t.machines.kind}>
				<button aria-pressed={kind === 'worker'} onclick={() => enrol('worker')}
					>{t.machines.kindWorker}</button
				>
				<button aria-pressed={kind === 'player'} onclick={() => enrol('player')}
					>{t.machines.kindPlayer}</button
				>
			</div>
			<p class="ctl-muted">{t.machines.steps(kind === 'worker')}</p>
			{#if token}
				<div class="ctl-field">
					<span>{t.machines.command}</span>
					<div class="copy">
						<code>{command}</code>
						<button class="ctl-btn" onclick={() => copy(command)}>{t.common.copy}</button>
					</div>
				</div>
				<div class="ctl-field">
					<span>{t.machines.token}</span>
					<div class="copy">
						<code>{token}</code>
						<button class="ctl-btn" onclick={() => copy(token ?? '')}>{t.common.copy}</button>
					</div>
					<span class="ctl-help">{t.machines.tokenHelp}</span>
				</div>
			{:else}
				<p class="ctl-muted">{t.common.loading}</p>
			{/if}
		</div>
	</Dialog>
{/if}

<style>
	.copy {
		display: flex;
		gap: var(--sp-2);
		align-items: start;
	}
	code {
		flex: 1;
		padding: var(--sp-2) var(--sp-3);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: var(--bg);
		font: var(--fs-s) / 1.5 var(--font-mono);
		word-break: break-all;
	}
</style>
