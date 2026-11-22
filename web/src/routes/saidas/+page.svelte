<script lang="ts">
	/**
	 * Outputs of the chosen screen: which sound output each stem goes to (a matrix, like a patch
	 * bay), which output keeps time, what happens if one goes away, and what each display shows.
	 * Changes are a draft until saved (Mod+S). Rows are keyed by position too: a player that
	 * reports two devices with one id must never take the page down.
	 */
	import type { PlayerConfig, Route, Screen } from '#lib/contracts';
	import { onMount } from 'svelte';
	import { commands } from '#lib/commands/registry.svelte.js';
	import Icon from '#lib/console/Icon.svelte';
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

<div class="c-page">
	<div class="c-page-head">
		<h1>{t.outputs.title}</h1>
		<span class="c-tag">{target?.name ?? '—'}</span>
		<span class="spacer"></span>
		{#if dirty}<span class="c-tally warn">{t.outputs.unsaved}</span>{/if}
		<button class="c-btn primary" onclick={save} disabled={!dirty}
			>{t.outputs.save} <Kbd keys="Mod+s" /></button
		>
	</div>
	{#if target && draft}
		<section class="c-panel">
			<header class="c-panel-head">
				<Icon name="outputs" size={16} />
				<h2>{t.outputs.matrix}</h2>
			</header>
			<div class="scroll">
				<table class="matrix">
					<thead>
						<tr>
							<th class="label">{t.outputs.audio}</th>
							<th class="label">{t.outputs.master}</th>
							{#each TRACKS as track (track)}<th class="label">{t.outputs[track]}</th>{/each}
							<th class="label">{t.outputs.calibration}</th>
							<th class="label">{t.outputs.policy}</th>
						</tr>
					</thead>
					<tbody>
						{#each audio as device, i (`${i}:${device.id}`)}
							{@const problem = errorOf(device.id)}
							<tr class:bad={!!problem}>
								<td class="device">
									<span class="c-tally {problem ? 'warn' : device.default ? 'cue' : ''}"></span>
									<span>
										<strong>{device.name}</strong>
										<span class="mono faint small"
											>{device.channels} ch · {device.sample_rate / 1000} kHz{#if target.status.sync[`${device.id}.correction_ppm`] !== undefined}
												· {target.status.sync[`${device.id}.correction_ppm`].toFixed(1)} ppm{/if}</span
										>
										{#if device.bluetooth}<span class="c-tag warn">{t.outputs.bluetooth}</span>{/if}
										{#if problem}<span class="c-tag warn">{t.playerErrors[problem.code]}</span>{/if}
									</span>
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
										<div class="patch" class:on={!!r}>
											<button
												class="jack"
												aria-pressed={!!r}
												onclick={() => toggleRoute(track, device.id)}
												aria-label={`${t.outputs[track]} → ${device.name}`}
											></button>
											{#if r}
												<input
													class="c-field num"
													type="number"
													step="0.5"
													bind:value={r.gain_db}
													aria-label={t.outputs.gain}
													title={t.outputs.gain}
												/>
												<input
													class="c-field num"
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
										class="c-field num"
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
										class="c-field"
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
		</section>

		<section class="c-panel">
			<header class="c-panel-head">
				<Icon name="screen" size={16} />
				<h2>{t.outputs.displays}</h2>
			</header>
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
						<strong>{display.name}</strong>
						{#if !display.connected}<span class="c-tag warn">{t.outputs.disconnected}</span>{/if}
						<label class="c-labelled">
							<span class="label">{t.outputs.shows}</span>
							<select
								class="c-field"
								value={s.layout}
								onchange={(e) =>
									setScreen(display.id, { layout: e.currentTarget.value as Screen['layout'] })}
								aria-label={display.name}
							>
								{#each Object.entries(t.outputs.layout) as [value, name] (value)}<option {value}
										>{name}</option
									>{/each}
							</select>
						</label>
						<label class="c-labelled">
							<span class="label">{t.outputs.theme}</span>
							<select
								class="c-field"
								value={s.theme}
								onchange={(e) => setScreen(display.id, { theme: e.currentTarget.value })}
								aria-label={t.outputs.theme}
							>
								{#each THEMES as theme (theme)}<option value={theme}>{theme}</option>{/each}
							</select>
						</label>
						<label class="c-labelled">
							<span class="label">{t.outputs.calibration}</span>
							<input
								class="c-field"
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
		<section class="c-panel"><p class="c-empty">{t.outputs.noPlayer}</p></section>
	{/if}
</div>

<style>
	.scroll {
		overflow-x: auto;
	}
	.matrix {
		width: 100%;
		border-collapse: collapse;
	}
	th {
		padding: 10px 12px;
		text-align: left;
		border-bottom: 1px solid var(--line);
		white-space: nowrap;
	}
	td {
		padding: 10px 12px;
		border-bottom: 1px solid var(--line);
		vertical-align: middle;
	}
	tr.bad {
		background: rgb(255 176 32 / 0.04);
	}
	.device {
		display: flex;
		gap: 10px;
		align-items: flex-start;
		min-width: 260px;
	}
	.device > span:last-child {
		display: grid;
		gap: 4px;
	}
	.small {
		font-size: 11.5px;
	}
	.center {
		text-align: center;
	}
	.center input {
		accent-color: var(--onair);
		width: 16px;
		height: 16px;
	}
	.patch {
		display: flex;
		align-items: center;
		gap: 6px;
	}
	.jack {
		width: 22px;
		height: 22px;
		border-radius: 50%;
		border: 2px solid var(--line-strong);
		background: radial-gradient(circle, #000 35%, var(--raise) 40%);
		cursor: pointer;
	}
	.patch.on .jack {
		border-color: var(--cue);
		background: radial-gradient(circle, var(--cue) 35%, #0b2018 40%);
		box-shadow: 0 0 10px var(--cue-glow);
	}
	.num {
		width: 5.5rem;
		min-height: 30px;
		padding: 4px 8px;
		font: 12px var(--font-mono);
	}
	.displays {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
		gap: 14px;
		padding: 14px;
	}
	.display {
		display: grid;
		gap: 10px;
		align-content: start;
	}
	.display.off .glass {
		opacity: 0.3;
	}
	.glass {
		display: grid;
		place-content: center;
		gap: 4px;
		text-align: center;
		max-height: 140px;
		background: linear-gradient(160deg, #0c1219, #020304);
		border: 1px solid var(--line-strong);
		font-size: 12px;
	}
</style>
