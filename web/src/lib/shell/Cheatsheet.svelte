<script lang="ts">
	import { SvelteMap } from 'svelte/reactivity';
	/** Every shortcut that works here, grouped (?). */
	import { commands } from '#lib/commands/registry.svelte.js';
	import { i18n } from '#lib/i18n';
	import Kbd from './Kbd.svelte';

	const groups = $derived.by(() => {
		const map = new SvelteMap<string, { title: string; keys: string[] }[]>();
		for (const command of commands.commands) {
			const keys = commands.keysOf(command);
			if (!keys.length || !commands.isActive(command)) continue;
			const group = command.group();
			map.set(group, [...(map.get(group) ?? []), { title: command.title(), keys }]);
		}
		return [...map];
	});
</script>

<svelte:window
	onkeydown={(e) =>
		commands.cheatsheetOpen && e.key === 'Escape' && (commands.cheatsheetOpen = false)}
/>

{#if commands.cheatsheetOpen}
	<div class="backdrop" role="presentation" onclick={() => (commands.cheatsheetOpen = false)}></div>
	<div class="dialog sheet" role="dialog" aria-modal="true" aria-label={i18n.t.cheatsheet.title}>
		<header>
			<h2>{i18n.t.cheatsheet.title}</h2>
			<p class="muted">{i18n.t.cheatsheet.rebind}</p>
		</header>
		<div class="grid">
			{#each groups as [group, list] (group)}
				<div>
					<h3>{group}</h3>
					<dl>
						{#each list as item (item.title)}
							<dt>{item.title}</dt>
							<dd>
								{#each item.keys as key (key)}<Kbd keys={key} />{/each}
							</dd>
						{/each}
					</dl>
				</div>
			{/each}
		</div>
	</div>
{/if}

<style>
	.sheet {
		top: 6vh;
		width: min(60rem, calc(100vw - 2rem));
		max-height: 86vh;
		padding: 20px 24px;
	}
	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(17rem, 1fr));
		gap: 24px;
		margin-top: 18px;
	}
	h3 {
		margin-bottom: 8px;
		color: var(--muted);
		font-size: 13px;
	}
	dl {
		display: grid;
		grid-template-columns: 1fr auto;
		gap: 6px 12px;
		margin: 0;
	}
	dd {
		margin: 0;
		display: flex;
		gap: 4px;
		justify-content: end;
	}
</style>
