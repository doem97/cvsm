// The live harness: a canvas that redraws the hero illustration every frame.
// Agent trajectories breathe between the gates (most before gate 01, none at a gate), particles
// stream along them and brighten at each gate, and an orange pulse holds at every gate before it
// lands on a table row, whose blue check then redraws. The pointer gently parts the unordered
// work before gate 01; the gates themselves never move. Paused offscreen and in hidden tabs; one
// static frame under prefers-reduced-motion.
import { layout, envelope, indexAt, type Layout, type Line, type Pt } from '~/lib/harness';

interface Data {
	gates: { num: string; name: string }[];
	table: { arm: string; n: string; metric: string; spec: string };
	caption: string;
	rows: { arm: string; n: string; v: string; sd: string }[];
}

interface Colors {
	text: string;
	muted: string;
	hair: string;
	hair2: string;
	accent: string;
	accentInk: string;
	verify: string;
	verifyInk: string;
	bg: string;
	rgb: [number, number, number];
}

const HOLD = 0.7; // seconds the pulse holds at each gate
const PULSE_SPEED = 0.15; // arc fraction per second
const LAND = 1.4; // seconds after landing before the next cycle

function hexRgb(c: string): [number, number, number] {
	const m = c.trim().match(/^#?([0-9a-f]{6})$/i);
	if (!m) return [242, 242, 240];
	const n = parseInt(m[1], 16);
	return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function readColors(el: Element): Colors {
	const cs = getComputedStyle(el);
	const v = (k: string) => cs.getPropertyValue(k).trim();
	return {
		text: v('--rh-text'), muted: v('--rh-muted'), hair: v('--rh-hair'), hair2: v('--rh-hair-2'),
		accent: v('--rh-accent'), accentInk: v('--rh-accent-ink'), verify: v('--rh-verify'),
		verifyInk: v('--rh-verify-ink'), bg: v('--rh-bg'), rgb: hexRgb(v('--rh-text')),
	};
}

// Chinese labels keep their casing (run, not RUN), as the CSS caps token does.
const caps = (s: string) => (document.documentElement.lang.startsWith('zh') ? s : s.toUpperCase());
const smooth = (x: number) => (x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x));

class LiveHarness {
	fig: HTMLElement;
	canvas: HTMLCanvasElement;
	ctx: CanvasRenderingContext2D;
	data: Data;
	L!: Layout;
	env: Float32Array[] = [];
	col!: Colors;
	dpr = 1;
	t = 0;
	last = 0;
	raf = 0;
	visible = false;
	reduced = matchMedia('(prefers-reduced-motion: reduce)');
	pointer = { u: 0, v: 0, tu: 0, tv: 0, on: 0, target: 0 };
	cycle = { start: 0, line: 0, row: 0, n: 0, plan: [] as { t: number; f: number; hold: number }[], end: 0 };
	flash = [0, 0, 0, 0].map(() => -10);
	grad: CanvasGradient | null = null;
	heroGrad: CanvasGradient | null = null;

	constructor(fig: HTMLElement) {
		this.fig = fig;
		this.canvas = fig.querySelector('canvas')!;
		this.ctx = this.canvas.getContext('2d')!;
		this.data = JSON.parse(fig.dataset.harness || '{}');
		this.col = readColors(fig);
		this.resize();
		new ResizeObserver(() => this.resize()).observe(fig);
		new IntersectionObserver(([e]) => {
			this.visible = e.isIntersecting;
			this.kick();
		}).observe(fig);
		document.addEventListener('visibilitychange', () => this.kick());
		this.reduced.addEventListener('change', () => this.kick());
		new MutationObserver(() => {
			this.col = readColors(this.fig);
			this.makeGradients();
			this.drawOnce();
		}).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
		fig.addEventListener('pointermove', (e) => this.onPointer(e));
		fig.addEventListener('pointerleave', () => (this.pointer.target = 0));
		document.fonts?.ready.then(() => this.drawOnce());
	}

	onPointer(e: PointerEvent) {
		if (e.pointerType !== 'mouse') return;
		const r = this.canvas.getBoundingClientRect();
		const x = e.clientX - r.left, y = e.clientY - r.top;
		const [u, v] = this.L.vertical ? [y, x] : [x, y];
		this.pointer.tu = u;
		this.pointer.tv = v;
		if (!this.pointer.on) {
			this.pointer.u = u;
			this.pointer.v = v;
		}
		this.pointer.target = 1;
	}

	resize() {
		const w = Math.max(1, Math.round(this.fig.clientWidth));
		const h = Math.max(1, Math.round(this.fig.clientHeight));
		if (this.L && this.L.w === w && this.L.h === h) return;
		this.dpr = Math.min(window.devicePixelRatio || 1, 2);
		this.canvas.width = Math.round(w * this.dpr);
		this.canvas.height = Math.round(h * this.dpr);
		const vw = window.innerWidth;
		const margin = Math.min(96, Math.max(16, vw * 0.05));
		const gutter = Math.min(24, Math.max(16, vw * 0.022));
		this.L = layout({ w, h, margin, gutter, seed: 36 });
		this.env = this.L.lines.map((ln) => Float32Array.from(ln.pts, (p) => envelope(this.L, p[0])));
		this.makeGradients();
		this.newCycle(this.t, this.cycle.n);
		this.drawOnce();
	}

	makeGradients() {
		const L = this.L, [r, g, b] = this.col.rgb, ctx = this.ctx;
		const g0 = L.gates[0].u;
		const mk = (a: number) => {
			const gr = L.vertical ? ctx.createLinearGradient(0, 0, 0, g0) : ctx.createLinearGradient(0, 0, g0, 0);
			gr.addColorStop(0, `rgba(${r},${g},${b},0)`);
			gr.addColorStop(1, `rgba(${r},${g},${b},${a})`);
			return gr;
		};
		this.grad = mk(0.26);
		this.heroGrad = mk(0.95);
	}

	/** Plan one pulse: a trajectory into the next row, its stops at the four gates. */
	newCycle(now: number, n: number) {
		const L = this.L;
		const row = n % 4;
		const cohort = L.lines.filter((l) => l.row === row);
		const line = L.lines.indexOf(cohort[Math.floor(cohort.length * (0.35 + 0.3 * (((n * 7) % 10) / 10)))]);
		const ln = L.lines[line];
		const f0 = 0.1;
		const plan: { t: number; f: number; hold: number }[] = [{ t: now, f: f0, hold: 0 }];
		let tt = now, f = f0;
		for (const ga of ln.gateAt) {
			tt += (ga - f) / PULSE_SPEED;
			plan.push({ t: tt, f: ga, hold: HOLD });
			tt += HOLD;
			f = ga;
		}
		tt += (1 - f) / PULSE_SPEED;
		plan.push({ t: tt, f: 1, hold: 0 });
		this.cycle = { start: now, line, row, n, plan, end: tt + LAND };
	}

	/** Where the pulse is at time t: its arc fraction and, if holding, the gate index. */
	pulseAt(t: number): { f: number; gate: number; holdP: number; alpha: number } {
		const P = this.cycle.plan;
		for (let i = 1; i < P.length; i++) {
			const a = P[i - 1], b = P[i];
			const depart = a.t + a.hold;
			if (t < a.t + a.hold && i > 1) return { f: a.f, gate: i - 2, holdP: (t - a.t) / a.hold, alpha: 1 };
			if (t < b.t) {
				const p = (t - depart) / (b.t - depart);
				const f = a.f + (b.f - a.f) * p;
				const alpha = i === 1 ? smooth(p * 4) : i === P.length - 1 ? 1 - smooth((p - 0.8) * 5) : 1;
				return { f, gate: -1, holdP: 0, alpha };
			}
		}
		return { f: 1, gate: -1, holdP: 0, alpha: 0 };
	}

	map(u: number, v: number): Pt {
		return this.L.vertical ? [v, u] : [u, v];
	}

	kick() {
		const running = this.visible && !document.hidden && !this.reduced.matches;
		if (running && !this.raf) {
			this.last = performance.now();
			this.raf = requestAnimationFrame((n) => this.frame(n));
		} else if (!running) {
			if (this.raf) cancelAnimationFrame(this.raf);
			this.raf = 0;
			this.drawOnce();
		}
	}

	frame(now: number) {
		const dt = Math.min(0.05, (now - this.last) / 1000);
		this.last = now;
		this.t += dt;
		const p = this.pointer;
		p.on += (p.target - p.on) * Math.min(1, dt * 4);
		p.u += (p.tu - p.u) * Math.min(1, dt * 6);
		p.v += (p.tv - p.v) * Math.min(1, dt * 6);
		if (this.t > this.cycle.end) this.newCycle(this.t, this.cycle.n + 1);
		this.draw(this.t, false);
		this.raf = requestAnimationFrame((n) => this.frame(n));
	}

	drawOnce() {
		if (!this.L) return;
		if (this.reduced.matches) {
			// A still frame: the pulse holding at gate 02, every row checked.
			this.newCycle(0, 2);
			const P = this.cycle.plan[2];
			this.draw(P.t + P.hold * 0.3, true);
		} else this.draw(this.t, false);
	}

	draw(t: number, still: boolean) {
		const { ctx, L, col } = this;
		const dpr = this.dpr;
		ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
		ctx.clearRect(0, 0, L.w, L.h);
		const sc = Math.max(0.75, Math.min(1.15, L.scale));
		const ptr = this.pointer;
		const pulse = this.pulseAt(t);

		// Gate walls first, behind the work.
		ctx.lineWidth = 1;
		ctx.strokeStyle = col.hair2;
		ctx.beginPath();
		for (const g of L.gates) {
			const a = L.c - g.half, b = L.c + g.half;
			const lo = L.vertical ? 0 : L.top - 30 * sc, hi = L.vertical ? L.V : L.bot + 30 * sc;
			this.seg(g.u, lo, g.u, a);
			this.seg(g.u, b, g.u, hi);
		}
		ctx.stroke();

		// The trajectories.
		const lines = L.lines;
		const pts: Pt[][] = new Array(lines.length);
		const sigma2 = 2 * Math.pow(0.16 * (L.bot - L.top), 2);
		const push = 0.065 * (L.bot - L.top) * ptr.on;
		for (let i = 0; i < lines.length; i++) {
			const ln = lines[i], env = this.env[i];
			const out: Pt[] = new Array(ln.pts.length);
			for (let j = 0; j < ln.pts.length; j++) {
				const [u, v] = ln.pts[j];
				const e = env[j];
				let dv = 0;
				if (e > 0.01) {
					dv = e * Math.sin((still ? 1.3 : t) * ln.freq + u * ln.wave * 6 + ln.phase);
					if (push > 0.5) {
						const du = u - ptr.u, dvp = v - ptr.v;
						const k = Math.exp(-(du * du + dvp * dvp) / sigma2) * (e / L.env[0]);
						dv += Math.sign(dvp || 1) * push * k;
					}
				}
				out[j] = L.vertical ? [v + dv, u] : [u, v + dv];
			}
			pts[i] = out;
		}
		ctx.strokeStyle = this.grad!;
		ctx.lineWidth = 0.8;
		for (let i = 0; i < lines.length; i++) {
			if (i === this.cycle.line) continue;
			this.poly(pts[i], 0, pts[i].length - 1);
			ctx.stroke();
		}

		// Particles: brighter after every gate they pass.
		if (!still) {
			const [r, g, b] = col.rgb;
			ctx.lineWidth = 1.3;
			ctx.lineCap = 'round';
			for (let i = 0; i < lines.length; i++) {
				const ln = lines[i];
				const total = ln.len[ln.len.length - 1];
				const f = (ln.offset + t * ln.speed) % 1;
				if (f < 0.06) continue;
				let passed = 0;
				for (const ga of ln.gateAt) if (f > ga) passed++;
				const a = ([0.22, 0.4, 0.55, 0.7, 0.85][passed] * smooth((f - 0.06) / 0.12) * (1 - smooth((f - 0.95) / 0.05))) * ln.weight;
				const i1 = indexAt(ln, f), i0 = indexAt(ln, Math.max(0, f - (passed ? 30 : 20) / total));
				ctx.strokeStyle = `rgba(${r},${g},${b},${Math.min(1, a)})`;
				this.poly(pts[i], i0, i1);
				ctx.stroke();
			}
		}

		// The highlighted trajectory and its orange pulse.
		const hl = lines[this.cycle.line];
		const hp = pts[this.cycle.line];
		ctx.lineCap = 'butt';
		ctx.strokeStyle = this.heroGrad!;
		ctx.lineWidth = 1.5;
		this.poly(hp, 0, hp.length - 1);
		ctx.stroke();
		const total = hl.len[hl.len.length - 1];
		if (pulse.alpha > 0) {
			const i1 = indexAt(hl, pulse.f), i0 = indexAt(hl, Math.max(0, pulse.f - 34 / total));
			ctx.globalAlpha = pulse.alpha;
			ctx.strokeStyle = col.accent;
			ctx.lineWidth = 3.5;
			ctx.lineCap = 'round';
			this.poly(hp, i0, i1);
			ctx.stroke();
			ctx.globalAlpha = 1;
		}

		// Gates: an aperture held open by two orange anchor points; the active one rings.
		for (let k = 0; k < L.gates.length; k++) {
			const g = L.gates[k];
			const a = L.c - g.half, b = L.c + g.half;
			const active = pulse.gate === k;
			ctx.strokeStyle = col.accent;
			ctx.lineWidth = 2;
			ctx.beginPath();
			this.seg(g.u, a - 28 * sc, g.u, a);
			this.seg(g.u, b + 28 * sc, g.u, b);
			ctx.stroke();
			ctx.fillStyle = col.accent;
			const s = (active ? 11 : 8) * sc;
			for (const v of [a, b]) {
				const [x, y] = this.map(g.u, v);
				ctx.fillRect(x - s / 2, y - s / 2, s, s);
			}
			if (active) {
				const j = indexAt(hl, hl.gateAt[k]);
				const [x, y] = hp[j];
				const p = still ? 0.15 : pulse.holdP;
				ctx.globalAlpha = 1 - p;
				ctx.lineWidth = 2;
				ctx.beginPath();
				ctx.arc(x, y, (6 + 14 * p) * sc, 0, Math.PI * 2);
				ctx.stroke();
				ctx.globalAlpha = 1;
			}
			this.gateLabel(k, active, sc);
		}

		// Landing: the row the pulse reaches flashes blue and its check redraws.
		if (!still && pulse.f >= 1 && this.flash[this.cycle.row] < this.cycle.plan[this.cycle.plan.length - 1].t) {
			this.flash[this.cycle.row] = this.cycle.plan[this.cycle.plan.length - 1].t;
		}
		this.table(t, still, sc);
	}

	seg(u1: number, v1: number, u2: number, v2: number) {
		const [x1, y1] = this.map(u1, v1), [x2, y2] = this.map(u2, v2);
		this.ctx.moveTo(x1, y1);
		this.ctx.lineTo(x2, y2);
	}

	poly(p: Pt[], i0: number, i1: number) {
		const ctx = this.ctx;
		ctx.beginPath();
		ctx.moveTo(p[i0][0], p[i0][1]);
		for (let j = i0 + 1; j <= i1; j++) ctx.lineTo(p[j][0], p[j][1]);
	}

	font(size: number, weight = 400) {
		const ctx = this.ctx;
		ctx.font = `${weight} ${size}px "Geist Mono Variable", "Noto Sans SC Variable", ui-monospace, monospace`;
		if ('letterSpacing' in ctx) (ctx as any).letterSpacing = '0.06em';
	}

	gateLabel(k: number, active: boolean, sc: number) {
		const { ctx, L, col } = this;
		const g = L.gates[k], d = this.data.gates[k];
		const size = Math.round(12 * Math.max(0.92, Math.min(1.1, sc)));
		this.font(size, 500);
		ctx.textBaseline = 'alphabetic';
		if (!L.vertical) {
			const y = L.bot + (L.h - L.bot) * 0.62;
			ctx.textAlign = 'right';
			ctx.fillStyle = col.accentInk;
			ctx.fillText(d.num, g.u - 7, y);
			ctx.textAlign = 'left';
			ctx.fillStyle = col.text;
			this.font(size, 400);
			ctx.fillText(caps(d.name), g.u + 7, y);
			if (active) {
				const w = ctx.measureText(caps(d.name)).width;
				ctx.fillStyle = col.accent;
				ctx.fillRect(g.u + 7, y + 7, w, 1.5);
			}
		} else {
			const x = L.c - g.half + 14, y = g.u + size * 0.36;
			const label = `${d.num}  ${caps(d.name)}`;
			const w = ctx.measureText(label).width;
			ctx.fillStyle = col.bg;
			ctx.fillRect(x - 6, y - size, w + 12, size * 1.5);
			ctx.textAlign = 'left';
			ctx.fillStyle = col.accentInk;
			ctx.fillText(d.num, x, y);
			ctx.fillStyle = col.text;
			this.font(size, 400);
			ctx.fillText(caps(d.name), x + ctx.measureText(`${d.num}  `).width, y);
			if (active) {
				ctx.fillStyle = col.accent;
				ctx.fillRect(x, y + 6, w, 1.5);
			}
		}
	}

	check(x: number, y: number, s: number, p: number) {
		const ctx = this.ctx;
		const a: Pt = [x, y - s * 0.45], b: Pt = [x + s * 0.36, y - s * 0.08], c: Pt = [x + s, y - s * 0.9];
		const l1 = Math.hypot(b[0] - a[0], b[1] - a[1]), l2 = Math.hypot(c[0] - b[0], c[1] - b[1]);
		const d = p * (l1 + l2);
		ctx.beginPath();
		ctx.moveTo(a[0], a[1]);
		if (d <= l1) ctx.lineTo(a[0] + ((b[0] - a[0]) * d) / l1, a[1] + ((b[1] - a[1]) * d) / l1);
		else {
			ctx.lineTo(b[0], b[1]);
			const q = (d - l1) / l2;
			ctx.lineTo(b[0] + (c[0] - b[0]) * q, b[1] + (c[1] - b[1]) * q);
		}
		ctx.stroke();
	}

	table(t: number, still: boolean, sc: number) {
		const { ctx, L, col, data } = this;
		const size = Math.round(13 * Math.max(0.9, Math.min(1.12, sc)));
		const progress = (r: number) => (still ? 1 : smooth((t - this.flash[r]) / 0.5));
		const wash = (r: number) => (still ? 0 : Math.max(0, 1 - (t - this.flash[r]) / 1.6));
		ctx.lineWidth = 1;
		if (!L.vertical) {
			const tx = L.tableU, right = L.tableEnd, P = L.pitch;
			const narrow = right - tx < 300;
			const cols = narrow ? [tx + 14, -1, tx + 0.42 * (right - tx), right - 12] : [tx + 22, tx + 0.38 * (right - tx), tx + 0.5 * (right - tx), right - 16];
			const hy = L.rows[0] - P / 2 - 40 * sc;
			ctx.strokeStyle = col.hair2;
			ctx.beginPath();
			ctx.moveTo(tx, hy); ctx.lineTo(right, hy);
			ctx.moveTo(tx, hy); ctx.lineTo(tx, L.rows[3] + P / 2);
			ctx.moveTo(tx, L.rows[3] + P / 2); ctx.lineTo(right, L.rows[3] + P / 2);
			ctx.stroke();
			this.font(size - 1, 400);
			ctx.textBaseline = 'middle';
			const hyT = hy + 22 * sc;
			ctx.fillStyle = col.muted;
			ctx.textAlign = 'left';
			ctx.fillText(caps(data.table.arm), cols[0], hyT);
			if (cols[1] > 0) ctx.fillText(data.table.n, cols[1], hyT);
			ctx.fillText(caps(data.table.metric), cols[2], hyT);
			ctx.textAlign = 'right';
			ctx.fillStyle = col.verifyInk;
			ctx.fillText(caps(data.table.spec), cols[3], hyT);
			data.rows.forEach((row, r) => {
				const y = L.rows[r];
				const wsh = wash(r);
				if (wsh > 0) {
					ctx.globalAlpha = wsh * 0.14;
					ctx.fillStyle = col.verify;
					ctx.fillRect(tx + 1, y - P / 2 + 1, right - tx - 1, P - 1);
					ctx.globalAlpha = 1;
				}
				if (r) {
					ctx.strokeStyle = col.hair;
					ctx.beginPath(); ctx.moveTo(tx, y - P / 2); ctx.lineTo(right, y - P / 2); ctx.stroke();
				}
				ctx.fillStyle = col.text;
				ctx.beginPath(); ctx.arc(tx, y, 2.5, 0, Math.PI * 2); ctx.fill();
				this.font(size, 400);
				if ('letterSpacing' in ctx) (ctx as any).letterSpacing = '0px';
				ctx.textAlign = 'left';
				ctx.fillText(row.arm, cols[0], y);
				if (cols[1] > 0) ctx.fillText(row.n, cols[1], y);
				ctx.fillText(row.v, cols[2], y);
				const w = ctx.measureText(row.v + ' ').width;
				ctx.fillStyle = col.muted;
				ctx.fillText(`± ${row.sd}`, cols[2] + w, y);
				ctx.strokeStyle = col.verify;
				ctx.lineWidth = 2;
				ctx.lineCap = 'round';
				ctx.lineJoin = 'round';
				this.check(cols[3] - 16 * sc, y + 7 * sc, 16 * sc, progress(r));
				ctx.lineWidth = 1;
				ctx.lineCap = 'butt';
			});
			this.font(size - 1, 400);
			ctx.textAlign = 'left';
			ctx.fillStyle = col.muted;
			ctx.fillText(caps(data.caption), tx, L.rows[3] + P / 2 + 26 * sc);
		} else {
			const ty = L.tableU, P = L.pitch;
			ctx.strokeStyle = col.hair2;
			ctx.beginPath();
			ctx.moveTo(L.top, ty); ctx.lineTo(L.bot, ty);
			ctx.stroke();
			ctx.textAlign = 'center';
			ctx.textBaseline = 'alphabetic';
			data.rows.forEach((row, r) => {
				const x = L.rows[r];
				const wsh = wash(r);
				if (wsh > 0) {
					ctx.globalAlpha = wsh * 0.14;
					ctx.fillStyle = col.verify;
					ctx.fillRect(x - P / 2 + 1, ty + 1, P - 2, 104);
					ctx.globalAlpha = 1;
				}
				if (r) {
					ctx.strokeStyle = col.hair;
					ctx.beginPath(); ctx.moveTo(x - P / 2, ty); ctx.lineTo(x - P / 2, ty + 104); ctx.stroke();
				}
				ctx.fillStyle = col.text;
				ctx.beginPath(); ctx.arc(x, ty, 2.5, 0, Math.PI * 2); ctx.fill();
				this.font(12, 400);
				if ('letterSpacing' in ctx) (ctx as any).letterSpacing = '0px';
				ctx.fillText(row.arm, x, ty + 26);
				ctx.fillText(row.v, x, ty + 50);
				ctx.fillStyle = col.muted;
				ctx.fillText(`± ${row.sd}`, x, ty + 68);
				ctx.strokeStyle = col.verify;
				ctx.lineWidth = 2;
				ctx.lineCap = 'round';
				ctx.lineJoin = 'round';
				this.check(x - 7, ty + 96, 14, progress(r));
				ctx.lineWidth = 1;
				ctx.lineCap = 'butt';
			});
			ctx.strokeStyle = col.hair2;
			ctx.beginPath(); ctx.moveTo(L.top, ty + 104); ctx.lineTo(L.bot, ty + 104); ctx.stroke();
			this.font(11, 400);
			ctx.textAlign = 'left';
			ctx.fillStyle = col.muted;
			ctx.fillText(caps(data.caption), L.top, ty + 128);
			ctx.textAlign = 'right';
			ctx.fillStyle = col.verifyInk;
			ctx.fillText(caps(data.table.spec), L.bot, ty + 128);
		}
	}
}

function boot() {
	document.querySelectorAll<HTMLElement>('[data-harness]').forEach((fig) => {
		if (!(fig as any).__rh) (fig as any).__rh = new LiveHarness(fig);
	});
}
boot();
