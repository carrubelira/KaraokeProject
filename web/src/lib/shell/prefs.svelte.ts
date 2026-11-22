/**
 * The operator's preferences: shortcuts, density, the player they drive. Kept on the server (they
 * follow the operator to another computer) and applied at once here; quick changes are grouped
 * into one request.
 */
import { api } from '#lib/control/api.js';
import { commands } from '#lib/commands/registry.svelte.js';

export interface Preferences {
	shortcuts: Record<string, string[]>;
	dense: boolean;
	player: string | null;
	/** The playlist being prepared when no player has one (or there is no player yet). */
	playlist: string | null;
}

const DEFAULTS: Preferences = {
	shortcuts: {},
	dense: false,
	player: null,
	playlist: null
};

class Prefs {
	value = $state<Preferences>({ ...DEFAULTS });
	private timer: ReturnType<typeof setTimeout> | null = null;

	load(raw: Record<string, unknown>): void {
		this.value = { ...DEFAULTS, ...(raw as Partial<Preferences>) };
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
		if (typeof document !== 'undefined') {
			document.documentElement.dataset.density = this.value.dense ? 'dense' : 'comfortable';
		}
	}
}

export const prefs = new Prefs();
