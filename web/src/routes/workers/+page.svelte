<script lang="ts">
	/** Workers and players: online state, GPU, VRAM, temperature, tasks, capabilities. */
	import { onMount } from 'svelte';
	import { commands } from '#lib/commands/registry.svelte.js';
	import { api } from '#lib/control/api.js';
	import { live } from '#lib/control/live.svelte.js';
	import { i18n } from '#lib/i18n';
	import { fail } from '#lib/shell/actions.svelte.js';
	import { megabytes } from '#lib/shell/format.js';
	import Kbd from '#lib/shell/Kbd.svelte';

	const t = $derived(i18n.t);
	const workers = $derived(live.state.nodes.filter((n) => n.kind === 'worker'));
	const players = $derived(live.state.nodes.filter((n) => n.kind === 'player'));
	let token = $state<{ token: string; kind: string } | null>(null);

	async function enrol(kind: 'worker' | 'player') {
		try {
			token = await api.enrollment(kind);
		} catch (error) {
			fail(error);
		}
	}

	onMount(() => {
		commands.scope = 'workers';
		const group = () => t.groups.workers;
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

<div class="ctl-page">
	<div class="ctl-page-head">
		<h1>{t.workers.title}</h1>
		<button class="ctl-btn" onclick={() => enrol('worker')}
			>{t.cmd.enrolWorker} <Kbd keys="w" /></button
		>
		<button class="ctl-btn" onclick={() => enrol('player')}
			>{t.cmd.enrolPlayer} <Kbd keys="Shift+w" /></button
		>
	</div>
	{#if token}
		<div class="ctl-box token">
			<h2>{t.workers.token}</h2>
			<code>{token.token}</code>
			<button class="ctl-btn" onclick={() => navigator.clipboard?.writeText(token?.token ?? '')}
				>{t.common.copy}</button
			>
			<p class="ctl-muted">{t.workers.tokenHelp(token.kind)}</p>
		</div>
	{/if}
	{#if workers.length === 0}<p class="ctl-muted">{t.workers.empty}</p>{/if}
	<div class="ctl-grid-2">
		{#each workers as node (node.id)}
			{@const gpu = node.capabilities.gpus[0]}
			<article class="ctl-box">
				<h2>
					{node.name}
					<span class="ctl-pill {node.online ? 'ctl-ok' : 'ctl-bad'}"
						>{node.online ? t.workers.online : t.workers.offline}</span
					>
				</h2>
				<p class="ctl-muted">
					{node.capabilities.os} · {node.capabilities.cpus} CPU · {node.capabilities.tasks.join(
						', '
					)}
				</p>
				{#if gpu}
					<p>{gpu.name}</p>
					<div
						class="ctl-bar"
						role="meter"
						aria-label="VRAM"
						aria-valuemin={0}
						aria-valuemax={gpu.vram_total_mb}
						aria-valuenow={node.telemetry.vram_used_mb ?? 0}
					>
						<span
							style:width={`${Math.round(((node.telemetry.vram_used_mb ?? 0) / gpu.vram_total_mb) * 100)}%`}
						></span>
					</div>
					<p class="ctl-muted">
						VRAM {t.workers.vram(
							megabytes(node.telemetry.vram_used_mb),
							megabytes(gpu.vram_total_mb)
						)}
						{#if node.telemetry.gpu_util !== null}
							· GPU {Math.round(node.telemetry.gpu_util)} %{/if}
						{#if node.telemetry.gpu_temp_c !== null}
							· {t.workers.temp(Math.round(node.telemetry.gpu_temp_c))}{/if}
					</p>
				{/if}
				<p>
					{t.workers.running(node.running.length)}{#if node.busy_playing}
						· <span class="ctl-pill ctl-warn">{t.workers.busyPlaying}</span>{/if}
				</p>
				<button
					class="ctl-btn"
					onclick={() =>
						api
							.revoke(node.id)
							.then(() => live.refreshNodes())
							.catch(fail)}>{t.workers.revoke}</button
				>
			</article>
		{/each}
	</div>
	<h2 class="section">{t.workers.players}</h2>
	<div class="ctl-grid-2">
		{#each players as node (node.id)}
			<article class="ctl-box">
				<h2>
					{node.name}
					<span class="ctl-pill {node.online ? 'ctl-ok' : 'ctl-bad'}"
						>{node.online ? t.workers.online : t.workers.offline}</span
					>
				</h2>
				<p class="ctl-muted">{node.capabilities.os} · {node.capabilities.decoders.join(', ')}</p>
				<button
					class="ctl-btn"
					onclick={() =>
						api
							.revoke(node.id)
							.then(() => live.refreshNodes())
							.catch(fail)}>{t.workers.revoke}</button
				>
			</article>
		{/each}
	</div>
</div>

<style>
	.token code {
		display: block;
		padding: var(--s-2);
		font-family: var(--font-data);
		word-break: break-all;
	}
	.section {
		margin-top: var(--s-6);
	}
	article p {
		margin: var(--s-1) 0;
	}
</style>
