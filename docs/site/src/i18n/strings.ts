// Every human-facing string of the landing pages and the figure components, in both languages.
// Facts follow AGENTS.md, the skills, .github/scripts and scripts/ at the commit the site builds from.

export type Lang = 'en' | 'zh-cn';

export const GITHUB = 'https://github.com/doem97/cvsm';

export const NAME = {
	en: 'Controlled-Variable State Machine Protocol',
	'zh-cn': '控制变量状态机协议',
};

/** The adoption copy command, as #38 fixes it for the READMEs and the site. */
export const COPY_COMMAND =
	"git -C <cvsm clone> archive HEAD AGENTS.md .agents .claude .codex .github scripts tests ':!.github/workflows/pages.yml' | tar -x -C <your repo>";

const en = {
	htmlLang: 'en',
	meta: {
		title: 'CVSM — Controlled-Variable State Machine Protocol',
		description:
			'A state machine protocol for running controlled ML experiments with coding agents. You write the study spec: which variables differ between arms, which are held fixed, and which may adapt.',
	},
	nav: {
		docs: 'Docs',
		quick: 'Quick start',
		github: 'GitHub',
		langLabel: 'Language',
		other: '中文',
		otherLang: 'zh-CN',
		theme: 'Switch between dark and light theme',
		skip: 'Skip to content',
		status: 'Pre-release',
	},
	gates: [
		{ num: '01', name: 'Publish' },
		{ num: '02', name: 'Merge' },
		{ num: '03', name: 'Budget' },
		{ num: '04', name: 'Conclude' },
	],
	harness: {
		label:
			'Many fine agent trajectories enter from the left, pass through four orange human gates (publish, merge, budget, conclude), grow more ordered at each, and resolve into a study table whose rows are checked against the study spec.',
		table: { arm: 'Arm', n: 'n', metric: 'Top-1', spec: 'Spec' },
		caption: 'Study table · 12 runs',
		legend: { gate: 'Human gate', agent: 'Agent work', verify: 'Checked against the spec' },
	},
	hero: {
		index: '01 — Overview',
		tag: 'CVSM',
		line1: 'Controlled-Variable',
		line2: 'State Machine Protocol',
		desc: 'A state machine protocol for running controlled ML experiments with coding agents. You write the study spec: which variables differ between arms, which are held fixed, and which may adapt. Agents implement and run the study through GitHub issues and pull requests, one state at a time. Every run records its resolved config, and a script checks it against the spec and reports any difference the spec does not allow. You decide at four points: publish, merge, budget and conclude.',
		ctaDocs: 'Read the docs',
		ctaQuick: 'Quick start',
		ctaGithub: 'GitHub',
	},
	problem: {
		index: '02 — Problem',
		aside: 'The spec and the layers below it',
		title: ['Agents change settings', 'that a comparison needs fixed'],
		body: [
			'Coding agents now write the code, launch the runs and post the results of an ML study faster than you can read them.',
			'A learning rate gets changed to fix a crash. An effective batch gets halved to fit memory. Each change is reasonable on its own; together they turn a comparison into a guess. Usually all you see is the agent’s summary.',
		],
		punch: 'The study spec is the one layer you can read in full, so CVSM checks every run against it, from the run’s own record.',
		spec: 'Study #10 · spec',
		layer0: 'Layer 0 · readable by you',
		layers: ['Layer 1 · code', 'Layer 2 · config', 'Layer 3 · launches and runs'],
		drifts: [
			{ key: 'optim.lr', from: '3e-4', to: '1e-4', why: 'to fix a crash' },
			{ key: 'train.effective_batch', from: '256', to: '128', why: 'to fit memory' },
			{ key: 'train.precision', from: 'bf16', to: 'fp16', why: 'never declared' },
		],
		deep: 'Below it: agent work, too deep to read',
	},
	loop: {
		index: '03 — State machine',
		aside: 'Four gates · every step on GitHub',
		title: ['A study is a', 'state machine on GitHub'],
		body: 'A study moves through plan, implement, review, merge, run and analyze, and each step is recorded on GitHub. Each instruction names a target state. The agent keeps going until it reaches that state, a gate or a blocker, and it stops at the four gates even when everything works.',
		hint: 'Hover or focus a gate',
		lanes: [
			{ name: 'Human', note: 'in a session; never clicks on GitHub' },
			{ name: 'Agents', note: 'four skills; Claude Code or Codex' },
			{ name: 'Record', note: 'GitHub and MLflow, written as it happens' },
		],
		phases: ['Plan', 'Implement', 'Review', 'Merge', 'Run', 'Analyze'],
		agents: [
			{ title: 'plan', sub: 'discuss, draft' },
			{ title: 'implement', sub: 'code to a PR' },
			{ title: 'review', sub: 'fresh session' },
			{ title: 'merge.py', sub: 'the only merge', mono: true },
			{ title: 'run', sub: 'launch, check' },
			{ title: 'report', sub: 'three lines' },
		],
		changes: 'changes',
		records: [
			{ head: 'Issues', lines: ['study #10', 'code #11', 'run #12'] },
			{ head: 'Pull request', lines: ['Closes #11', 'guard · test'] },
			{ head: 'Review', lines: ['Verdict: pass', '@ 3f9c2a1'] },
			{ head: 'main', lines: ['squash merge', 'of that head'] },
			{ head: 'MLflow runs', lines: ['cvsm.*  cfg.*', 'artifacts'] },
			{ head: 'Results', lines: ['per-issue table'], verify: ['spec check', 'study table'] },
		],
		blocker: 'Blocker',
		labels: { when: 'When', say: 'You say', rec: 'Recorded' },
		stops: [
			{
				id: 'g1', phase: 0, kind: 'gate', num: '01', name: 'Publish', say: '“publish”',
				when: 'New or changed approved work: publishing a plan; changing a task’s Goal, Scope, Acceptance or Merge, or a study’s Arms, Controlled or Adaptable; changing a protected path.',
				answer: '“publish”, or approve the change',
				rec: 'The parent and its sub-issues, created wave by wave, and a Decision: comment on the parent.',
			},
			{
				id: 'b', phase: 1, kind: 'blocker', num: '', name: 'Blocker', say: '“option 2”',
				when: 'The same failure 3 times in a row, 3 changes verdicts in a row, an ambiguity that would change the deliverable, or a Controlled setting that can’t be met without changing the comparison.',
				answer: 'one of at most 3 options, e.g. “option 2”',
				rec: 'needs-decision and a four-line comment (Blocked:, Evidence:, Options:, Recommend:) when you’re away; then your Decision: comment.',
			},
			{
				id: 'g2', phase: 3, kind: 'gate', num: '02', name: 'Merge', say: '“merge”',
				when: 'A PR is merge-ready: guard and test green and Verdict: pass on the current head. Under Merge: agent the agent merges it itself with merge.py, which refuses protected paths and unreviewed heads.',
				answer: '“merge”, or “merge #15”',
				rec: 'merge.py --human squash-merges that head; the task closes, with a Decision: comment.',
			},
			{
				id: 'g3', phase: 4, kind: 'gate', num: '03', name: 'Budget', say: '“continue”',
				when: 'The next step would exceed the budget in tokens, time or GPU hours.',
				answer: '“continue”, with a new budget if you like',
				rec: 'A Decision: comment with the budget you set.',
			},
			{
				id: 'g4', phase: 5, kind: 'gate', num: '04', name: 'Conclude', say: '“conclude #10”',
				when: 'All of a study’s sub-issues are closed and it awaits analysis.',
				answer: 'your conclusion, e.g. “conclude #10: …”',
				rec: 'The study closes with your conclusion, recorded as a Decision: comment.',
			},
		],
		decision: 'Decision:',
	},
	contract: {
		index: '04 — Spec check',
		aside: 'Study spec and run records',
		title: ['Every run is checked', 'against the study spec'],
		body: 'You approve a study spec at gate 01: the arms, the settings held fixed (each with a reason), and what may adapt. Every run records its resolved config, and the results command checks those records against the spec, right after launch and in every results comment.',
		specTitle: 'Study #10 · spec',
		approved: 'Readable by you · gate 01',
		notes: [
			{ name: 'Arms', note: 'the only differences' },
			{ name: 'Controlled', note: 'held fixed, each with a reason' },
			{ name: 'Adaptable', note: 'may differ, within its rule' },
		],
		records: '6 run records',
		checkTitle: 'spec check',
		checkStatus: 'from the records · 6 runs',
		gloss: [
			'The effective-batch line fails for one run, which took 128.',
			'train.precision differs between runs, although no section declares it.',
			'The values each Adaptable key took, per arm.',
			'',
		],
		listsTitle: 'It lists, as facts',
		lists: [
			'problems of the spec itself: unreadable lines, Controlled lines without a reason, missing sections, keys in several sections',
			'runs where a Controlled line does not hold, or whose config never recorded its key',
			'runs that match no arm, or several',
			'arms missing a value of an in line',
			'keys in no section whose values differ: undeclared differences',
			'arms with no run',
			'the values each Adaptable key took per arm',
		],
		closing: 'CVSM reports what the records show. Whether the runs are still comparable is your call.',
	},
	session: {
		index: '05 — Decisions',
		aside: 'Claude Code or Codex',
		title: ['You decide in a session', 'at four points'],
		body: 'You make decisions only in an agent session, not on GitHub pages. Agents create issues, open PRs, review, merge and close on your instruction, and record each of your decisions on the issue.',
		report: 'Every stop ends with three lines',
		reportLines: ['Done:', 'Waiting for you:', 'Next:'],
		you: 'You',
		agent: 'Agent',
		gate: 'Gate',
		replay: 'Replay',
		transcript: [
			{ who: 'you', say: 'let’s plan this study: does LoRA match full fine-tuning?' },
			{ who: 'agent', lines: ['Discusses the spec with you, then drafts study #10 with code #11 and run #12.'] },
			{ who: 'you', say: 'publish', gate: '01' },
			{ who: 'agent', lines: ['Done: published #10 with #11 and #12; Decision on #10', 'Waiting for you: nothing', 'Next: #11 is ready'] },
			{ who: 'you', say: 'do #11' },
			{ who: 'agent', lines: ['Done: PR #13 is merge-ready, Verdict: pass @ 3f9c2a1', 'Waiting for you: merge PR #13', 'Next: run #12'] },
			{ who: 'you', say: 'merge', gate: '02' },
			{ who: 'agent', lines: ['Done: merged PR #13 with merge.py --human; #11 closed; Decision on #11', 'Waiting for you: nothing', 'Next: run #12'] },
			{ who: 'you', say: 'take #10 to analysis' },
			{ who: 'agent', lines: ['Done: #12 closed with its results and spec check; study table on #10', 'Waiting for you: conclude #10 (gate 04)', 'Next: nothing until you decide'] },
		],
	},
	facts: {
		index: '06 — Contents',
		aside: 'Six numbers',
		title: ['What the protocol', 'consists of'],
		items: [
			{ n: '0', cap: 'services to install' },
			{ n: '80', cap: 'lines of rules, capped by a test' },
			{ n: '4', cap: 'skills of at most 120 lines each' },
			{ n: '4', cap: 'human gates, the only planned stops', accent: true },
			{ n: '1', cap: 'merge path for agents: merge.py' },
			{ n: '2', cap: 'agent CLIs, Claude Code and Codex, with one set of skills' },
		],
	},
	cta: {
		index: '07 — Adopt',
		title: ['Copy the protocol', 'into your repo'],
		body: 'Copy only tracked files, then fill in the Project section of AGENTS.md. An agent in your session can do every step; you decide, and lend an admin account where one is needed.',
		copy: 'Copy',
		copied: 'Copied',
		adopt: 'Adopt CVSM in five steps',
		quick: 'Quick start',
	},
	footer: {
		tagline: 'Controlled-Variable State Machine Protocol',
		license: 'Apache-2.0',
		licenseHref: 'project/license/',
		status: 'Pre-release · built with CVSM',
		docs: 'Docs',
		github: 'GitHub',
	},
	links: {
		docs: 'start/overview/',
		quick: 'start/quick-start/',
		adopt: 'guides/adopt/',
		loop: 'concepts/gates-and-blockers/',
		spec: 'concepts/study-spec/',
		session: 'start/talk-dont-click/',
		readMore: 'Read more',
	},
};

