// Geometry of the harness illustration, shared by the static figure (SVG, built at build time)
// and the live hero (canvas). A port of the hero in docs/assets/src/build.py: seeded agent
// trajectories pass four gate apertures, grow more ordered at each, and land on the rows of a
// study table. Coordinates are in "flow" space: u runs along the flow, v across it. The
// horizontal layout maps (u, v) to (x, y); the vertical one (narrow screens) to (y, x).

export type Pt = [number, number];

export interface Line {
	row: number;
	/** Control points of the Catmull-Rom curve, in flow coordinates. */
	ctrl: Pt[];
	/** Dense samples of the curve, in flow coordinates. */
	pts: Pt[];
	/** Cumulative arc length at each sample. */
	len: number[];
	/** Arc-length fraction at which the line crosses each gate. */
	gateAt: number[];
	/** Per-line motion parameters. */
	phase: number;
	freq: number;
	wave: number;
	speed: number;
	offset: number;
	weight: number;
}

export interface Layout {
	w: number;
	h: number;
	vertical: boolean;
	/** Flow extent and cross extent. */
	U: number;
	V: number;
	/** Cross-axis band of the trajectories, and its centre. */
	top: number;
	bot: number;
	c: number;
	gates: { u: number; half: number }[];
	rows: number[];
	tableU: number;
	tableEnd: number;
	pitch: number;
	lines: Line[];
	/** Motion envelope amplitude per segment: before gate 1, between gates, after gate 4. */
	env: number[];
	scale: number;
}

export function rng(seed: number) {
	let a = seed >>> 0;
	return () => {
		a = (a + 0x6d2b79f5) >>> 0;
		let t = a;
		t = Math.imul(t ^ (t >>> 15), t | 1);
		t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
		return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
	};
}

const clamp = (x: number, a: number, b: number) => Math.min(Math.max(x, a), b);

/** Catmull-Rom through pts, sampled about every `step` units of u. */
function sample(pts: Pt[], step: number): Pt[] {
	const out: Pt[] = [];
	for (let i = 0; i < pts.length - 1; i++) {
		const p0 = pts[Math.max(i - 1, 0)], p1 = pts[i], p2 = pts[i + 1];
		const p3 = pts[Math.min(i + 2, pts.length - 1)];
		const c1: Pt = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
		const c2: Pt = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
		const n = Math.max(2, Math.ceil(Math.hypot(p2[0] - p1[0], p2[1] - p1[1]) / step));
		for (let j = 0; j < n + (i === pts.length - 2 ? 1 : 0); j++) {
			const t = j / n, s = 1 - t;
			out.push([
				s * s * s * p1[0] + 3 * s * s * t * c1[0] + 3 * s * t * t * c2[0] + t * t * t * p2[0],
				s * s * s * p1[1] + 3 * s * s * t * c1[1] + 3 * s * t * t * c2[1] + t * t * t * p2[1],
			]);
		}
	}
	return out;
}

export interface LayoutOptions {
	w: number;
	h: number;
	/** Page margin and gutter in px, so gates and table sit on the 12-column grid. */
	margin: number;
	gutter: number;
	seed?: number;
	lines?: number;
	vertical?: boolean;
	step?: number;
}

