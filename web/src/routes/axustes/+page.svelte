<script lang="ts">
	import { SvelteMap, SvelteSet } from 'svelte/reactivity';
	/** Settings: language, appearance and every shortcut, rebindable by pressing the new one. */
	import { eventChord } from '#lib/commands/keys.js';
	import { commands } from '#lib/commands/registry.svelte.js';
	import { api } from '#lib/control/api.js';
	import { i18n, LOCALE_NAMES, LOCALES, setLocale, type Locale } from '#lib/i18n';
	import Kbd from '#lib/shell/Kbd.svelte';
	import { prefs } from '#lib/shell/prefs.svelte.js';

	const t = $derived(i18n.t);
	let capturing = $state<string | null>(null);
	let first = $state<string | null>(null);
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
</script>

<svelte:window onkeydowncapture={capture} />

<div class="ctl-page">
	<header class="ctl-page-head"><h1>{t.settings.title}</h1></header>
	<div class="ctl-grid">
		<section class="ctl-panel">
			<div class="ctl-panel-head"><h2>{t.settings.general}</h2></div>
			<div class="ctl-panel-body ctl-form">
				<label class="ctl-field">
					<span>{t.settings.language}</span>
					<select
						class="ctl-select"
						value={i18n.locale}
						onchange={(e) => setLocale(e.currentTarget.value as Locale)}
					>
						{#each LOCALES as locale (locale)}<option value={locale}>{LOCALE_NAMES[locale]}</option
							>{/each}
					</select>
				</label>
				<label class="ctl-check"
					><input
						type="checkbox"
						checked={prefs.value.dense}
						onchange={() => prefs.set('dense', !prefs.value.dense)}
					/>
					{t.settings.dense}
					<Kbd keys="Shift+d" /></label
				>
			</div>
		</section>
		<section class="ctl-panel">
			<div class="ctl-panel-head"><h2>{t.settings.account}</h2></div>
			<div class="ctl-panel-body ctl-form">
				<p class="ctl-muted">{t.settings.accountHelp}</p>
				<div>
					<button class="ctl-btn" onclick={() => api.signOut().then(() => location.reload())}
						>{t.app.signOut}</button
					>
				</div>
			</div>
		</section>
	</div>
	<section class="ctl-panel shortcuts">
		<div class="ctl-panel-head">
			<h2>{t.settings.shortcuts}</h2>
			<span class="ctl-muted">{t.settings.shortcutsHelp}</span>
		</div>
		<table class="ctl-table">
			{#each groups as [group, list] (group)}
				<tbody>
					<tr class="group"><th colspan="3">{group}</th></tr>
					{#each list as command (command.id)}
						<tr class:ctl-marked={conflicts.has(command.id)}>
							<td>
								{command.title()}
								{#if conflicts.has(command.id)}<span class="ctl-badge ctl-bad"
										>{t.settings.conflict}</span
									>{/if}
							</td>
							<td
								><span class="keys">
									{#if capturing === command.id}
										<em>{first ? `${first} …` : t.settings.press}</em>
									{:else}
										{#each commands.keysOf(command) as key (key)}<Kbd keys={key} />{/each}
									{/if}
								</span></td
							>
							<td class="ctl-shrink">
								<button class="ctl-btn ctl-quiet" onclick={() => (capturing = command.id)}
									>{t.settings.change}</button
								>
								<button
									class="ctl-btn ctl-quiet"
									onclick={() => reset(command.id)}
									disabled={!prefs.value.shortcuts[command.id]}>{t.settings.reset}</button
								>
							</td>
						</tr>
					{/each}
				</tbody>
			{/each}
		</table>
	</section>
</div>

<style>
	.shortcuts {
		margin-top: var(--sp-4);
	}
	tr.group th {
		padding-top: var(--sp-4);
		color: var(--text-2);
		font-weight: 600;
	}
	.keys {
		display: inline-flex;
		gap: var(--sp-1);
	}
</style>
