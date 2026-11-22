<script lang="ts">
	/**
	 * Settings: language, how much the background moves, the server, song identification, and
	 * every shortcut, rebindable by pressing the new one.
	 */
	import { SvelteMap, SvelteSet } from 'svelte/reactivity';
	import { onMount } from 'svelte';
	import { eventChord } from '#lib/commands/keys.js';
	import { commands } from '#lib/commands/registry.svelte.js';
	import { api } from '#lib/control/api.js';
	import { i18n, LOCALE_NAMES, LOCALES, setLocale } from '#lib/i18n';
	import Kbd from '#lib/shell/Kbd.svelte';
	import { prefs, type Effects } from '#lib/shell/prefs.svelte.js';

	const t = $derived(i18n.t);
	let capturing = $state<string | null>(null);
	let first = $state<string | null>(null);
	let server = $state<{ version: string; fingerprint: string; tls: boolean } | null>(null);
	const conflicts = $derived(new SvelteSet([...commands.conflicts().values()].flat()));
	const groups = $derived.by(() => {
		const map = new SvelteMap<string, typeof commands.commands>();
		for (const command of commands.commands) {
			if (command.hidden && !command.keys?.length) continue;
			map.set(command.group(), [...(map.get(command.group()) ?? []), command]);
		}
		return [...map];
	});
	const EFFECTS: { value: Effects; label: () => string }[] = [
		{ value: 'full', label: () => t.settings.effectsFull },
		{ value: 'calm', label: () => t.settings.effectsCalm },
		{ value: 'off', label: () => t.settings.effectsOff }
	];

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

<div class="c-page">
	<div class="c-page-head"><h1>{t.settings.title}</h1></div>
	<div class="grid">
		<section class="c-panel">
			<header class="c-panel-head"><h2>{t.settings.language}</h2></header>
			<div class="c-panel-body segmented" role="radiogroup" aria-label={t.settings.language}>
				{#each LOCALES as locale (locale)}
					<button
						role="radio"
						aria-checked={i18n.locale === locale}
						class:on={i18n.locale === locale}
						onclick={() => setLocale(locale)}
					>
						{LOCALE_NAMES[locale]}
					</button>
				{/each}
			</div>
		</section>
		<section class="c-panel">
			<header class="c-panel-head"><h2>{t.settings.effects}</h2></header>
			<div class="c-panel-body segmented" role="radiogroup" aria-label={t.settings.effects}>
				{#each EFFECTS as effect (effect.value)}
					<button
						role="radio"
						aria-checked={prefs.value.effects === effect.value}
						class:on={prefs.value.effects === effect.value}
						onclick={() => prefs.set('effects', effect.value)}
					>
						{effect.label()}
					</button>
				{/each}
			</div>
		</section>
		<section class="c-panel">
			<header class="c-panel-head"><h2>{t.settings.server}</h2></header>
			<dl class="c-panel-body c-kv">
				<dt>{t.settings.version}</dt>
				<dd class="mono">{server?.version ?? '—'}</dd>
				<dt>{t.nodes.fingerprint}</dt>
				<dd class="mono small">{server?.fingerprint || '—'}</dd>
			</dl>
		</section>
		<section class="c-panel">
			<header class="c-panel-head"><h2>{t.settings.identify}</h2></header>
			<p class="c-panel-body dim small">{t.settings.identifyHelp}</p>
		</section>
		<section class="c-panel">
			<header class="c-panel-head"><h2>{t.settings.account}</h2></header>
			<div class="c-panel-body">
				<button class="c-btn" onclick={() => api.signOut().then(() => location.reload())}
					>{t.app.signOut}</button
				>
			</div>
		</section>
	</div>

	<section class="c-panel">
		<header class="c-panel-head"><h2>{t.settings.shortcuts}</h2></header>
		<div class="c-panel-body shortcuts">
			{#each groups as [group, list] (group)}
				<div>
					<h3>{group}</h3>
					<ul class="c-rows">
						{#each list as command (command.id)}
							<li class="c-row shortcut" class:is-marked={conflicts.has(command.id)}>
								<span class="name">{command.title()}</span>
								<span class="keys">
									{#if capturing === command.id}
										<em class="c-tally info">{first ? `${first} …` : t.settings.press}</em>
									{:else}
										{#each commands.keysOf(command) as key (key)}<Kbd keys={key} />{/each}
									{/if}
								</span>
								<button
									class="c-btn icon ghost"
									aria-label={t.settings.press}
									onclick={() => (capturing = command.id)}>✎</button
								>
								<button
									class="c-btn ghost"
									onclick={() => reset(command.id)}
									disabled={!prefs.value.shortcuts[command.id]}>{t.settings.reset}</button
								>
								{#if conflicts.has(command.id)}<span class="c-tag onair">{t.settings.conflict}</span
									>{/if}
							</li>
						{/each}
					</ul>
				</div>
			{/each}
		</div>
	</section>
</div>

<style>
	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
		gap: var(--gap);
	}
	.segmented {
		display: flex;
		gap: 4px;
	}
	.segmented button {
		flex: 1;
		padding: 9px 12px;
		border: 1px solid var(--line);
		border-radius: 2px;
		background: transparent;
		color: var(--dim);
		font: 500 12px var(--font-mono);
		text-transform: uppercase;
		letter-spacing: 0.06em;
		cursor: pointer;
	}
	.segmented button.on {
		border-color: var(--info);
		color: var(--text);
		background: rgb(60 200 255 / 0.08);
	}
	.small {
		font-size: 12.5px;
		margin: 0;
	}
	.shortcuts {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
		gap: 22px;
	}
	h3 {
		margin: 0 0 6px;
		font: 500 11px var(--font-mono);
		text-transform: uppercase;
		letter-spacing: 0.14em;
		color: var(--info);
	}
	.shortcut {
		min-height: 40px;
		padding: 4px 8px;
	}
	.name {
		flex: 1;
		font-size: 13.5px;
	}
	.keys {
		display: flex;
		gap: 4px;
	}
</style>
