/**
 * Keyboard shortcuts as text: `Mod+K`, `Space`, `Shift+J`, `Alt+ArrowUp`, `?`, and sequences of
 * two chords separated by a space (`g b`: press g, then b). `Mod` is Cmd on a Mac and Ctrl
 * elsewhere. A shortcut and a key event meet as the same normalised chord string.
 */

export const IS_MAC =
	typeof navigator !== 'undefined' &&
	/Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);

const MODIFIERS = ['Mod', 'Ctrl', 'Alt', 'Shift'] as const;
type Modifier = (typeof MODIFIERS)[number];

const ALIASES: Record<string, string> = {
	space: 'Space',
	' ': 'Space',
	esc: 'Escape',
	del: 'Delete',
	up: 'ArrowUp',
	down: 'ArrowDown',
	left: 'ArrowLeft',
	right: 'ArrowRight',
	return: 'Enter'
};

function normaliseKey(key: string): string {
	const alias = ALIASES[key.toLowerCase()] ?? ALIASES[key];
	if (alias) return alias;
	return key.length === 1 ? key.toLowerCase() : key;
}

/** A chord written by hand (`shift+j`, `Mod+k`) in canonical form (`Shift+J` → `Shift+j`). */
export function parseChord(text: string): string {
	const parts = text.split('+').map((p) => p.trim());
	// "Shift++" means Shift and the plus key.
	if (text.endsWith('++')) parts.splice(parts.length - 2, 2, '+');
	const key = parts.pop() ?? '';
	const mods = new Set<Modifier>();
	for (const part of parts) {
		const found = MODIFIERS.find((m) => m.toLowerCase() === part.toLowerCase());
		if (found) mods.add(found);
		else if (part.toLowerCase() === 'cmd' || part.toLowerCase() === 'meta') mods.add('Mod');
	}
	return [...MODIFIERS.filter((m) => mods.has(m)), normaliseKey(key)].join('+');
}

/** A whole shortcut: one chord or a sequence. */
export function parseShortcut(text: string): string[] {
	return text.trim().split(/\s+/).filter(Boolean).map(parseChord);
}

/** The chord a key event makes, in the same form as `parseChord`. */
export function eventChord(
	event: Pick<KeyboardEvent, 'key' | 'ctrlKey' | 'metaKey' | 'altKey' | 'shiftKey'>,
	mac = IS_MAC
): string {
	const mods: Modifier[] = [];
	const mod = mac ? event.metaKey : event.ctrlKey;
	if (mod) mods.push('Mod');
	if (mac ? event.ctrlKey : event.metaKey) mods.push('Ctrl');
	if (event.altKey) mods.push('Alt');
	let key = normaliseKey(event.key);
	// Shift is part of the character for symbols (?, +): only letters, digits and named keys
	// carry it as a modifier.
	if (event.shiftKey && (key.length > 1 || /[a-z0-9]/.test(key))) mods.push('Shift');
	if (key.length === 1 && /[A-Z]/.test(event.key)) key = event.key.toLowerCase();
	return [...mods, key].join('+');
}

/** How a shortcut is shown in the palette, the menus and the cheat sheet. */
export function label(shortcut: string, mac = IS_MAC): string {
	const names: Record<string, string> = mac
		? { Mod: '⌘', Ctrl: '⌃', Alt: '⌥', Shift: '⇧' }
		: { Mod: 'Ctrl', Ctrl: 'Win', Alt: 'Alt', Shift: 'Mayús' };
	const keys: Record<string, string> = {
		ArrowUp: '↑',
		ArrowDown: '↓',
		ArrowLeft: '←',
		ArrowRight: '→',
		Space: 'Espazo',
		Enter: '↵',
		Escape: 'Esc',
		Delete: 'Supr',
		Backspace: '⌫'
	};
	return parseShortcut(shortcut)
		.map((chord) =>
			chord
				.split('+')
				.map((p) => names[p] ?? keys[p] ?? (p.length === 1 ? p.toUpperCase() : p))
				.join(mac ? '' : '+')
		)
		.join(' ');
}

/** True when typing goes to a field (then only shortcuts with a modifier, or Escape, count). */
export function isTyping(target: EventTarget | null): boolean {
	if (typeof HTMLElement === 'undefined' || !(target instanceof HTMLElement)) return false;
	if (target.isContentEditable) return true;
	const tag = target.tagName;
	if (tag === 'TEXTAREA' || tag === 'SELECT') return true;
	if (tag === 'INPUT') {
		const type = (target as HTMLInputElement).type;
		return !['checkbox', 'radio', 'button', 'range', 'submit'].includes(type);
	}
	return false;
}

export function hasModifier(chord: string): boolean {
	return chord.startsWith('Mod+') || chord.startsWith('Ctrl+') || chord.startsWith('Alt+');
}
