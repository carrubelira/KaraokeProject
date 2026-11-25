/** Times as the control shows them. */
export function clock(seconds: number | null | undefined): string {
	if (seconds === null || seconds === undefined || !Number.isFinite(seconds)) return '—';
	const s = Math.max(0, Math.round(seconds));
	const h = Math.floor(s / 3600);
	const m = Math.floor((s % 3600) / 60);
	const r = String(s % 60).padStart(2, '0');
	return h ? `${h}:${String(m).padStart(2, '0')}:${r}` : `${m}:${r}`;
}

export function megabytes(mb: number | null | undefined): string {
	if (mb === null || mb === undefined) return '—';
	return mb >= 1024 ? `${(mb / 1024).toFixed(1)} GB` : `${mb} MB`;
}

/** How long ago a Unix time (seconds) was, short: 12 s, 4 min, 3 h, 2 d. */
export function ago(seconds: number, now = Date.now() / 1000): string {
	const s = Math.max(0, Math.round(now - seconds));
	if (s < 60) return `${s} s`;
	if (s < 3600) return `${Math.floor(s / 60)} min`;
	if (s < 86400) return `${Math.floor(s / 3600)} h`;
	return `${Math.floor(s / 86400)} d`;
}
