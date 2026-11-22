/** The commands that work everywhere: navigation, transport, undo, the palette, the view. */
import { goto } from '$app/navigation';
import { resolve } from '$app/paths';
import { commands, type Command } from '#lib/commands/registry.svelte.js';
import { i18n } from '#lib/i18n';
import { redo, transport, undo } from './actions.svelte';
import { prefs } from './prefs.svelte';

const t = () => i18n.t;

/** The sections, in the order and the groups of the sidebar. */
export const SECTIONS = [
	{ id: 'home', group: null, icon: 'home', path: '/', key: 'g h', label: () => t().nav.home },
	{
		id: 'live',
		group: 'session',
		icon: 'live',
		path: '/directo',
		key: 'g d',
		label: () => t().nav.live
	},
	{
		id: 'library',
		group: 'content',
		icon: 'library',
		path: '/biblioteca',
		key: 'g b',
		label: () => t().nav.library
	},
	{
		id: 'create',
		group: 'content',
		icon: 'create',
		path: '/crear',
		key: 'g n',
		label: () => t().nav.create
	},
	{
		id: 'jobs',
		group: 'system',
		icon: 'jobs',
		path: '/cola',
		key: 'g t',
		label: () => t().nav.jobs
	},
	{
		id: 'machines',
		group: 'system',
		icon: 'machines',
		path: '/equipos',
		key: 'g e',
		label: () => t().nav.machines
	},
	{
		id: 'outputs',
		group: 'system',
		icon: 'outputs',
		path: '/saidas',
		key: 'g s',
		label: () => t().nav.outputs
	},
	{
		id: 'settings',
		group: 'system',
		icon: 'settings',
		path: '/axustes',
		key: 'g a',
		label: () => t().nav.settings
	}
] as const;

export function registerGlobal(): () => void {
	const navigation: Command[] = SECTIONS.map((section) => ({
		id: `go.${section.id}`,
		title: section.label,
		group: () => t().groups.navigation,
		keys: [section.key],
		run: () => goto(resolve(section.path))
	}));
	const transportCommands: Command[] = [
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
		{ id: 'transport.stop', title: () => t().cmd.stop, keys: ['Shift+s'], run: transport.stop }
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
	const view: Command[] = [
		{
			id: 'view.dense',
			title: () => t().cmd.density,
			keys: ['Shift+d'],
			run: () => prefs.set('dense', !prefs.value.dense)
		}
	].map((c) => ({ ...c, group: () => t().groups.view }));
	return commands.register(...navigation, ...transportCommands, ...general, ...view);
}
