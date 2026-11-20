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
	<div class="ctl-page-head"><h1>{t.settings.title}</h1></div>
	<div class="ctl-grid-2">
		<section class="ctl-box">
			<h2>{t.settings.language}</h2>
			<select
				class="ctl-field"
				value={i18n.locale}
				onchange={(e) => setLocale(e.currentTarget.value as Locale)}
				aria-label={t.settings.language}
			>
				{#each LOCALES as locale (locale)}<option value={locale}>{LOCALE_NAMES[locale]}</option
					>{/each}
			</select>
		</section>
		<section class="ctl-box">
			<h2>{t.settings.appearance}</h2>
			<label
				><input
					type="radio"
					checked={prefs.value.theme === 'dark'}
					onchange={() => prefs.set('theme', 'dark')}
				/>
				{t.settings.dark}</label
			>
			<label
				><input
					type="radio"
					checked={prefs.value.theme === 'light'}
					onchange={() => prefs.set('theme', 'light')}
				/>
				{t.settings.light}</label
			>
			<label
				><input
					type="checkbox"
					checked={prefs.value.dense}
					onchange={() => prefs.set('dense', !prefs.value.dense)}
				/>
				{t.settings.dense}
				<Kbd keys="Shift+d" /></label
			>
		</section>
		<section class="ctl-box">
			<h2>{t.settings.account}</h2>
			<button class="ctl-btn" onclick={() => api.signOut().then(() => location.reload())}
				>{t.app.signOut}</button
			>
		</section>
	</div>
	<section class="ctl-box shortcuts">
		<h2>{t.settings.shortcuts}</h2>
		{#each groups as [group, list] (group)}
			<h3>{group}</h3>
			<ul class="ctl-rows">
				{#each list as command (command.id)}
					<li class="ctl-row shortcut" class:ctl-marked={conflicts.has(command.id)}>
						<span>{command.title()}</span>
						<span>
							{#if capturing === command.id}
								<em>{first ? `${first} …` : t.settings.press}</em>
							{:else}
								{#each commands.keysOf(command) as key (key)}<Kbd keys={key} />
								{/each}
							{/if}
						</span>
						<button class="ctl-btn" onclick={() => (capturing = command.id)}>✎</button>
						<button
							class="ctl-btn"
							onclick={() => reset(command.id)}
							disabled={!prefs.value.shortcuts[command.id]}>{t.settings.reset}</button
						>
						{#if conflicts.has(command.id)}<span class="ctl-pill ctl-bad"
								>{t.settings.conflict}</span
							>{/if}
					</li>
				{/each}
			</ul>
		{/each}
	</section>
</div>

<style>
	label {
		display: flex;
		gap: var(--s-2);
		align-items: center;
		margin: var(--s-1) 0;
	}
	.shortcuts {
		margin-top: var(--s-4);
	}
	h3 {
		color: var(--ouro);
		font-size: var(--t-0);
		margin: var(--s-3) 0 var(--s-1);
	}
	.shortcut {
		grid-template-columns: minmax(12rem, 1fr) minmax(8rem, auto) auto auto auto;
	}
</style>
