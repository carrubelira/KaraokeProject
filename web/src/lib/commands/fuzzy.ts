/**
 * Fuzzy matching for the command palette: every letter of the query, in order, in the text.
 * Higher scores for letters that start words and for runs; accents and case do not matter.
 */

export function fold(text: string): string {
	return text.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
}

/** A score (higher is better) and the matched positions, or null if it does not match. */
export function fuzzy(query: string, text: string): { score: number; positions: number[] } | null {
	const q = fold(query).replace(/\s+/g, '');
	if (!q) return { score: 0, positions: [] };
	const t = fold(text);
	const positions: number[] = [];
	let score = 0;
	let from = 0;
	let previous = -2;
	for (const char of q) {
		const at = t.indexOf(char, from);
		if (at < 0) return null;
		const wordStart = at === 0 || /[\s\-_/·.]/.test(t[at - 1]);
		score += 1 + (wordStart ? 6 : 0) + (at === previous + 1 ? 4 : 0);
		positions.push(at);
		previous = at;
		from = at + 1;
	}
	// Shorter texts and earlier matches first.
	score -= positions[0] * 0.05 + t.length * 0.01;
	if (t.startsWith(fold(query))) score += 10;
	return { score, positions };
}

export function rank<T>(query: string, items: T[], text: (item: T) => string, limit = 50): T[] {
	if (!query.trim()) return items.slice(0, limit);
	return items
		.map((item) => ({ item, match: fuzzy(query, text(item)) }))
		.filter(
			(x): x is { item: T; match: { score: number; positions: number[] } } => x.match !== null
		)
		.sort((a, b) => b.match.score - a.match.score)
		.slice(0, limit)
		.map((x) => x.item);
}
