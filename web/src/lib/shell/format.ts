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

/** When something happened: the time if it was today, else the day and the month. */
export function when(iso: string, locale: string, now = new Date()): string {
	const date = new Date(iso);
	if (Number.isNaN(date.getTime())) return '—';
	const today = date.toDateString() === now.toDateString();
	return today
		? date.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' })
		: date.toLocaleDateString(locale, { day: 'numeric', month: 'short' });
}