export function layout(o: LayoutOptions): Layout {
	const vertical = o.vertical ?? o.w < 640;
	const rand = rng(o.seed ?? 36);
	const R = 4;
	const N = o.lines ?? (vertical ? 64 : o.w < 1000 ? 84 : 112);
	const step = o.step ?? 5;
	const U = vertical ? o.h : o.w;
	const V = vertical ? o.w : o.h;

	let top: number, bot: number, gates: { u: number; half: number }[], rows: number[];
	let tableU: number, tableEnd: number, pitch: number, B: number;
	if (!vertical) {
		const cw = Math.min(o.w - 2 * o.margin, 1600 - 2 * o.margin);
		const m = (o.w - cw) / 2;
		const COL = (cw - 11 * o.gutter) / 12;
		const col = (i: number) => m + i * (COL + o.gutter);
		top = V * 0.17;
		bot = V * 0.79;
		B = bot - top;
		const g0 = col(2) + COL / 2, g3 = col(7) + COL / 2;
		const half = [0.47, 0.37, 0.3, 0.26];
		gates = half.map((hf, k) => ({ u: g0 + (k * (g3 - g0)) / 3, half: hf * B }));
		pitch = 0.143 * B;
		const c = (top + bot) / 2;
		rows = Array.from({ length: R }, (_, r) => c - (pitch * (R - 1)) / 2 + r * pitch + 0.06 * B);
		tableU = col(8);
		tableEnd = o.w - m;
	} else {
		top = o.margin;
		bot = V - o.margin;
		B = bot - top;
		const half = [0.42, 0.34, 0.29, 0.26];
		const g0 = U * 0.2, g3 = U * 0.6;
		gates = half.map((hf, k) => ({ u: g0 + (k * (g3 - g0)) / 3, half: hf * B }));
		pitch = B / R;
		rows = Array.from({ length: R }, (_, r) => top + (r + 0.5) * pitch);
		tableU = U * 0.72;
		tableEnd = U * 0.97;
	}
	const c = (top + bot) / 2;
	const order = [0.28, 0.66, 0.92, 1.0];
	const g0 = gates[0].u;

	const lines: Line[] = [];
	for (let i = 0; i < N; i++) {
		const per = Math.floor(N / R);
		const r = Math.min(R - 1, Math.floor((i * R) / N));
		const within = ((i % per) / Math.max(per - 1, 1)) * 2 - 1;
		const target = rows[r];
		const pts: Pt[] = [];
		let v = top - 8 + rand() * (B + 16);
		for (const u of [0, g0 * 0.25, g0 * 0.5, g0 * 0.75]) {
			pts.push([u, v]);
			v = clamp(v + (rand() * 2 - 1) * 0.24 * B, top - 8, bot + 8);
		}
		let prev = g0;
		gates.forEach((g, k) => {
			const spread = vertical ? 0.12 : 0.22;
			const ordered = c + (target - c) * Math.min(1, g.half / (0.29 * B)) + within * g.half * spread * (1 - order[k] * 0.8);
			const loose = c + (rand() * 2 - 1) * g.half * 0.92;
			let vk = order[k] * ordered + (1 - order[k]) * loose;
			vk = clamp(vk, c - g.half + 8, c + g.half - 8);
			if (k) {
				const mid = (prev + g.u) / 2;
				const amp = [0, 0.12, 0.06, 0.024][k] * B;
				pts.push([mid, (pts[pts.length - 1][1] + vk) / 2 + (rand() * 2 - 1) * amp]);
			}
			pts.push([g.u, vk]);
			prev = g.u;
		});
		const g3 = gates[3].u;
		pts.push([g3 + (tableU - g3) * 0.5, target + (pts[pts.length - 1][1] - target) * 0.15]);
		pts.push([tableU - 20, target]);
		pts.push([tableU, target]);
		const s = sample(pts, step);
		const len = [0];
		for (let j = 1; j < s.length; j++) len.push(len[j - 1] + Math.hypot(s[j][0] - s[j - 1][0], s[j][1] - s[j - 1][1]));
		const total = len[len.length - 1];
		const gateAt = gates.map((g) => {
			const j = s.findIndex((p) => p[0] >= g.u);
			return len[Math.max(j, 0)] / total;
		});
		lines.push({
			row: r,
			ctrl: pts,
			pts: s,
			len,
			gateAt,
			phase: rand() * Math.PI * 2,
			freq: 0.35 + rand() * 0.5,
			wave: (0.6 + rand() * 1.6) / Math.max(B, 1),
			speed: 0.055 + rand() * 0.06,
			offset: rand(),
			weight: 0.75 + rand() * 0.5,
		});
	}
	const env = [0.11, 0.04, 0.02, 0.009, 0.004].map((e) => e * B);
	return { w: o.w, h: o.h, vertical, U, V, top, bot, c, gates, rows, tableU, tableEnd, pitch, lines, env, scale: B / 336 };
}

/** The curve through pts as SVG cubic Béziers; map turns flow coordinates into x, y. */
export function smoothPath(pts: Pt[], map: (p: Pt) => Pt): string {
	const q = pts.map(map);
	const f = (x: number) => (Math.round(x * 10) / 10).toString();
	const d = [`M${f(q[0][0])} ${f(q[0][1])}`];
	for (let i = 0; i < q.length - 1; i++) {
		const p0 = q[Math.max(i - 1, 0)], p1 = q[i], p2 = q[i + 1], p3 = q[Math.min(i + 2, q.length - 1)];
		d.push(`C${f(p1[0] + (p2[0] - p0[0]) / 6)} ${f(p1[1] + (p2[1] - p0[1]) / 6)} ${f(p2[0] - (p3[0] - p1[0]) / 6)} ${f(p2[1] - (p3[1] - p1[1]) / 6)} ${f(p2[0])} ${f(p2[1])}`);
	}
	return d.join('');
}

/** Motion amplitude at u: largest before gate 1, zero at every gate and at the table. */
export function envelope(L: Layout, u: number): number {
	const g = L.gates;
	if (u <= g[0].u) {
		const x = u / g[0].u;
		return L.env[0] * Math.pow(1 - x, 0.7);
	}
	for (let k = 0; k < g.length - 1; k++) {
		if (u <= g[k + 1].u) return L.env[k + 1] * Math.sin((Math.PI * (u - g[k].u)) / (g[k + 1].u - g[k].u));
	}
	if (u <= L.tableU) return L.env[4] * Math.sin((Math.PI * (u - g[3].u)) / (L.tableU - g[3].u));
	return 0;
}

/** Index of the sample at arc-length fraction f (binary search). */
export function indexAt(line: Line, f: number): number {
	const target = f * line.len[line.len.length - 1];
	let lo = 0, hi = line.len.length - 1;
	while (lo < hi) {
		const mid = (lo + hi) >> 1;
		if (line.len[mid] < target) lo = mid + 1;
		else hi = mid;
	}
	return lo;
}

/** The example study table the work resolves into: one row per arm, three seeds each. */
export const TABLE = [
	{ arm: 'linear', n: '3', v: '71.4', sd: '0.6' },
	{ arm: 'full', n: '3', v: '85.1', sd: '0.4' },
	{ arm: 'lora-8', n: '3', v: '84.2', sd: '0.5' },
	{ arm: 'lora-16', n: '3', v: '84.6', sd: '0.3' },
];
