// Expressive Code for Starlight: two monochrome themes in the site's ink and paper palette.
// Syntax is told apart by weight and tone, not hue; colour stays reserved for gates and checks.
import { defineEcConfig, ExpressiveCodeTheme } from '@astrojs/starlight/expressive-code';

function theme(name, type, c) {
	return new ExpressiveCodeTheme({
		name,
		type,
		colors: {
			'editor.background': c.surface,
			'editor.foreground': c.text,
			'titleBar.activeBackground': c.surface,
			'titleBar.activeForeground': c.muted,
			'titleBar.border': c.hair,
			'editorGroupHeader.tabsBackground': c.bg,
			'editorGroupHeader.tabsBorder': c.hair,
			'tab.activeBackground': c.surface,
			'tab.activeForeground': c.text,
			'tab.activeBorderTop': c.text,
			'terminal.background': c.surface,
			'terminal.foreground': c.text,
			'scrollbarSlider.background': c.hair,
			'editor.selectionBackground': c.hair,
		},
		settings: [
			{ settings: { foreground: c.text, background: c.surface } },
			{ scope: ['comment', 'punctuation.definition.comment'], settings: { foreground: c.muted, fontStyle: 'italic' } },
			{ scope: ['string', 'string.quoted', 'markup.inline.raw'], settings: { foreground: c.soft } },
			{ scope: ['constant.numeric', 'constant.language', 'constant.other'], settings: { foreground: c.soft } },
			{ scope: ['keyword', 'storage', 'storage.type', 'keyword.operator.word'], settings: { foreground: c.text, fontStyle: 'bold' } },
			{ scope: ['entity.name.function', 'support.function', 'entity.name.tag', 'markup.heading'], settings: { foreground: c.text, fontStyle: 'bold' } },
			{ scope: ['variable.parameter', 'variable.other', 'entity.other.attribute-name', 'support.type.property-name'], settings: { foreground: c.text } },
			{ scope: ['punctuation', 'keyword.operator', 'meta.brace'], settings: { foreground: c.muted } },
			{ scope: ['markup.inserted'], settings: { foreground: c.text } },
			{ scope: ['markup.deleted'], settings: { foreground: c.muted } },
		],
	});
}

export default defineEcConfig({
	themes: [
		theme('cvsm-dark', 'dark', { bg: '#0B0C0F', surface: '#121419', hair: '#262930', text: '#F2F2F0', soft: '#C9CBCE', muted: '#9BA0A8' }),
		theme('cvsm-light', 'light', { bg: '#F7F6F2', surface: '#FFFFFF', hair: '#E3E2DD', text: '#0B0C0F', soft: '#33363C', muted: '#5F646C' }),
	],
	useStarlightUiThemeColors: false,
	styleOverrides: {
		borderRadius: '0',
		borderColor: 'var(--cvsm-hair)',
		codeFontFamily: 'var(--cvsm-font-mono)',
		uiFontFamily: 'var(--cvsm-font-mono)',
		codeFontSize: '0.8125rem',
		codeLineHeight: '1.7',
		frames: {
			shadowColor: 'transparent',
			frameBoxShadowCssValue: 'none',
			editorTabBarBackground: 'var(--cvsm-bg)',
			editorActiveTabBackground: 'var(--cvsm-surface)',
			editorActiveTabIndicatorTopColor: 'var(--cvsm-text)',
			editorBackground: 'var(--cvsm-surface)',
			terminalBackground: 'var(--cvsm-surface)',
			terminalTitlebarBackground: 'var(--cvsm-surface)',
			terminalTitlebarBorderBottomColor: 'var(--cvsm-hair)',
			terminalTitlebarDotsForeground: 'var(--cvsm-hair-2)',
			inlineButtonForeground: 'var(--cvsm-muted)',
			inlineButtonBorder: 'var(--cvsm-hair-2)',
			tooltipSuccessBackground: 'var(--cvsm-verify)',
		},
	},
});
