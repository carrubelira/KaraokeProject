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
	<div class="sheet" role="dialog" aria-modal="true" aria-label={i18n.t.cheatsheet.title}>
		<header>
			<h2>{i18n.t.cheatsheet.title}</h2>
			<p>{i18n.t.cheatsheet.rebind}</p>
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
	.backdrop {
		position: fixed;
		inset: 0;
		z-index: 40;
		background: rgb(0 0 0 / 0.5);
	}
	.sheet {
		position: fixed;
		z-index: 41;
		inset: 6vh 50% auto auto;
		transform: translateX(50%);
		width: min(64rem, calc(100vw - 2rem));
		max-height: 86vh;
		overflow: auto;
		padding: var(--s-5) var(--s-6);
		background: var(--fondo-2);
		border: 1px solid var(--raia-forte);
		border-radius: var(--radius-panel);
	}
	header p {
		color: var(--texto-3);
		margin: 0;
	}
	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr));
		gap: var(--s-5);
		margin-top: var(--s-4);
	}
	h3 {
		font-size: var(--t-0);
		color: var(--ouro);
		margin: 0 0 var(--s-2);
	}
	dl {
		display: grid;
		grid-template-columns: 1fr auto;
		gap: var(--s-1) var(--s-3);
		margin: 0;
	}
	dt {
		color: var(--texto-2);
	}
	dd {
		margin: 0;
		display: flex;
		gap: var(--s-1);
		justify-content: end;
	}
</style>