type Strings = typeof en;

const zh: Strings = {
	htmlLang: 'zh-CN',
	meta: {
		title: 'CVSM — 控制变量状态机协议',
		description:
			'用编码 agent 跑控制变量实验的状态机协议。你写研究规格：各组之间改变哪些变量、固定哪些变量、哪些可以调整。',
	},
	nav: {
		docs: '文档',
		quick: '快速开始',
		github: 'GitHub',
		langLabel: '语言',
		other: 'English',
		otherLang: 'en',
		theme: '切换深色和浅色主题',
		skip: '跳到正文',
		status: '预发布',
	},
	gates: [
		{ num: '01', name: '发布' },
		{ num: '02', name: '合并' },
		{ num: '03', name: '预算' },
		{ num: '04', name: '下结论' },
	],
	harness: {
		label:
			'许多细密的 agent 轨迹从左侧进入，穿过四个橙色的人的关口（发布、合并、预算、下结论），每过一关就更有序，最后汇成一张按研究规格逐行核对过的研究总表。',
		table: { arm: 'Arm', n: 'n', metric: 'Top-1', spec: '规格' },
		caption: '研究总表 · 12 个 run',
		legend: { gate: '人的关口', agent: 'agent 的工作', verify: '按规格核对过' },
	},
	hero: {
		index: '01 — 概述',
		tag: 'CVSM',
		line1: '控制变量',
		line2: '状态机协议',
		desc: '用编码 agent 跑控制变量实验的状态机协议。你写研究规格：各组之间改变哪些变量、固定哪些变量、哪些可以调整。agent 在 GitHub 的 issue 和 PR 上按状态机一步步实现和运行实验。每个 run 都记下实际生效的完整配置，由脚本对照规格核对，规格不允许的差异都会报出来。你只在四处做决定：发布、合并、预算、下结论。',
		ctaDocs: '阅读文档',
		ctaQuick: '快速开始',
		ctaGithub: 'GitHub',
	},
	problem: {
		index: '02 — 问题',
		aside: '规格和它以下的各层',
		title: ['agent 会改动', '对比需要固定的设置'],
		body: [
			'编码 agent 写代码、启动运行、贴出结果的速度，已经快过人能读完的速度。',
			'为了修一次崩溃改了学习率，为了塞进显存把有效 batch 减半。每一处单看都合理，合在一起，对比就成了猜测。而你通常只看到 agent 的总结。',
		],
		punch: '研究规格是你能完整读懂的那一层，所以 CVSM 按每个 run 自己的记录，对照规格核对。',
		spec: '研究 #10 · 规格',
		layer0: '第 0 层 · 你读得懂',
		layers: ['第 1 层 · 代码', '第 2 层 · 配置', '第 3 层 · 启动与运行'],
		drifts: [
			{ key: 'optim.lr', from: '3e-4', to: '1e-4', why: '为了修崩溃' },
			{ key: 'train.effective_batch', from: '256', to: '128', why: '为了塞进显存' },
			{ key: 'train.precision', from: 'bf16', to: 'fp16', why: '从没声明过' },
		],
		deep: '规格以下：agent 的工作，深到读不完',
	},
	loop: {
		index: '03 — 状态机',
		aside: '四个关口 · 每一步都在 GitHub 上',
		title: ['研究是', 'GitHub 上的状态机'],
		body: '研究依次经过计划、实现、审查、合并、运行、分析，每一步都记在 GitHub 上。每条指令就是一个目标状态。agent 一直推进，到达目标状态、碰到关口或遇到卡点时才停；一切顺利也要在四个关口停下。',
		hint: '把鼠标移到关口上，或用 Tab 聚焦',
		lanes: [
			{ name: '人', note: '在会话里；不点 GitHub 页面' },
			{ name: 'Agent', note: '四个 skill；Claude Code 或 Codex' },
			{ name: '记录', note: 'GitHub 和 MLflow，随做随记' },
		],
		phases: ['计划', '实现', '审查', '合并', '运行', '分析'],
		agents: [
			{ title: 'plan', sub: '讨论、起草' },
			{ title: 'implement', sub: '写代码到 PR' },
			{ title: 'review', sub: '新会话审查' },
			{ title: 'merge.py', sub: '唯一的合并入口', mono: true },
			{ title: 'run', sub: '启动、核对' },
			{ title: 'report', sub: '三行汇报' },
		],
		changes: 'changes',
		records: [
			{ head: 'Issue', lines: ['study #10', 'code #11', 'run #12'] },
			{ head: 'PR', lines: ['Closes #11', 'guard · test'] },
			{ head: '审查', lines: ['Verdict: pass', '@ 3f9c2a1'] },
			{ head: 'main', lines: ['squash 合并', '就是那个 head'] },
			{ head: 'MLflow run', lines: ['cvsm.*  cfg.*', 'artifacts'] },
			{ head: '结果', lines: ['单个 issue 的表'], verify: ['规格核对', '研究总表'] },
		],
		blocker: '卡点',
		labels: { when: '什么时候', say: '你说', rec: '记下什么' },
		stops: [
			{
				id: 'g1', phase: 0, kind: 'gate', num: '01', name: '发布', say: '“发布”',
				when: '新增或改变已批准的工作：发布计划；改任务的 Goal、Scope、Acceptance 或 Merge，或研究的 Arms、Controlled、Adaptable；改受保护路径。',
				answer: '“发布”，或批准这处改动',
				rec: '按波次建好的父 issue 和子 issue，以及父 issue 上的一条 Decision: 评论。',
			},
			{
				id: 'b', phase: 1, kind: 'blocker', num: '', name: '卡点', say: '“选 2”',
				when: '同一个失败连续 3 次；审查连续 3 次给出 changes；目标有歧义且会影响交付物；某个 Controlled 设置不改变对比就满足不了。',
				answer: '最多 3 个选项里的一个，例如“选 2”',
				rec: '你不在时：needs-decision 标签和一条四行评论（Blocked:、Evidence:、Options:、Recommend:）；你答复后记一条 Decision:。',
			},
			{
				id: 'g2', phase: 3, kind: 'gate', num: '02', name: '合并', say: '“合并”',
				when: 'PR 待合并：guard 和 test 全绿，当前 head 有 Verdict: pass。任务写了 Merge: agent 时，agent 自己用 merge.py 合并；碰了受保护路径或没审查过的 head，merge.py 会拒绝。',
				answer: '“合并”，或“合并 #15”',
				rec: 'merge.py --human squash 合并那个 head；任务随之关闭，并记一条 Decision: 评论。',
			},
			{
				id: 'g3', phase: 4, kind: 'gate', num: '03', name: '预算', say: '“继续”',
				when: '下一步会超出预算：token、时间或 GPU 小时。',
				answer: '“继续”，也可以给个新预算',
				rec: '一条写明新预算的 Decision: 评论。',
			},
			{
				id: 'g4', phase: 5, kind: 'gate', num: '04', name: '下结论', say: '“#10 下结论”',
				when: '研究的子 issue 全部关闭，进入待分析。',
				answer: '你的结论，例如“#10 下结论：……”',
				rec: '研究带着你的结论关闭，结论记成一条 Decision: 评论。',
			},
		],
		decision: 'Decision:',
	},
	contract: {
		index: '04 — 规格核对',
		aside: '研究规格与运行记录',
		title: ['每个 run 都', '对照研究规格核对'],
		body: '你在关口 01 批准研究规格：各组（arm）之间的不同、固定不变的设置（各带理由）、可以调整的设置。每个 run 都记下解析后的配置，结果命令拿这些记录对照规格核对：启动后马上核一次，每条结果评论里再核一次。',
		specTitle: '研究 #10 · 规格',
		approved: '你读得懂 · 关口 01',
		notes: [
			{ name: 'Arms', note: '各组之间仅有的不同' },
			{ name: 'Controlled', note: '固定不变，各带理由' },
			{ name: 'Adaptable', note: '可以不同，守住各自的规则' },
		],
		records: '6 条运行记录',
		checkTitle: '规格核对',
		checkStatus: '来自记录 · 6 个 run',
		gloss: ['', '', '', ''],
		listsTitle: '它按事实列出',
		lists: [
			'规格本身的问题：读不懂的行、没写理由的 Controlled 行、缺少的节、出现在多节的键',
			'不满足某条 Controlled 的 run，或配置里没记录这个键的 run（未记录）',
			'不属于任何 arm、或属于多个 arm 的 run',
			'缺了某条 in 中某些取值的 arm',
			'不在任何一节、取值却不同的键（未声明的差异）',
			'没有 run 的 arm',
			'每个 Adaptable 键在各 arm 取过的值',
		],
		closing: 'CVSM 只报告记录里有什么。这些 run 还能不能比，由你判断。',
	},
	session: {
		index: '05 — 决定',
		aside: 'Claude Code 或 Codex',
		title: ['你在会话里', '做四个决定'],
		body: '你只在 agent 会话里做决定，不在 GitHub 页面上操作。建 issue、开 PR、审查、合并、关闭都由 agent 按你的指示执行，你的每个决定都记在相应的 issue 上。',
		report: '每次停下，都汇报三行',
		reportLines: ['Done:', 'Waiting for you:', 'Next:'],
		you: '你',
		agent: 'Agent',
		gate: '关口',
		replay: '重放',
		transcript: [
			{ who: 'you', say: '我们计划一个研究：LoRA 能不能追上全量微调？' },
			{ who: 'agent', lines: ['和你讨论规格，然后起草研究 #10，以及代码任务 #11 和运行任务 #12。'] },
			{ who: 'you', say: '发布', gate: '01' },
			{ who: 'agent', lines: ['Done: 已发布 #10 及 #11、#12；Decision 记在 #10', 'Waiting for you: 无', 'Next: #11 已就绪'] },
			{ who: 'you', say: '做 #11' },
			{ who: 'agent', lines: ['Done: PR #13 待合并，Verdict: pass @ 3f9c2a1', 'Waiting for you: 合并 PR #13', 'Next: 运行 #12'] },
			{ who: 'you', say: '合并', gate: '02' },
			{ who: 'agent', lines: ['Done: 用 merge.py --human 合并了 PR #13；#11 已关闭；Decision 记在 #11', 'Waiting for you: 无', 'Next: 运行 #12'] },
			{ who: 'you', say: '把 #10 推到待分析' },
			{ who: 'agent', lines: ['Done: #12 已关闭，附结果和规格核对；研究总表贴在 #10', 'Waiting for you: #10 下结论（关口 04）', 'Next: 等你决定'] },
		],
	},
	facts: {
		index: '06 — 组成',
		aside: '六个数字',
		title: ['协议由', '什么组成'],
		items: [
			{ n: '0', cap: '个要安装的服务' },
			{ n: '80', cap: '行规则，有测试卡住上限' },
			{ n: '4', cap: '个 skill，每个最多 120 行' },
			{ n: '4', cap: '个人的关口，是仅有的计划内停点', accent: true },
			{ n: '1', cap: '个 agent 的合并入口：merge.py' },
			{ n: '2', cap: '种 agent 命令行工具（Claude Code 和 Codex）共用一套 skill' },
		],
	},
	cta: {
		index: '07 — 接入',
		title: ['把协议复制进', '你的仓库'],
		body: '只复制被跟踪的文件，再填好 AGENTS.md 的 Project 一节。每一步都可以交给会话里的 agent 去做；你只需要拍板，并在需要时提供管理员账号。',
		copy: '复制',
		copied: '已复制',
		adopt: '五步接入 CVSM',
		quick: '快速开始',
	},
	footer: {
		tagline: '控制变量状态机协议',
		license: 'Apache-2.0',
		licenseHref: 'zh-cn/project/license/',
		status: '预发布 · 用 CVSM 开发',
		docs: '文档',
		github: 'GitHub',
	},
	links: {
		docs: 'zh-cn/start/overview/',
		quick: 'zh-cn/start/quick-start/',
		adopt: 'zh-cn/guides/adopt/',
		loop: 'zh-cn/concepts/gates-and-blockers/',
		spec: 'zh-cn/concepts/study-spec/',
		session: 'zh-cn/start/talk-dont-click/',
		readMore: '继续阅读',
	},
};

