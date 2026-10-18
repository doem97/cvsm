// The Noto Sans SC @font-face map as its own stylesheet, linked only by Chinese pages, so English
// pages don't carry ~100 unicode-range rules. The woff2 slices go through the build as hashed
// assets; a page downloads only the slices its text needs.
import css from '@fontsource-variable/noto-sans-sc/wght.css?raw';

const files = import.meta.glob<string>(
	'/node_modules/@fontsource-variable/noto-sans-sc/files/*-wght-normal.woff2',
	{ query: '?url', import: 'default', eager: true },
);
const byName = new Map(Object.entries(files).map(([path, href]) => [path.split('/').pop()!, href]));

export function GET() {
	const out = css.replace(/url\(\.\/files\/([^)]+)\)/g, (m, name: string) => {
		const href = byName.get(name);
		if (!href) throw new Error(`noto-sans-sc: no asset for ${name}`);
		return `url(${href})`;
	});
	return new Response(out, { headers: { 'Content-Type': 'text/css; charset=utf-8' } });
}
