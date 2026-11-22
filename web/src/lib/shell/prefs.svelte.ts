/**
 * The operator's preferences: shortcuts, the screen they drive, how much the background moves.
 * Kept on the server (they follow the operator to another computer) and applied at once here;
 * writes are grouped so a burst of changes sends one request.
 */
import { api } from '#lib/control/api.js';
import { commands } from '#lib/commands/registry.svelte.js';

export type Effects = 'full' | 'calm' | 'off';

export interface Preferences {
	shortcuts: Record<string, string[]>;
	/** The screen (player) the deck and the queue act on. */
	player: string | null;
	effects: Effects;
	/** Go on without a review when the analysis is sure. */
	autoConfirm: boolean;
}

const DEFAULTS: Preferences = {
	shortcuts: {},
	player: null,
	effects: 'full',
	autoConfirm: false
};

class Prefs {
	value = $state<Preferences>({ ...DEFAULTS });
	private timer: ReturnType<typeof setTimeout> | null = null;

	load(raw: Record<string, unknown>): void {
		const known = Object.fromEntries(Object.entries(raw).filter(([key]) => key in DEFAULTS));
		this.value = { ...DEFAULTS, ...(known as Partial<Preferences>) };
		this.apply();
	}

	set<K extends keyof Preferences>(key: K, value: Preferences[K]): void {
		this.value = { ...this.value, [key]: value };
		this.apply();
		if (this.timer) clearTimeout(this.timer);
		this.timer = setTimeout(() => void api.savePreferences({ ...this.value }).catch(() => {}), 600);
	}

	private apply(): void {
		commands.overrides = this.value.shortcuts;
	}
}

export const prefs = new Prefs();