export const STRINGS: Record<Lang, Strings> = { en, 'zh-cn': zh };

export function t(lang: Lang | undefined): Strings {
	return STRINGS[lang === 'zh-cn' ? 'zh-cn' : 'en'];
}

/** A site-internal URL under the configured base, e.g. url('start/overview/'). */
export function url(path = ''): string {
	const base = import.meta.env.BASE_URL.replace(/\/?$/, '/');
	return base + path.replace(/^\//, '');
}

/** The spec of the running example, as README and results.py show it; reasons in the page's language. */
export function specLines(lang: Lang): Array<{ kind: 'h' | 'kv'; text: string; note?: string }> {
	const zh = lang === 'zh-cn';
	return [
		{ kind: 'h', text: '### Arms' },
		{ kind: 'kv', text: 'full: model.adapter=none' },
		{ kind: 'kv', text: 'lora: model.adapter=lora model.lora.rank=8' },
		{ kind: 'h', text: '### Controlled' },
		{ kind: 'kv', text: 'optim.lr=3e-4', note: zh ? '# 论文 X 表 2' : '# paper X, Table 2' },
		{ kind: 'kv', text: 'train.effective_batch=256', note: zh ? '# 论文 X 表 2' : '# paper X, Table 2' },
		{ kind: 'kv', text: 'seed in 1,2,3', note: zh ? '# 同论文 X，用 3 个 seed' : '# three seeds, as in paper X' },
		{ kind: 'h', text: '### Adaptable' },
		{ kind: 'kv', text: 'train.per_device_batch', note: zh ? '# 按显存调整，有效 batch 固定为 256' : '# fit to GPU memory; effective batch stays 256' },
		{ kind: 'kv', text: 'train.accum', note: zh ? '# 跟随 per_device_batch' : '# follows per_device_batch' },
	];
}

/** results.py's 规格核对 for six toy runs of that spec (README, verbatim; run id shortened). */
export const CHECK_LINES = [
	{ mark: '≠', text: '`train.effective_batch=256` 不成立：1 个 run，0330bc8a…（128）' },
	{ mark: '≠', text: '未声明的差异 `train.precision`：bf16（5 个 run）、fp16（1 个 run）' },
	{ mark: '·', text: 'Adaptable `train.per_device_batch`：full 取 64（3 个 run）；lora 取 64（2 个 run）、32（1 个 run）' },
	{ mark: '·', text: 'Adaptable `train.accum`：full 取 4（3 个 run）；lora 取 4（3 个 run）' },
];
