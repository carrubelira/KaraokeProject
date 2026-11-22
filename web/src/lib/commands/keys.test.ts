import { describe, expect, it } from 'vitest';
import { eventChord, label, parseChord, parseShortcut } from './keys';
import { fuzzy, rank } from './fuzzy';
import { Registry } from './registry.svelte';
import { UndoStack } from './undo.svelte';

const key = (key: string, mods: Partial<KeyboardEvent> = {}) =>
	({
		key,
		ctrlKey: false,
		metaKey: false,
		altKey: false,
		shiftKey: false,
		...mods
	}) as KeyboardEvent;

describe('shortcuts', () => {
	it('parse to one canonical form', () => {
		expect(parseChord('mod+k')).toBe('Mod+k');
		expect(parseChord('Shift+J')).toBe('Shift+j');
		expect(parseChord('alt+up')).toBe('Alt+ArrowUp');
		expect(parseChord('space')).toBe('Space');
		expect(parseShortcut('g b')).toEqual(['g', 'b']);
	});

	it('match key events, with Mod as Cmd on a Mac and Ctrl elsewhere', () => {
		expect(eventChord(key('k', { ctrlKey: true }), false)).toBe('Mod+k');
		expect(eventChord(key('k', { metaKey: true }), true)).toBe('Mod+k');
		expect(eventChord(key('J', { shiftKey: true }), false)).toBe('Shift+j');
		expect(eventChord(key('?', { shiftKey: true }), false)).toBe('?');
		expect(eventChord(key(' '), false)).toBe('Space');
		expect(eventChord(key('ArrowUp', { altKey: true }), false)).toBe('Alt+ArrowUp');
	});

	it('are shown the platform way', () => {
		expect(label('Mod+k', true)).toBe('⌘K');
		expect(label('Mod+k', false)).toBe('Ctrl+K');
		expect(label('g b', false)).toBe('G B');
	});
});

describe('fuzzy search', () => {
	it('finds letters in order, preferring word starts, ignoring accents', () => {
		expect(fuzzy('rep', 'Reproducir')).not.toBeNull();
		expect(fuzzy('xyz', 'Reproducir')).toBeNull();
		expect(fuzzy('cancion', 'Canción nova')).not.toBeNull();
		const ranked = rank('sp', ['Subir o tono', 'Siguiente pista', 'Espazo'], (s) => s);
		expect(ranked[0]).toBe('Siguiente pista');
	});
});

describe('registry', () => {
	it('runs commands from chords and sequences, scoped ones first', async () => {
		const registry = new Registry();
		const ran: string[] = [];
		registry.register(
			{
				id: 'play',
				title: () => 'Play',
				group: () => 'T',
				keys: ['Space'],
				run: () => void ran.push('play')
			},
			{
				id: 'go-library',
				title: () => 'Library',
				group: () => 'G',
				keys: ['g b'],
				run: () => void ran.push('library')
			},
			{
				id: 'remove',
				title: () => 'Remove',
				group: () => 'P',
				scope: 'playlist',
				keys: ['Delete'],
				run: () => void ran.push('remove')
			},
			{
				id: 'cancel',
				title: () => 'Cancel',
				group: () => 'Q',
				scope: 'queue',
				keys: ['Delete'],
				run: () => void ran.push('cancel')
			}
		);
		const event = (k: string) =>
			({
				...key(k),
				target: null,
				isComposing: false,
				preventDefault: () => {}
			}) as unknown as KeyboardEvent;
		expect(registry.handle(event(' '))).toBe(true);
		expect(registry.handle(event('g'))).toBe(true);
		expect(registry.handle(event('b'))).toBe(true);
		registry.scope = 'queue';
		registry.handle(event('Delete'));
		registry.scope = 'playlist';
		registry.handle(event('Delete'));
		await Promise.resolve();
		expect(ran).toEqual(['play', 'library', 'cancel', 'remove']);
	});

	it('takes the operator’s bindings and reports conflicts', () => {
		const registry = new Registry();
		registry.register(
			{ id: 'a', title: () => 'A', group: () => 'G', keys: ['n'], run: () => {} },
			{ id: 'b', title: () => 'B', group: () => 'G', keys: ['m'], run: () => {} }
		);
		registry.overrides = { b: ['n'] };
		expect(registry.keysOf(registry.find('b')!)).toEqual(['n']);
		expect([...registry.conflicts().values()]).toEqual([['a', 'b']]);
	});
});

describe('undo', () => {
	it('undoes and redoes in order', async () => {
		const stack = new UndoStack();
		let value = 0;
		stack.push({
			label: '+1',
			undo: async () => void (value -= 1),
			redo: async () => void (value += 1)
		});
		value = 1;
		await stack.undo();
		expect(value).toBe(0);
		await stack.redo();
		expect(value).toBe(1);
		expect(stack.canRedo).toBe(false);
	});
});

describe('the plus key', () => {
	it('is a shortcut of its own, alone or with a modifier', () => {
		expect(parseChord('+')).toBe('+');
		expect(parseChord('Shift++')).toBe('Shift++');
		expect(
			eventChord({ key: '+', ctrlKey: false, metaKey: false, altKey: false, shiftKey: true })
		).toBe('+');
	});

	it('is written as a plus', () => {
		expect(label('+', false)).toBe('+');
		expect(label('Alt++', false)).toBe('Alt++');
		expect(label('Alt++', true)).toBe('⌥+');
	});
});
