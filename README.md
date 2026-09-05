# icu-experience · ICU 众包经验库

**i-can-see-you(ICU · 电脑软件连接器)** 的社区经验库:把「控制某软件某功能」的实跑剧本压缩成 JSON 汇集,人人 pull 即得全部经验,人人皆可贡献。

- 压缩:剧本只存「动作序列+相对坐标+锚点文字」,一条 ~1.5KB;坑一条 ~200B。不存截图。
- 工具:`tools/experience.py`(list/show/add-playbook/add-pitfall/merge/export/stats/replay)
- 格式:见 `EXPERIENCE.md`(schema/压缩原则/隐私红线)

## 贡献(两条路)
1. 会 git:改/加 JSON → PR 到 staging;
2. 不会 git:用工具 `export` 生成贡献包 JSON → 贴到 Issue,机器人自动校验入库。

**隐私红线**:贡献内容禁止账号/密码/真实姓名/资金数字,工具入库前强制脱敏。

## 版本
staging 持续收集 → 审阅合并 main → 打 tag `exp-vX.Y` → Release 挂打包 zip。`sync pull` 即更新本地。
