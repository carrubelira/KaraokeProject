/**
 * One registry for every action of the control UI (plan v4 §7): the command palette, the
 * keyboard shortcuts, the menus and the cheat sheet all come from it, so an action has one name,
 * one shortcut and one implementation.
 *
 * Commands belong to a scope: `global` ones work anywhere; the others only while a panel of that
 * scope has the focus (Delete removes from the queue in Live, cancels a job in Jobs).
 * Operators can rebind any shortcut; their bindings are kept on the server with their other
 * preferences.
 */

import { SvelteMap, SvelteSet } from 'svelte/reactivity';
import { eventChord, hasModifier, isTyping, parseShortcut } from './keys';

export type Scope = 'global' | 'live' | 'add' | 'jobs' | 'library' | 'nodes' | 'outputs' | 'editor';

export interface Command {
	id: string;
	/** Shown in the palette and the cheat sheet; a function so it follows the language. */
	title: () => string;
	group: () => string;
	scope?: Scope;
	/** Default shortcuts (`parseShortcut` syntax). */
	keys?: string[];
	run: () => void | Promise<void>;
	enabled?: () => boolean;
	/** Also while typing in a field (only sensible with a modifier). */
	whileTyping?: boolean;
	/** Words that also find it in the palette. */
	keywords?: string;
	/** Hidden from the palette (navigation inside lists, for instance). */
	hidden?: boolean;
}

const SEQUENCE_MS = 900;

class Registry {
	commands = $state<Command[]>([]);
	/** Operator overrides: command id → shortcuts (an empty list unbinds). */
	overrides = $state<Record<string, string[]>>({});
	scope = $state<Scope>('global');
	paletteOpen = $state(false);
	cheatsheetOpen = $state(false);
	/** The first chord of a sequence being typed, shown in the status bar. */
	pending = $state<string | null>(null);
	/** The last command run from the keyboard and how long it took (the < 100 ms target). */
	lastRun = $state<{ id: string; ms: number } | null>(null);
	private pendingAt = 0;

	register(...commands: Command[]): () => void {
		const ids = new SvelteSet(commands.map((c) => c.id));
		this.commands = [...this.commands.filter((c) => !ids.has(c.id)), ...commands];
		return () => {
			this.commands = this.commands.filter((c) => !ids.has(c.id) || !commands.includes(c));
		};
	}

	keysOf(command: Command): string[] {
		return this.overrides[command.id] ?? command.keys ?? [];
	}

	isActive(command: Command): boolean {
		const scope = command.scope ?? 'global';
		return (scope === 'global' || scope === this.scope) && (command.enabled?.() ?? true);
	}

	/** Shortcuts bound to more than one command of the same scope (shown in the settings). */
	conflicts(): Map<string, string[]> {
		const seen = new SvelteMap<string, string[]>();
		for (const command of this.commands) {
			for (const shortcut of this.keysOf(command)) {
				const key = `${command.scope ?? 'global'}|${parseShortcut(shortcut).join(' ')}`;
				seen.set(key, [...(seen.get(key) ?? []), command.id]);
			}
		}
		return new SvelteMap([...seen].filter(([, ids]) => ids.length > 1));
	}

	find(id: string): Command | undefined {
		return this.commands.find((c) => c.id === id);
	}

	async run(command: Command): Promise<void> {
		if (!this.isActive(command)) return;
		const started = performance.now();
		try {
			await command.run();
		} finally {
			this.lastRun = { id: command.id, ms: performance.now() - started };
		}
	}

	/** The window's keydown handler: returns true if a command took the event. */
	handle(event: KeyboardEvent): boolean {
		if (event.isComposing || event.key === 'Dead') return false;
		if (['Shift', 'Control', 'Alt', 'Meta'].includes(event.key)) return false;
		const chord = eventChord(event);
		const typing = isTyping(event.target);
		const now = performance.now();
		const first = this.pending && now - this.pendingAt < SEQUENCE_MS ? this.pending : null;
		this.pending = null;
		const candidates = this.commands.filter((c) => this.isActive(c));
		// Scoped commands win over global ones with the same shortcut.
		candidates.sort(
			(a, b) =>
				Number((b.scope ?? 'global') !== 'global') - Number((a.scope ?? 'global') !== 'global')
		);
		let startsSequence = false;
		for (const command of candidates) {
			if (typing && !command.whileTyping && !hasModifier(chord) && chord !== 'Escape') continue;
			for (const shortcut of this.keysOf(command)) {
				const chords = parseShortcut(shortcut);
				const hit =
					(chords.length === 1 && !first && chords[0] === chord) ||
					(chords.length === 2 && first === chords[0] && chords[1] === chord);
				if (hit) {
					event.preventDefault();
					void this.run(command);
					return true;
				}
				if (chords.length === 2 && !first && chords[0] === chord) startsSequence = true;
			}
		}
		if (startsSequence && !typing) {
			this.pending = chord;
			this.pendingAt = now;
			event.preventDefault();
			return true;
		}
		return false;
	}
}

export const commands = new Registry();
export { Registry };
