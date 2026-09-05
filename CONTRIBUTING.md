# 贡献规范
1. 剧本 schema 见 EXPERIENCE.md;xy_rel 必须 0~1 比例(相对软件窗口),锚点文字 label 必填;
2. 提交前跑 `tools/experience.py export`,确认脱敏后无敏感信息;
3. 坑条目(已验证的教训)与剧本分开:坑进 pitfalls.json,操作序列进 playbooks;
4. 重复条目:同 hash 坑自动去重;同 id 剧本按 verified.count 取大;
5. verified 计数规则:你用某条剧本重放成功一次,verified +1 并更新 last 日期。
