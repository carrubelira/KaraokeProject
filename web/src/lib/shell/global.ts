/** The commands that work everywhere: navigation, the deck (transport), undo, the palette. */
import { goto } from '$app/navigation';
import { resolve } from '$app/paths';
import { commands, type Command } from '#lib/commands/registry.svelte.js';
import { i18n } from '#lib/i18n';
import { nextPlayer, redo, transport, undo } from './actions.svelte';

const t = () => i18n.t;

export const SECTIONS = [
	{ id: 'live', path: '/', key: 'g d', icon: 'live', label: () => t().nav.live },
	{ id: 'add', path: '/engadir', key: 'g n', icon: 'add', label: () => t().nav.add },
	{ id: 'jobs', path: '/traballos', key: 'g t', icon: 'jobs', label: () => t().nav.jobs },
	{ id: 'library', path: '/biblioteca', key: 'g b', icon: 'library', label: () => t().nav.library },
	{ id: 'nodes', path: '/nodos', key: 'g w', icon: 'nodes', label: () => t().nav.nodes },
	{ id: 'outputs', path: '/saidas', key: 'g s', icon: 'outputs', label: () => t().nav.outputs },
	{ id: 'settings', path: '/axustes', key: 'g a', icon: 'settings', label: () => t().nav.settings }
] as const;

export function registerGlobal(): () => void {
	const navigation: Command[] = SECTIONS.map((section) => ({
		id: `go.${section.id}`,
		title: section.label,
		group: () => t().groups.navigation,
		keys: [section.key],
		run: () => goto(resolve(section.path))
	}));
	const deck: Command[] = [
		{ id: 'transport.toggle', title: () => t().cmd.toggle, keys: ['Space'], run: transport.toggle },
		{ id: 'transport.next', title: () => t().cmd.next, keys: ['n'], run: transport.next },
		{
			id: 'transport.previous',
			title: () => t().cmd.previous,
			keys: ['p'],
			run: transport.previous
		},
		{
			id: 'transport.back',
			title: () => t().cmd.back,
			keys: ['ArrowLeft'],
			run: () => transport.seekBy(-5)
		},
		{
			id: 'transport.forward',
			title: () => t().cmd.forward,
			keys: ['ArrowRight'],
			run: () => transport.seekBy(5)
		},
		{
			id: 'transport.restart',
			title: () => t().cmd.restart,
			keys: ['Home'],
			run: transport.restart
		},
		{
			id: 'transport.volumeUp',
			title: () => t().cmd.volumeUp,
			keys: ['+', '='],
			run: () => transport.volumeBy(0.1)
		},
		{
			id: 'transport.volumeDown',
			title: () => t().cmd.volumeDown,
			keys: ['-'],
			run: () => transport.volumeBy(-0.1)
		},
		{
			id: 'transport.pitchUp',
			title: () => t().cmd.pitchUp,
			keys: [']'],
			run: () => transport.pitchBy(1)
		},
		{
			id: 'transport.pitchDown',
			title: () => t().cmd.pitchDown,
			keys: ['['],
			run: () => transport.pitchBy(-1)
		},
		{
			id: 'transport.pitchReset',
			title: () => t().cmd.pitchReset,
			keys: ['Mod+0'],
			run: transport.pitchReset
		},
		{ id: 'transport.stop', title: () => t().cmd.stop, keys: ['Shift+s'], run: transport.stop },
		{ id: 'screen.next', title: () => t().cmd.nextScreen, keys: ['s'], run: nextPlayer }
	].map((c) => ({ ...c, group: () => t().groups.transport }));
	const general: Command[] = [
		{
			id: 'palette',
			title: () => t().cmd.palette,
			keys: ['Mod+k'],
			whileTyping: true,
			run: () => void (commands.paletteOpen = !commands.paletteOpen),
			hidden: true
		},
		{
			id: 'cheatsheet',
			title: () => t().cmd.cheatsheet,
			keys: ['?'],
			run: () => void (commands.cheatsheetOpen = true)
		},
		{ id: 'add', title: () => t().cmd.add, keys: ['Mod+n'], run: () => goto(resolve('/engadir')) },
		{ id: 'undo', title: () => t().cmd.undo, keys: ['Mod+z'], run: undo },
		{ id: 'redo', title: () => t().cmd.redo, keys: ['Mod+Shift+z', 'Mod+y'], run: redo },
		{
			id: 'search',
			title: () => t().cmd.search,
			keys: ['/'],
			run: () => document.querySelector<HTMLInputElement>('[data-search]')?.focus()
		},
		{
			id: 'escape',
			title: () => t().common.close,
			keys: ['Escape'],
			whileTyping: true,
			hidden: true,
			run: () => {
				if (
					document.activeElement instanceof HTMLElement &&
					document.activeElement.matches('input, textarea')
				) {
					document.activeElement.blur();
				}
				commands.paletteOpen = false;
				commands.cheatsheetOpen = false;
			}
		}
	].map((c) => ({ ...c, group: () => t().groups.general }));
	return commands.register(...navigation, ...deck, ...general);
}
