// @ts-check
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import starlightLinksValidator from 'starlight-links-validator';

const GITHUB = 'https://github.com/doem97/cvsm';

export default defineConfig({
	site: 'https://doem97.github.io',
	base: '/cvsm',
	integrations: [
		starlight({
			title: 'CVSM',
			description:
				'A state machine protocol for running controlled ML experiments with coding agents. You write the study spec: which variables differ between arms, which are held fixed, and which may adapt.',
			defaultLocale: 'root',
			locales: {
				root: { label: 'English', lang: 'en' },
				'zh-cn': { label: '简体中文', lang: 'zh-CN' },
			},
			sidebar: [
				{ label: 'Start', translations: { 'zh-CN': '开始' }, items: [{ autogenerate: { directory: 'start' } }] },
				{ label: 'Concepts', translations: { 'zh-CN': '概念' }, items: [{ autogenerate: { directory: 'concepts' } }] },
				{ label: 'Guides', translations: { 'zh-CN': '指南' }, items: [{ autogenerate: { directory: 'guides' } }] },
				{ label: 'Reference', translations: { 'zh-CN': '参考' }, items: [{ autogenerate: { directory: 'reference' } }] },
				{ label: 'Project', translations: { 'zh-CN': '项目' }, items: [{ autogenerate: { directory: 'project' } }] },
			],
			social: [{ icon: 'github', label: 'GitHub', href: GITHUB }],
			favicon: '/favicon.svg',
			customCss: ['./src/styles/fonts.css', './src/styles/tokens.css', './src/styles/starlight.css'],
			components: {
				Head: './src/components/starlight/Head.astro',
				SiteTitle: './src/components/starlight/SiteTitle.astro',
			},
			titleDelimiter: '·',
			credits: false,
			// Broken links in the knowledge base fail the build.
			plugins: [starlightLinksValidator()],
		}),
	],
	vite: {
		// Fonts stay files, never data: URIs, so unicode-range slices load only when used.
		build: { assetsInlineLimit: (file) => (file.endsWith('.woff2') ? false : undefined) },
		resolve: {
			alias: [{ find: /^~\//, replacement: fileURLToPath(new URL('./src/', import.meta.url)) }],
		},
	},
});
