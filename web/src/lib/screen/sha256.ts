/**
 * SHA-256 that takes the bytes as they arrive (FIPS 180-4).
 *
 * The screens are opened over plain HTTP on the LAN (decision 011), where browsers give no
 * `crypto.subtle`; and a whole video should not have to sit in memory twice to be checked. So
 * every blob is hashed chunk by chunk while it downloads, and only one that matches its name is
 * kept.
 */

const K = new Uint32Array([
	0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
	0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
	0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
	0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
	0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
	0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
	0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
	0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
]);

export class Sha256 {
	#h = new Uint32Array([
		0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
	]);
	#block = new Uint8Array(64);
	#filled = 0;
	#length = 0;
	#w = new Uint32Array(64);

	update(bytes: Uint8Array): this {
		this.#length += bytes.length;
		let offset = 0;
		if (this.#filled) {
			const take = Math.min(64 - this.#filled, bytes.length);
			this.#block.set(bytes.subarray(0, take), this.#filled);
			this.#filled += take;
			offset = take;
			if (this.#filled < 64) return this;
			this.#compress(this.#block, 0);
			this.#filled = 0;
		}
		for (; offset + 64 <= bytes.length; offset += 64) this.#compress(bytes, offset);
		if (offset < bytes.length) {
			this.#block.set(bytes.subarray(offset));
			this.#filled = bytes.length - offset;
		}
		return this;
	}

	/** Lower-case hex, as the content store names blobs. */
	hex(): string {
		const bits = this.#length * 8;
		const pad = new Uint8Array((this.#filled < 56 ? 56 : 120) - this.#filled + 8);
		pad[0] = 0x80;
		const view = new DataView(pad.buffer);
		view.setUint32(pad.length - 8, Math.floor(bits / 2 ** 32));
		view.setUint32(pad.length - 4, bits >>> 0);
		this.update(pad);
		return Array.from(this.#h, (word) => word.toString(16).padStart(8, '0')).join('');
	}

	#compress(data: Uint8Array, at: number): void {
		const w = this.#w;
		for (let i = 0; i < 16; i++) {
			const j = at + i * 4;
			w[i] = (data[j] << 24) | (data[j + 1] << 16) | (data[j + 2] << 8) | data[j + 3];
		}
		for (let i = 16; i < 64; i++) {
			const a = w[i - 15];
			const b = w[i - 2];
			const s0 = ((a >>> 7) | (a << 25)) ^ ((a >>> 18) | (a << 14)) ^ (a >>> 3);
			const s1 = ((b >>> 17) | (b << 15)) ^ ((b >>> 19) | (b << 13)) ^ (b >>> 10);
			w[i] = (w[i - 16] + s0 + w[i - 7] + s1) | 0;
		}
		let [a, b, c, d, e, f, g, h] = this.#h;
		for (let i = 0; i < 64; i++) {
			const S1 = ((e >>> 6) | (e << 26)) ^ ((e >>> 11) | (e << 21)) ^ ((e >>> 25) | (e << 7));
			const ch = (e & f) ^ (~e & g);
			const t1 = (h + S1 + ch + K[i] + w[i]) | 0;
			const S0 = ((a >>> 2) | (a << 30)) ^ ((a >>> 13) | (a << 19)) ^ ((a >>> 22) | (a << 10));
			const maj = (a & b) ^ (a & c) ^ (b & c);
			const t2 = (S0 + maj) | 0;
			h = g;
			g = f;
			f = e;
			e = (d + t1) | 0;
			d = c;
			c = b;
			b = a;
			a = (t1 + t2) | 0;
		}
		const H = this.#h;
		H[0] += a;
		H[1] += b;
		H[2] += c;
		H[3] += d;
		H[4] += e;
		H[5] += f;
		H[6] += g;
		H[7] += h;
	}
}

export function sha256Hex(bytes: Uint8Array): string {
	return new Sha256().update(bytes).hex();
}
