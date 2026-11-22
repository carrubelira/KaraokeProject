<script lang="ts">
	/**
	 * Outputs of the chosen screen: which sound output each part goes to (the music and the guide
	 * vocals), which output keeps time, what happens if one goes away, and what each display shows.
	 * Changes are a draft until saved (Mod+S). Rows are keyed by position too: a player that
	 * reports two devices with one id must never take the page down.
	 */
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
	let draftOf = $state<string | null>(null);
	let saved = $state('');
	$effect(() => {
		if (target && draftOf !== target.id) {
			draft = structuredClone($state.snapshot(target.config));
			saved = JSON.stringify(draft);
			draftOf = target.id;
		}
	});
	const dirty = $derived(draft !== null && JSON.stringify(draft) !== saved);
	const errorOf = (id: string) => (target?.status.errors ?? []).find((e) => e.device === id);

	const route = (track: string, output: string): Route | undefined =>
		draft?.routing.routes.find((r) => r.track === track && r.output === output);

	function toggleRoute(track: (typeof TRACKS)[number], output: string) {
		if (!draft) return;
		const routes = draft.routing.routes;
		draft.routing.routes = route(track, output)
			? routes.filter((r) => !(r.track === track && r.output === output))
			: [...routes, { track, output, gain_db: 0, delay_ms: 0 }];
	}

	/** A display's setting; one not listed is off as soon as any display is listed (as the
	 * player reads it), and shows everything while none is. */
	function screen(display: string): Screen {
		const listed = draft?.routing.screens ?? [];
		return (
			listed.find((s) => s.display === display) ?? {
				display,
				layout: listed.length ? 'off' : 'video-lyrics',
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
			<h1>{t.outputs.title}{target ? ` · ${target.name}` : ''}</h1>
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
	{#if target && draft}
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
											>{device.channels} ch · {device.sample_rate / 1000} kHz{#if target.status.sync[`${device.id}.correction_ppm`] !== undefined}
												· {target.status.sync[`${device.id}.correction_ppm`].toFixed(1)} ppm{/if}</span
										>
										{#if device.bluetooth}<span class="warn-text small">{t.outputs.bluetooth}</span
											>{/if}
										{#if problem}<span class="badge warn">{t.playerErrors[problem.code]}</span>{/if}
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
										value={draft.calibration.audio_ms[device.id] ?? 0}
										oninput={(e) =>
											draft &&
											(draft.calibration.audio_ms[device.id] = Number(e.currentTarget.value))}
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

		<section class="panel">
			<header class="panel-header"><h2>{t.outputs.displays}</h2></header>
			<div class="displays">
				{#each displays as display, i (`${i}:${display.id}`)}
					{@const s = screen(display.id)}
					<article class="display" class:off={s.layout === 'off'}>
						<div class="glass" style:aspect-ratio={`${display.width} / ${display.height}`}>
							<span class="mono">{display.width}×{display.height}</span>
							<span class="mono faint"
								>{display.refresh_hz} Hz{display.primary ? ` · ${t.outputs.primary}` : ''}</span
							>
						</div>
						<div class="display-name">
							<strong>{display.name}</strong>
							{#if !display.connected}<span class="badge warn">{t.outputs.disconnected}</span>{/if}
						</div>
						<label class="form-row">
							<span>{t.outputs.shows}</span>
							<select
								class="field"
								value={s.layout}
								onchange={(e) =>
									setScreen(display.id, { layout: e.currentTarget.value as Screen['layout'] })}
							>
								{#each Object.entries(t.outputs.layout) as [value, name] (value)}<option {value}
										>{name}</option
									>{/each}
							</select>
						</label>
						<label class="form-row">
							<span>{t.outputs.theme}</span>
							<select
								class="field"
								value={s.theme}
								onchange={(e) => setScreen(display.id, { theme: e.currentTarget.value })}
							>
								{#each THEMES as theme (theme)}<option value={theme}>{theme}</option>{/each}
							</select>
						</label>
						<label class="form-row">
							<span>{t.outputs.calibration}</span>
							<input
								class="field"
								type="number"
								step="1"
								value={draft.calibration.display_ms[display.id] ?? 0}
								oninput={(e) =>
									draft &&
									(draft.calibration.display_ms[display.id] = Number(e.currentTarget.value))}
							/>
						</label>
					</article>
				{/each}
			</div>
		</section>
	{:else}
		<section class="panel"><div class="empty"><p>{t.outputs.noPlayer}</p></div></section>
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
	.displays {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
		gap: 20px;
		padding: 16px;
	}
	.display {
		display: grid;
		gap: 10px;
		align-content: start;
	}
	.display.off .glass {
		opacity: 0.35;
	}
	.display-name {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.glass {
		display: grid;
		place-content: center;
		gap: 2px;
		max-height: 130px;
		border: 1px solid var(--border-strong);
		border-radius: var(--radius);
		background: var(--bg);
		font-size: 12px;
		text-align: center;
	}
</style>
