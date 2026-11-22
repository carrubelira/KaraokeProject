<script lang="ts">
	/** Outputs of the player: screens and audio, the routing matrix, calibration and policies. */
	import type { PlayerConfig, Route, Screen } from '#lib/contracts';
	import { onMount } from 'svelte';
	import { commands } from '#lib/commands/registry.svelte.js';
	import { api } from '#lib/control/api.js';
	import { toasts } from '#lib/control/toasts.svelte.js';
	import { i18n } from '#lib/i18n';
	import { fail, player } from '#lib/shell/actions.svelte.js';
	import Kbd from '#lib/shell/Kbd.svelte';

	const t = $derived(i18n.t);
	const target = $derived(player());
	const audio = $derived(target?.status.outputs.audio ?? []);
	const displays = $derived(target?.status.outputs.displays ?? []);
	const TRACKS = ['instrumental', 'vocals'] as const;
	const THEMES = ['clasico', 'moderno', 'contraste'];

	let draft = $state<PlayerConfig | null>(null);
	$effect(() => {
		if (target && (!draft || draft === null))
			draft = structuredClone($state.snapshot(target.config));
	});

	const route = (track: string, output: string): Route | undefined =>
		draft?.routing.routes.find((r) => r.track === track && r.output === output);

	function toggleRoute(track: (typeof TRACKS)[number], output: string) {
		if (!draft) return;
		const routes = draft.routing.routes;
		draft.routing.routes = route(track, output)
			? routes.filter((r) => !(r.track === track && r.output === output))
			: [...routes, { track, output, gain_db: 0, delay_ms: 0 }];
	}

	function screen(display: string): Screen {
		return (
			draft?.routing.screens.find((s) => s.display === display) ?? {
				display,
				layout: 'video-lyrics',
				theme: 'clasico'
			}
		);
	}

	function setScreen(display: string, change: Partial<Screen>) {
		if (!draft) return;
		const next = { ...screen(display), ...change };
		draft.routing.screens = [...draft.routing.screens.filter((s) => s.display !== display), next];
	}

	async function save() {
		if (!target || !draft) return;
		try {
			await api.setConfig(target.id, $state.snapshot(draft));
			toasts.show(t.outputs.saved);
		} catch (error) {
			fail(error);
		}
	}

	onMount(() => {
		commands.scope = 'outputs';
		return commands.register({
			id: 'outputs.save',
			title: () => t.outputs.save,
			group: () => t.groups.outputs,
			scope: 'outputs',
			keys: ['Mod+s'],
			whileTyping: true,
			run: save
		});
	});
</script>

