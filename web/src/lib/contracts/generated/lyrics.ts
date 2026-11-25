/* Generated from schemas/ by `pnpm gen:contracts`. Do not edit by hand. */

/**
 * The `lyrics` track: lines, words and syllables with times and confidence, nothing else.
 */
export interface Lyrics {
	schema_version: string;
	language: string;
	singers: Singer[];
	lines: Line[];
	provenance: LyricsProvenance;
	edited: boolean;
}
export interface Singer {
	id: string;
	name: string | null;
	color: string | null;
}
export interface Line {
	id: string;
	/**
	 * Seconds from the start of the song audio.
	 */
	start: number;
	/**
	 * Seconds from the start of the song audio.
	 */
	end: number;
	singer: string | null;
	/**
	 * backing: backing vocals (written in parentheses); they may overlap the lead.
	 */
	role: 'lead' | 'backing';
	/**
	 * @minItems 1
	 */
	words: Word[];
}
export interface Word {
	/**
	 * Text as displayed, with its original spelling.
	 */
	text: string;
	/**
	 * Seconds from the start of the song audio.
	 */
	start: number;
	/**
	 * Seconds from the start of the song audio.
	 */
	end: number;
	confidence: number | null;
	/**
	 * Optional sub-units; when present their texts concatenate to the word text.
	 */
	parts: Part[];
}
/**
 * A sub-unit of a word (a syllable or a group of letters) with its own timing.
 */
export interface Part {
	text: string;
	/**
	 * Seconds from the start of the song audio.
	 */
	start: number;
	/**
	 * Seconds from the start of the song audio.
	 */
	end: number;
}
export interface LyricsProvenance {
	lyrics_source: 'user' | 'asr' | 'lrclib';
	separation_model: string | null;
	asr_model: string | null;
	align_model: string | null;
	engine_version: string;
	language_fallbacks: LanguageFallback[];
}
/**
 * Records that a step could not use a resource for the requested language.
 */
export interface LanguageFallback {
	step: string;
	requested: string;
	used: string;
	reason: string;
}
