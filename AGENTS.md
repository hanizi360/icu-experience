# 总工作台工程说明(项目级入口 · 新会话必读)

> 本文件是 `C:\Users\Cui\WorkBuddy\` 整个工程的**项目总结与冷启动入口**。
> 任何 AI 新会话在本目录工作时,先读完本文件再动手;细节按文中索引按需加载。
> 最后更新:2026-09-06 · 版本 v1.3(版本真相源:`工作台注册表.json`)

## 一、这是什么

个人 A 股指挥台(command center):一个总工作台 + 四个子工作台 + 数据大表 + 自动任务 + 众包经验库。
浏览器访问:**http://127.0.0.1:8765/总工作台.html**(8765 端口 nocache_server.py 开机自启,已加固多线程/超时/日志免疫)。

## 二、体系结构

- 总工作台 `总工作台.html`(504 行):REGISTRY 注册表驱动,iframe 嵌子台;自带 emJsonp 直连东财涨停池/炸板池做首板实时概览;含总览聚合/我的产物/已归档页。
- 子台两种形态:
  - **自包含单文件**:首板工作台(524KB)、板块工作台(112KB)——数据以 `const SNAPSHOT = {...};` 内嵌,改数据必须同步内嵌快照;
  - **壳 + wb.js + 数据JSON**:新闻哨兵、美股监测——壳仅 292B(`<div id="app" data-src="XX数据.json">` + `<script src="../wb.js">`),渲染逻辑全在根目录 `wb.js`(839 行通用渲染器:块渲染/主题/刷新/版本徽章)。
- 子台都在 `workbench/` 下;`工作台注册表.json` = 版本管理唯一真相源(v1.2,changelog 在内)。

## 三、四个子工作台

| 子台 | 功能 | 数据文件 | 数据链/脚本 |
|------|------|---------|------------|
| 首板工作台 | ≥4%候选池/实时选股/连板天梯/题材/**快速买入** | ~~首板数据.json 已废~~ | stock.db 构建注入(`_build_shouban.py`,模板 `_build/首板工作台.模板.html`)+ 东财/腾讯实时直连(页面运行时);「🔄刷新」走 `/api/refresh-shouban`;行内「买」按钮→`/api/em-buy`→唤东财交易窗自动填单(对方最优价+保护价现价×1.015+1/2仓原生按钮),「买入」人工手点(见 PLAYBOOKS 剧本#2) |
| 新闻哨兵工作台 | 全量新闻流水精选(5 板块 25-35 条) | 新闻哨兵数据.json | `A股/news_sentinel_fetch.py`(东财7×24+新浪)→ AI 语义打分;自动任务 8:40 |
| 美股监测工作台 | 29 只美股标的隔夜→A股映射(光模块/存储/设备/AI芯片…) | 美股监测数据.json | `A股/fetch_us_live.py`(东财 push2delay 实时);页面 9/5 被增强(实时行情注入) |
| 板块工作台 | 3涨3跌预测+对账学习闭环+全量496板块信号+**对冲盘温度计**(中信期货IF) | 板块数据.json | `A股/sector_forecast.py` 采原料 → AI 对账+生成预测;温度计 `build_citic_history.py`→`_build_signal.py`→`citic_signal.json`(页面运行时 fetch) |

## 四、数据大表

`C:\Users\Cui\.workbuddy\stockdb\stock.db`:bars 1890 万行(含涨停/一字标志)、stocks 6008、hot_concepts 5644(realtime_theme=每日精选题材)。补数脚本 `A股/import_bars_missing.py`。

## 五、生产脚本链(仅 6 个,其余 A股/ 下 probe/inspect/_ 开头多为历史草稿)

news_sentinel_fetch.py / sector_forecast.py / build_citic_history.py + _build_signal.py / _build_shouban.py / fetch_us_live.py

## 六、自动任务(执行者=WorkBuddy,ZCode 不建 cron)

- 新闻哨兵:每交易日 **8:40**(规则文件 `workbench/新闻哨兵_cron_prompt.txt`)
- 板块预测:每交易日 **15:40**(规则文件 `workbench/板块预测_cron_prompt.txt`,含温度计更新步骤 0b 与对账新口径)
- ⚠️ WorkBuddy 触发不可靠(9/5 全天未跑)。**每日验收**:看各台数据 JSON 的 meta.date;missed 就手动喊跑。
- 自动任务规则文件 ZCode 有永久修改权(改文件即生效);任务实体增删需用户在 WorkBuddy UI 操作。

## 七、众包经验库(已上线 GitHub)

- 仓库:**github.com/hanizi360/icu-experience**(Public);内容=剧本(playbooks)+ 坑库(pitfalls.json, K1-K21)+ 工具(tools/experience.py)+ Actions 校验。
- 本地库:本目录 `skills/i-can-see-you/experience/`;工具 CLI:`experience.py list/show/add-playbook/add-pitfall/merge/export/stats/sync pull/replay`。
- 压缩 28:1:剧本只存动作序列+xy_rel 相对坐标+锚点 label,不存截图;同步走 **api.github.com + token**(存 `C:\Users\Cui\.github_token`,scope=repo+workflow;github.com 主站被网络阻断、ZCode IAB 被沙盒管控——三环境三路径,详见 LOGIC.md K21)。
- 贡献规范/隐私红线见仓库 CONTRIBUTING.md。

## 八、ICU 工具箱(i-can-see-you · 电脑软件连接器)

位置 `skills/i-can-see-you/`。执行内核:`native.py`(零依赖 ctypes:鼠标/键盘[UNICODE 中文]/窗口/剪贴板)、`find.py`(UIA+模板匹配)、`cursor.py`(截图+光标靶心)、`recorder.py`(录制/重放)、`experience.py`(经验库)。
**文档**:`SKILL.md`(入口卡,3.4KB)+ `references/LOGIC.md`(逻辑唯一规格 + K1-K21 踩坑库,**实跑前后必读第 8 节**)+ `PLAYBOOKS.md`(已录剧本)+ FAQ/ARCHITECTURE/FLOWCHART。
**核心纪律**:① move --confirm 看靶心才 click;② 坐标显式参照系(mss 全图图内=native+(3840,1834));③ 卡住先截图取证,禁止无图下结论;④ 两次失败转录制;⑤ 返回值必查;⑥ 踩坑回流。
**第 0 阶段分流**:API/本地数据直连优先,GUI 最后。已覆盖:东财(登录/交割单导出/买股填单/数据下载)、网易云;新软件写新适配层。
**买股填单链**(2026-09-06):`native.focus` 已升级 `_force_foreground`(Alt→AttachThreadInput→SwitchToThisWindow),后台服务进程抢前台必成;交易窗自绘控件 UIA 死路,走窗口相对坐标+键盘;剧本 `eastmoney__quick_buy` + LOGIC K22。

## 九、关键纪律(全部血泪)

1. 数据 JSON = 唯一数据源;自包含台改数据须同步内嵌 SNAPSHOT;不新建按日期文件;不动其他台的文件。
2. 多模型并行开发过本目录:**动手前核对文件 mtime 与 `工作台注册表.json`**(9/5 曾发生温度计被迁走、三个工作台 HTML 被删的事故)。
3. 自动任务归 WorkBuddy;ZCode 只做编程/数据/打分。
4. GUI 操作三铁律:点击前截图确认靶心;连续失败≥2 次先截图取证禁止无图下"不可能"结论;卡住把截图给用户看。
5. WorkBuddy 自动任务规则文件(`*_cron_prompt.txt`)ZCode 有永久修改权;任务实体增删请用户切 WorkBuddy 窗口。

## 十、已知状态与待办

- 美股监测数据停留在 8/11 旧版(9/4 被 WorkBuddy 误删,未恢复),需重建当日数据链;
- 快速买入已上线(候选池/涨停池行内「买」按钮→交易窗自动填单,买入人工手点);**盘中实单验收待用户**(9/6 周日晚仅做了非提交态验证:600000/688170/003040 三链全通);
- WorkBuddy 侧旧 9:25 首板任务(automation-1786331299903)已死待用户在 UI 删除;
- 首板台温度计已迁至板块工作台(用户决定);E:\zcard 首板模板仍在,`_build/` 模板为日常构建用;
- 每交易日 15:40 后检查板块台是否更新(对账+新预测),8:40 后检查新闻哨兵。

## 十一、版本与同步

- 工作台体系:`工作台注册表.json` version(当前 1.2,changelog 三条);改版必登记。
- 经验库:github.com/hanizi360/icu-experience,**定期把本文件(AGENTS.md)同步上传到该仓库根**,随经验版本一起迭代(`experience.py export` + API 上传)。
