<script lang="ts">
	/**
	 * The stage's sound (decision 011): the sound cards and DACs on the backend, which part goes
	 * to each (the music and the guide vocals) with its gain and delay, which output keeps time,
	 * how late each one really is and what happens if one goes away. Changes are a draft until
	 * saved (Mod+S). Rows are keyed by position too: two devices with one id must never take the
	 * page down. What each screen shows is set in Devices.
	 */
	import type { AudioConfig, Route } from '#lib/contracts';
	import { resolve } from '$app/paths';
	import { onMount } from 'svelte';
	import { commands } from '#lib/commands/registry.svelte.js';
	import { api } from '#lib/control/api.js';
	import { live } from '#lib/control/live.svelte.js';
	import { toasts } from '#lib/control/toasts.svelte.js';
	import { i18n } from '#lib/i18n';
	import { fail } from '#lib/shell/actions.svelte.js';
	import Kbd from '#lib/shell/Kbd.svelte';

	const t = $derived(i18n.t);
	const engine = $derived(live.state.audio);
	const audio = $derived(engine.status.devices);
	const TRACKS = ['instrumental', 'vocals'] as const;

	/** The configuration as kp-audio applies it: with no routes, both stems go to the master
	 * (or the default output), so that is what the matrix shows and edits. */
	function effective(config: AudioConfig, devices: typeof audio): AudioConfig {
		const copy = structuredClone(config);
		if (copy.routing.routes.length > 0 || devices.length === 0) return copy;
		const master =
			devices.find((d) => d.id === copy.routing.master) ??
			devices.find((d) => d.default) ??
			devices[0];
		copy.routing.routes = TRACKS.map((track) => ({
			track,
			output: master.id,
			gain_db: 0,
			delay_ms: 0
		}));
		return copy;
	}

	let draft = $state<AudioConfig | null>(null);
	let saved = $state('');
	$effect(() => {
		// The first configuration the server sends; later ones only when nothing is being edited.
		const config = effective($state.snapshot(engine.config), $state.snapshot(audio));
		const json = JSON.stringify(config);
		if (draft === null || (json !== saved && JSON.stringify(draft) === saved)) {
			draft = config;
			saved = json;
		}
	});
	const dirty = $derived(draft !== null && JSON.stringify(draft) !== saved);
	const errorOf = (id: string) => engine.status.errors.find((e) => e.device === id);

	const route = (track: string, output: string): Route | undefined =>
		draft?.routing.routes.find((r) => r.track === track && r.output === output);

	function toggleRoute(track: (typeof TRACKS)[number], output: string) {
		if (!draft) return;
		const routes = draft.routing.routes;
		draft.routing.routes = route(track, output)
			? routes.filter((r) => !(r.track === track && r.output === output))
			: [...routes, { track, output, gain_db: 0, delay_ms: 0 }];
	}

	async function save() {
		if (!draft) return;
		try {
			await api.setAudio($state.snapshot(draft));
			saved = JSON.stringify(draft);
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

<div class="page">
	<header class="page-header">
		<div>
			<h1>{t.outputs.title}</h1>
			<p class="description">{t.outputs.description}</p>
		</div>
		<div class="actions">
			{#if dirty}<span class="badge warn">{t.outputs.unsaved}</span>{/if}
			<button class="btn primary" onclick={save} disabled={!dirty}>
				{t.outputs.save}
				<Kbd keys="Mod+s" />
			</button>
		</div>
	</header>
	{#if !engine.online}
		<p class="notice warn" role="status">{engine.fault ?? t.outputs.engineOffline}</p>
	{/if}
	{#if draft}
		<section class="panel">
			<header class="panel-header"><h2>{t.outputs.audio}</h2></header>
			<div class="scroll">
				<table class="table matrix">
					<thead>
						<tr>
							<th>{t.devices.name}</th>
							<th class="center">{t.outputs.master}</th>
							{#each TRACKS as track (track)}<th>{t.outputs[track]}</th>{/each}
							<th>{t.outputs.calibration}</th>
							<th>{t.outputs.policy}</th>
						</tr>
					</thead>
					<tbody>
						{#each audio as device, i (`${i}:${device.id}`)}
							{@const problem = errorOf(device.id)}
							<tr>
								<td>
									<div class="device">
										<strong>{device.name}</strong>
										<span class="mono faint small"
											>{device.channels} ch · {device.sample_rate / 1000} kHz{#if engine.status.sync[`${device.id}.correction_ppm`] !== undefined}
												· {engine.status.sync[`${device.id}.correction_ppm`].toFixed(1)} ppm{/if}</span
										>
										{#if device.bluetooth}<span class="warn-text small">{t.outputs.bluetooth}</span
											>{/if}
										{#if problem}<span class="badge warn">{t.audioErrors[problem.code]}</span>{/if}
									</div>
								</td>
								<td class="center">
									<input
										type="radio"
										name="master"
										checked={draft.routing.master === device.id}
										onchange={() => draft && (draft.routing.master = device.id)}
										aria-label={`${t.outputs.master}: ${device.name}`}
									/>
								</td>
								{#each TRACKS as track (track)}
									{@const r = route(track, device.id)}
									<td>
										<div class="patch">
											<input
												type="checkbox"
												class="route"
												checked={!!r}
												onchange={() => toggleRoute(track, device.id)}
												aria-label={`${t.outputs[track]}: ${device.name}`}
											/>
											{#if r}
												<input
													class="field num"
													type="number"
													step="0.5"
													bind:value={r.gain_db}
													aria-label={t.outputs.gain}
													title={t.outputs.gain}
												/>
												<input
													class="field num"
													type="number"
													step="1"
													min="0"
													bind:value={r.delay_ms}
													aria-label={t.outputs.delay}
													title={t.outputs.delay}
												/>
											{/if}
										</div>
									</td>
								{/each}
								<td>
									<input
										class="field num"
										type="number"
										step="1"
										value={draft.calibration_ms[device.id] ?? 0}
										oninput={(e) =>
											draft && (draft.calibration_ms[device.id] = Number(e.currentTarget.value))}
										aria-label={t.outputs.calibration}
									/>
								</td>
								<td>
									<select
										class="field policy"
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
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
			<p class="panel-footer faint small legend">{t.outputs.gain} · {t.outputs.delay}</p>
		</section>

		<p class="faint small">
			{t.outputs.screensElsewhere} <a href={resolve('/equipos')}>{t.nav.devices}</a>
		</p>
	{/if}
</div>

<style>
	.scroll {
		overflow-x: auto;
	}
	.device {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 2px;
		min-width: 240px;
	}
	.warn-text {
		color: var(--warn);
	}
	.center {
		text-align: center;
	}
	.center input,
	.route {
		width: 16px;
		height: 16px;
		accent-color: var(--accent);
	}
	.patch {
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.num {
		width: 5.5rem;
		height: 30px;
		font: 12.5px var(--mono);
	}
	.policy {
		width: 8rem;
		height: 30px;
	}
	.legend {
		justify-content: flex-start;
	}
</style>