<div class="ctl-page">
	<header class="ctl-page-head">
		<h1>{t.outputs.title}</h1>
		<span class="ctl-sub">{target?.name ?? t.status.noPlayer}</span>
		<div class="ctl-actions">
			<button class="ctl-btn ctl-primary" onclick={save} disabled={!draft}
				>{t.outputs.save} <Kbd keys="Mod+s" /></button
			>
		</div>
	</header>
	{#if target && draft}
		<section class="ctl-panel">
			<div class="ctl-panel-head">
				<h2>{t.outputs.matrix}</h2>
				<span class="ctl-muted">{t.outputs.matrixHelp}</span>
			</div>
			<table class="ctl-table">
				<thead>
					<tr>
						<th>{t.outputs.audio}</th>
						<th>{t.outputs.master}</th>
						{#each TRACKS as track (track)}<th>{t.outputs[track]}</th>{/each}
						<th>{t.outputs.calibration}</th>
						<th>{t.outputs.policy}</th>
						<th class="ctl-num">{t.outputs.sync}</th>
					</tr>
				</thead>
				<tbody>
					{#each audio as device (device.id)}
						<tr>
							<td
								>{device.name}{#if device.bluetooth}<br /><span class="ctl-badge ctl-warn"
										>{t.outputs.bluetooth}</span
									>{/if}</td
							>
							<td
								><input
									type="radio"
									name="master"
									checked={draft.routing.master === device.id}
									onchange={() => draft && (draft.routing.master = device.id)}
									aria-label={t.outputs.master}
								/></td
							>
							{#each TRACKS as track (track)}
								{@const r = route(track, device.id)}
								<td class="cell">
									<input
										type="checkbox"
										checked={Boolean(r)}
										onchange={() => toggleRoute(track, device.id)}
										aria-label={`${t.outputs[track]} → ${device.name}`}
									/>
									{#if r}
										<input
											class="ctl-input ctl-num-input"
											type="number"
											step="0.5"
											bind:value={r.gain_db}
											aria-label={t.outputs.gain}
											title={t.outputs.gain}
										/>
										<input
											class="ctl-input ctl-num-input"
											type="number"
											step="1"
											min="0"
											bind:value={r.delay_ms}
											aria-label={t.outputs.delay}
											title={t.outputs.delay}
										/>
									{/if}
								</td>
							{/each}
							<td
								><input
									class="ctl-input ctl-num-input"
									type="number"
									step="1"
									value={draft.calibration.audio_ms[device.id] ?? 0}
									oninput={(e) =>
										draft &&
										(draft.calibration.audio_ms[device.id] = Number(e.currentTarget.value))}
									aria-label={t.outputs.calibration}
								/></td
							>
							<td>
								<select
									class="ctl-select"
									value={draft.routing.policies[device.id] ?? ''}
									onchange={(e) => {
										if (!draft) return;
										if (e.currentTarget.value)
											draft.routing.policies[device.id] = e.currentTarget.value as
												'pause' | 'continue';
										else delete draft.routing.policies[device.id];
									}}
									aria-label={t.outputs.policy}
								>
									<option value="">—</option>
									<option value="pause">{t.outputs.pause}</option>
									<option value="continue">{t.outputs.continue}</option>
								</select>
							</td>
							<td class="ctl-num ctl-muted">
								{#if target.status.sync[`${device.id}.correction_ppm`] !== undefined}{target.status.sync[
										`${device.id}.correction_ppm`
									].toFixed(1)} ppm{/if}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</section>
		<section class="ctl-panel">
			<div class="ctl-panel-head"><h2>{t.outputs.displays}</h2></div>
			<table class="ctl-table">
				<thead>
					<tr>
						<th>{t.outputs.display}</th>
						<th>{t.outputs.shows}</th>
						<th>{t.outputs.theme}</th>
						<th class="ctl-num">{t.outputs.calibration}</th>
					</tr>
				</thead>
				<tbody>
					{#each displays as display (display.id)}
						{@const s = screen(display.id)}
						<tr>
							<td
								>{display.name}
								<span class="ctl-muted"
									>{display.width}×{display.height} · {display.refresh_hz} Hz</span
								></td
							>
							<td>
								<select
									class="ctl-select"
									value={s.layout}
									onchange={(e) =>
										setScreen(display.id, { layout: e.currentTarget.value as Screen['layout'] })}
									aria-label={display.name}
								>
									{#each Object.entries(t.outputs.layout) as [value, name] (value)}<option {value}
											>{name}</option
										>{/each}
								</select>
							</td>
							<td>
								<select
									class="ctl-select"
									value={s.theme}
									onchange={(e) => setScreen(display.id, { theme: e.currentTarget.value })}
									aria-label={t.outputs.theme}
								>
									{#each THEMES as theme (theme)}<option value={theme}>{theme}</option>{/each}
								</select>
							</td>
							<td
								><input
									class="ctl-input ctl-num-input"
									type="number"
									step="1"
									value={draft.calibration.display_ms[display.id] ?? 0}
									oninput={(e) =>
										draft &&
										(draft.calibration.display_ms[display.id] = Number(e.currentTarget.value))}
									aria-label={t.outputs.calibration}
								/></td
							>
						</tr>
					{/each}
				</tbody>
			</table>
		</section>
	{:else}
		<section class="ctl-panel"><p class="ctl-empty">{t.outputs.noPlayer}</p></section>
	{/if}
</div>

<style>
	section {
		overflow-x: auto;
	}
	.cell {
		white-space: nowrap;
	}
	.cell input + input {
		margin-left: var(--sp-1);
	}
</style>
