// Types a Session transcript in once it scrolls into view: your words character by character,
// then the agent's report lines one by one. The full text is in the HTML from the start (for
// readers without script, search and screen readers); hidden characters keep their space, so
// nothing moves. Under prefers-reduced-motion the transcript simply stays as it is.

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

function prepare(fig: HTMLElement) {
	fig.querySelectorAll<HTMLElement>('.typed').forEach((el) => {
		const text = el.dataset.text ?? el.textContent ?? '';
		el.dataset.text = text;
		el.textContent = '';
		const on = document.createElement('span');
		on.className = 'on';
		const off = document.createElement('span');
		off.className = 'off';
		off.textContent = text;
		el.append(on, off);
	});
	fig.querySelectorAll('.on').forEach((el) => el.classList.remove('caret'));
	fig.querySelectorAll('.turn, .line').forEach((el) => el.classList.remove('on'));
	fig.classList.add('is-typing');
}

async function play(fig: HTMLElement, token: { stop: boolean }) {
	for (const turn of fig.querySelectorAll<HTMLElement>('.turn')) {
		if (token.stop) return;
		if (turn.classList.contains('turn--you')) {
			const typed = turn.querySelector<HTMLElement>('.typed')!;
			const on = typed.querySelector<HTMLElement>('.on')!;
			const off = typed.querySelector<HTMLElement>('.off')!;
			const chars = Array.from(typed.dataset.text ?? '');
			on.classList.add('caret');
			await wait(260);
			for (let i = 1; i <= chars.length; i++) {
				if (token.stop) return;
				on.textContent = chars.slice(0, i).join('');
				off.textContent = chars.slice(i).join('');
				await wait(24 + Math.random() * 34);
			}
			await wait(220);
			on.classList.remove('caret');
			turn.classList.add('on');
			await wait(240);
		} else {
			turn.classList.add('on');
			await wait(180);
			for (const line of turn.querySelectorAll<HTMLElement>('.line')) {
				if (token.stop) return;
				line.classList.add('on');
				await wait(230);
			}
			await wait(380);
		}
	}
}

document.querySelectorAll<HTMLElement>('[data-session]').forEach((fig) => {
	if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
	const replay = fig.querySelector<HTMLButtonElement>('[data-replay]');
	let token = { stop: false };
	const run = async () => {
		token.stop = true;
		token = { stop: false };
		prepare(fig);
		const mine = token;
		await play(fig, mine);
		if (!mine.stop && replay) replay.hidden = false;
	};
	prepare(fig);
	const io = new IntersectionObserver(
		(entries) => {
			if (entries.some((e) => e.isIntersecting)) {
				io.disconnect();
				run();
			}
		},
		{ threshold: 0.3 },
	);
	io.observe(fig);
	replay?.addEventListener('click', () => {
		replay.hidden = true;
		run();
	});
});
