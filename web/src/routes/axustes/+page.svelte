<script lang="ts">
	/**
	 * Settings: language, the server, song identification, and
	 * every shortcut, rebindable by pressing the new one.
	 */
	import { SvelteMap, SvelteSet } from 'svelte/reactivity';
	import { onMount } from 'svelte';
	import { eventChord } from '#lib/commands/keys.js';
	import { commands } from '#lib/commands/registry.svelte.js';
	import { api } from '#lib/control/api.js';
	import { i18n, LOCALE_NAMES, LOCALES, setLocale } from '#lib/i18n';
	import Kbd from '#lib/shell/Kbd.svelte';
	import { prefs } from '#lib/shell/prefs.svelte.js';

	const t = $derived(i18n.t);
	let capturing = $state<string | null>(null);
	let first = $state<string | null>(null);
	let server = $state<{ version: string } | null>(null);
	const conflicts = $derived(new SvelteSet([...commands.conflicts().values()].flat()));
	const groups = $derived.by(() => {
		const map = new SvelteMap<string, typeof commands.commands>();
		for (const command of commands.commands) {
			if (command.hidden && !command.keys?.length) continue;
			map.set(command.group(), [...(map.get(command.group()) ?? []), command]);
		}
		return [...map];
	});
	function capture(event: KeyboardEvent) {
		if (!capturing) return;
		event.preventDefault();
		event.stopPropagation();
		if (['Shift', 'Control', 'Alt', 'Meta'].includes(event.key)) return;
		const chord = eventChord(event);
		if (chord === 'Escape') {
			capturing = null;
			first = null;
			return;
		}
		// `g` waits for a second key: a sequence.
		if (!first && /^[a-z]$/.test(chord) && event.key === 'g') {
			first = chord;
			return;
		}
		const shortcut = first ? `${first} ${chord}` : chord;
		prefs.set('shortcuts', { ...prefs.value.shortcuts, [capturing]: [shortcut] });
		capturing = null;
		first = null;
	}

	function reset(id: string) {
		const next = { ...prefs.value.shortcuts };
		delete next[id];
		prefs.set('shortcuts', next);
	}

	onMount(() => {
		void api.server().then((found) => (server = found));
	});
</script>

<svelte:window onkeydowncapture={capture} />

<div class="page">
	<header class="page-header">
		<h1>{t.settings.title}</h1>
	</header>
	<div class="grid">
		<section class="panel">
			<header class="panel-header"><h2>{t.settings.language}</h2></header>
			<div class="panel-body choices" role="radiogroup" aria-label={t.settings.language}>
				{#each LOCALES as locale (locale)}
					<label class="check">
						<input
							type="radio"
							name="locale"
							checked={i18n.locale === locale}
							onchange={() => setLocale(locale)}
						/>
						{LOCALE_NAMES[locale]}
					</label>
				{/each}
			</div>
		</section>
		<section class="panel">
			<header class="panel-header"><h2>{t.settings.server}</h2></header>
			<dl class="panel-body details">
				<dt>{t.settings.version}</dt>
				<dd class="mono">{server?.version ?? '—'}</dd>
			</dl>
		</section>
		<section class="panel">
			<header class="panel-header"><h2>{t.settings.identify}</h2></header>
			<p class="panel-body muted">{t.settings.identifyHelp}</p>
		</section>
		<section class="panel">
			<header class="panel-header"><h2>{t.settings.account}</h2></header>
			<div class="panel-body">
				<button class="btn" onclick={() => api.signOut().then(() => location.reload())}>
					{t.app.signOut}
				</button>
			</div>
		</section>
	</div>

	<section class="panel">
		<header class="panel-header">
			<h2>{t.settings.shortcuts}</h2>
		</header>
		<div class="panel-body shortcuts">
			{#each groups as [group, list] (group)}
				<div>
					<h3>{group}</h3>
					<table class="table compact">
						<tbody>
							{#each list as command (command.id)}
								<tr class:conflict={conflicts.has(command.id)}>
									<td>
										{command.title()}
										{#if conflicts.has(command.id)}
											<span class="badge error">{t.settings.conflict}</span>
										{/if}
									</td>
									<td class="keys">
										{#if capturing === command.id}
											<span class="badge info">{first ? `${first} …` : t.settings.press}</span>
										{:else}
											{#each commands.keysOf(command) as key (key)}<Kbd keys={key} />{/each}
										{/if}
									</td>
									<td class="row-actions">
										<button class="btn subtle" onclick={() => (capturing = command.id)}>
											{t.settings.change}
										</button>
										<button
											class="btn subtle"
											onclick={() => reset(command.id)}
											disabled={!prefs.value.shortcuts[command.id]}>{t.settings.reset}</button
										>
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/each}
		</div>
	</section>
</div>

<style>
	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
		gap: 16px;
	}
	.choices {
		display: flex;
		gap: 20px;
	}
	.shortcuts {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
		gap: 24px;
	}
	h3 {
		margin-bottom: 6px;
		color: var(--muted);
		font-size: 13px;
	}
	.compact td {
		padding: 6px 8px;
	}
	.keys {
		white-space: nowrap;
	}
	.keys :global(.kbd) {
		margin-right: 4px;
	}
	.row-actions {
		width: 1%;
	}
	tr.conflict {
		background: var(--error-soft);
	}
	@media (max-width: 640px) {
		.shortcuts {
			grid-template-columns: minmax(0, 1fr);
		}
	}
</style>
