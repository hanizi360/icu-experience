# -*- coding: utf-8 -*-
"""
experience.py — ICU 众包经验库核心(收集/压缩/合并/重放/统计)
================================================================
目标:让所有用户把「控制某软件某功能」的实跑经验压缩成标准 JSON 汇集,
     在 Git 仓库(Gitee/GitHub)零服务器分发,人人 pull 即得全部经验。

压缩三原则(空间可控的关键):
  1. 剧本只存「动作序列 + 相对坐标(xy_rel 0~1) + 锚点文字 label」,绝存不截图;
  2. 坑只存「症状一句 + 规律一句 + 标签」;
  3. 同 id 新版覆盖 + verified 计数累加;坑按 (tag+symptom) 哈希去重。
     → 一条剧本 ~1.5KB、一条坑 ~200B;1000 条经验 < 3MB,git 毫无压力。

存储布局(仓库根 = 本目录上一级 experience/):
  INDEX.json                    总索引(软件→功能→id→版本/验证计数)
  playbooks/<软件>__<功能>.json  一功能一文件
  pitfalls.json                 通用坑库(K 系列的结构化压缩镜像)

CLI:
  python experience.py list [软件名]                 # 列经验
  python experience.py show <id>                     # 看一条
  python experience.py add-playbook <draft.json>     # 剧本入库(schema 校验+脱敏)
  python experience.py add-pitfall --tag a,b --symptom 症状 --rule 规律 [--fixed 笔记]
  python experience.py merge <贡献包.json>           # 合并他人贡献包(冲突:verified 大者胜)
  python experience.py export [out.json]             # 本地新经验打包成贡献包(提交到仓库)
  python experience.py stats                         # 空间/压缩比统计
  python experience.py replay <id> [--step N]        # 按 xy_rel 重放(confirm 闭环)
  python experience.py sanitize <json>               # 脱敏检查(账号/密码/大额数字)
"""
import argparse, glob, hashlib, json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "experience"))
PB_DIR = os.path.join(ROOT, "playbooks")
INDEX_F = os.path.join(ROOT, "INDEX.json")
PIT_F = os.path.join(ROOT, "pitfalls.json")

SENSITIVE = [
    (re.compile(r"(资金账号|账号|account)\s*[:=：]?\s*\d{5,}"), "<账号已脱敏>"),
    (re.compile(r"(资金|余额|发生金额|成交金额)\s*[:=：]?\s*\d{6,}"), "<金额已脱敏>"),
    (re.compile(r"(密码|password|pwd)\s*[:=：]?\s*\S+", re.I), "<密码已脱敏>"),
    (re.compile(r"\b\d{6,}\b(?=.*(成交|资金|余额))"), "<数字已脱敏>"),
]
REQUIRED_PB = ["id", "software", "func", "steps"]


# ───────────────────────── 基础 ─────────────────────────
def load_json(path, default):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def index():
    return load_json(INDEX_F, {"version": "exp-0.1", "playbooks": {}, "updated": ""})


def sanitize(obj):
    """递归脱敏:命中敏感模式就地替换。返回 (obj, 命中数)"""
    hits = 0
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            obj[k], n = sanitize(v); hits += n
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            obj[i], n = sanitize(v); hits += n
    elif isinstance(obj, str):
        for pat, rep in SENSITIVE:
            obj, n = pat.subn(rep, obj); hits += n
    return obj, hits


def validate_playbook(pb):
    """schema 校验。返回错误列表(空=通过)。核心:坐标必须是 xy_rel 比例,拒绝绝对像素。"""
    errs = []
    for k in REQUIRED_PB:
        if not pb.get(k):
            errs.append(f"缺必填字段 {k}")
    steps = pb.get("steps") or []
    if not steps:
        errs.append("steps 为空")
    for i, s in enumerate(steps):
        if "act" not in s:
            errs.append(f"step{i} 缺 act")
        if "xy_rel" in s:
            x, y = s["xy_rel"]
            if not (0 <= x <= 1 and 0 <= y <= 1):
                errs.append(f"step{i} xy_rel 必须是 0~1 比例(相对窗口),拒绝绝对像素:{s['xy_rel']}")
        if s.get("act") in ("click", "dblclick", "rclick") and "xy_rel" not in s and "label" not in s:
            errs.append(f"step{i} 点击类动作必须有 xy_rel 或 label 锚点")
    if pb.get("software", {}).get("match", "") == "":
        errs.append("software.match 缺失(重放时靠它找窗口)")
    return errs


# ───────────────────────── 命令 ─────────────────────────
def cmd_add_playbook(path):
    pb, hits = sanitize(load_json(path, None))
    if pb is None:
        return print(f"[FAIL] 读不到 {path}")
    errs = validate_playbook(pb)
    if errs:
        return print("[FAIL] schema 未通过:\n  " + "\n  ".join(errs))
    pb.setdefault("verified", {"count": 0, "last": "", "by": ""})
    pb.setdefault("pitfalls", [])
    fname = f"{pb['software']['name']}__{pb['func']}.json".replace("/", "_")
    out = os.path.join(PB_DIR, fname)
    save_json(out, pb)
    idx = index()
    idx["playbooks"][pb["id"]] = {
        "software": pb["software"]["name"], "func": pb["func"], "file": f"playbooks/{fname}",
        "verified": pb["verified"]["count"], "added": time.strftime("%Y-%m-%d"),
    }
    idx["updated"] = time.strftime("%Y-%m-%d %H:%M")
    save_json(INDEX_F, idx)
    size = os.path.getsize(out)
    print(f"[OK] 剧本入库 {out} ({size}B) 脱敏命中 {hits} 处")


def cmd_add_pitfall(a):
    pits = load_json(PIT_F, [])
    sym = a.symptom.strip()
    h = hashlib.md5((a.tag + sym).encode("utf-8")).hexdigest()[:8]
    for p in pits:  # 去重:同 tag+symptom
        if p.get("hash") == h:
            return print(f"[SKIP] 已存在 K{p['id']}({p['symptom'][:24]}…),若规律有更新请直接改 pitfalls.json")
    pid = 1 + max([p["id"] for p in pits], default=0)
    pits.append({"id": pid, "hash": h, "tag": [t.strip() for t in a.tag.split(",")],
                 "symptom": sym, "rule": a.rule.strip(), "fixed": a.fixed or "", "date": time.strftime("%Y-%m-%d")})
    save_json(PIT_F, pits)
    print(f"[OK] 坑 K{pid} 入库,坑库共 {len(pits)} 条")


def cmd_merge(path):
    """合并贡献包:剧本同 id 比 verified,坑按 hash 去重。"""
    pack = load_json(path, None)
    if not pack or "playbooks" not in pack and "pitfalls" not in pack:
        return print("[FAIL] 贡献包格式不对(需含 playbooks/pitfalls)")
    add_n = upd_n = pit_n = 0
    for pb in pack.get("playbooks", []):
        pb, _ = sanitize(pb)
        if validate_playbook(pb):
            continue
        fname = f"{pb['software']['name']}__{pb['func']}.json".replace("/", "_")
        out = os.path.join(PB_DIR, fname)
        old = load_json(out, None)
        if old is None:
            save_json(out, pb); add_n += 1
        else:
            ov, nv = old.get("verified", {}).get("count", 0), pb.get("verified", {}).get("count", 0)
            if nv > ov:
                save_json(out, pb); upd_n += 1
    pits = load_json(PIT_F, [])
    have = {p.get("hash") for p in pits}
    for p in pack.get("pitfalls", []):
        p, _ = sanitize(p)
        h = p.get("hash") or hashlib.md5((",".join(p.get("tag", [])) + p.get("symptom", "")).encode()).hexdigest()[:8]
        if h not in have:
            p["hash"] = h; pits.append(p); pit_n += 1
    save_json(PIT_F, pits)
    idx = index()
    for pb in pack.get("playbooks", []):
        pid = pb.get("id")
        if pid and pid in idx["playbooks"]:
            idx["playbooks"][pid]["verified"] = max(idx["playbooks"][pid].get("verified", 0),
                                                    pb.get("verified", {}).get("count", 0))
    idx["updated"] = time.strftime("%Y-%m-%d %H:%M")
    save_json(INDEX_F, idx)
    print(f"[OK] 合并完成:剧本新增 {add_n} 更新 {upd_n},坑新增 {pit_n}")


def cmd_export(out=None):
    out = out or os.path.join(ROOT, f"contrib_{time.strftime('%Y%m%d_%H%M')}.json")
    idx = index()
    pack = {"schema": "icu-experience-1", "exported": time.strftime("%Y-%m-%d %H:%M"),
            "playbooks": [load_json(os.path.join(ROOT, v["file"]), {}) for v in idx["playbooks"].values()],
            "pitfalls": load_json(PIT_F, [])}
    _, hits = sanitize(pack)
    save_json(out, pack)
    print(f"[OK] 贡献包 → {out}({os.path.getsize(out)}B,脱敏命中 {hits})\n提交方式:贴 Issue 或直接 PR 到仓库 staging 分支")


def cmd_list(sw=None):
    idx = index()
    rows = [(k, v) for k, v in idx["playbooks"].items() if not sw or sw in v["software"]]
    for k, v in sorted(rows):
        print(f"{k:34s} {v['software']:8s} {v['func']:16s} verified={v['verified']}")
    print(f"── 共 {len(rows)} 条剧本")


def cmd_show(pid):
    pb = load_json(os.path.join(ROOT, index()["playbooks"][pid]["file"]), None)
    print(json.dumps(pb, ensure_ascii=False, indent=1))


def cmd_stats():
    idx = index(); pits = load_json(PIT_F, [])
    total = sum(os.path.getsize(os.path.join(ROOT, v["file"])) for v in idx["playbooks"].values() if os.path.exists(os.path.join(ROOT, v["file"])))
    n_pb = len(idx["playbooks"])
    raw_est = n_pb * 200 * 1024  # 若每条存全截图(200KB/张 × 平均步骤数)的保守估计
    print(f"剧本 {n_pb} 条,共 {total:,}B(均 {total // max(n_pb, 1):,}B/条)")
    print(f"坑 {len(pits)} 条")
    print(f"若不压缩(存截图),估算 {raw_est // 1024:,}KB → 实际 {(total + os.path.getsize(PIT_F)) // 1024 or 1}KB,压缩比 ≈ {raw_est // max((total + os.path.getsize(PIT_F)), 1)}:1")


def cmd_replay(pid, step=None, dry=False):
    """按剧本重放。窗口 rect 惰性获取:前置步骤(focus/F12/登录)先执行,交易窗出现后再做坐标类动作。"""
    sys.path.insert(0, HERE)
    import native  # noqa
    pb = load_json(os.path.join(ROOT, index()["playbooks"][pid]["file"]), None)
    if not pb:
        return print("[FAIL] 无此剧本")
    focus_w = pb["software"].get("focus_match") or pb["software"].get("match", "")
    match_w = pb["software"].get("match", "")
    state = {"rect": None}

    def get_rect():
        if state["rect"]:
            return state["rect"]
        w = native.list_windows(match_w)
        wins = w.get("windows") or []
        if not wins:
            return None
        r = wins[0]["rect"]
        state["rect"] = (r[0], r[1], r[2] - r[0], r[3] - r[1])
        return state["rect"]

    def ensure_front():
        for _ in range(3):
            if native.focus(focus_w).get("active_now"):
                return True
            native.window_ctl(focus_w, "min"); time.sleep(0.25)
            native.window_ctl(focus_w, "restore"); time.sleep(0.25)
        return False

    ACT = {"click": native.click, "dblclick": lambda x, y: native.click(x, y, double=True),
           "rclick": lambda x, y: native.click(x, y, button="right")}
    for i, s in enumerate(pb["steps"]):
        if step and i + 1 != int(step):
            continue
        act = s["act"]
        tag = s.get("label", "?")
        if act == "focus":
            print(f"[{i+1}] focus {s.get('match', focus_w)}")
            if not dry:
                if not ensure_front():
                    print("   ⚠️ 前台切换未确认,继续尝试后续步骤")
            time.sleep(0.4)
        elif act == "hotkey":
            print(f"[{i+1}] hotkey {s.get('key')}")
            if not dry: native.hotkey(s["key"])
            time.sleep(1)
        elif act == "key":
            print(f"[{i+1}] key {s.get('key')}")
            if not dry: native.key(s["key"])
            time.sleep(0.5)
        elif act == "wait":
            print(f"[{i+1}] wait {s.get('sec')}s")
            if not dry: time.sleep(float(s.get("sec", 1)))
        elif act in ACT:
            rc = get_rect()
            if rc is None:
                if dry:
                    print(f"[{i+1}] {act} label={tag}(窗口未出现,dry 模式跳过换算)")
                    continue
                return print(f"[FAIL] 目标窗口「{match_w}」未出现——前置步骤(登录?)是否成功?")
            L, T, W, H = rc
            rx, ry = s["xy_rel"]
            x, y = int(L + rx * W), int(T + ry * H)
            print(f"[{i+1}] {act} ({x},{y}) label={tag}")
            if not dry:
                native.move(x, y); time.sleep(0.3)
                ACT[act](x, y)
                time.sleep(float(s.get("wait", 1)))
                print(f"     ⚠️ confirm:截图核对靶心是否在「{tag}」")
        else:
            print(f"[{i+1}] 未知动作 {act}")
    print("replay 完成" + ("(dry 演练)" if dry else ""))
    if not dry:
        print("提示:每步后请按剧本 verify 字段核对产物(如桌面 Table_*.xlsx)")



def main():
    ap = argparse.ArgumentParser(description="ICU 众包经验库")
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("list").add_argument("software", nargs="?", default="")
    p_show = sp.add_parser("show"); p_show.add_argument("id")
    p_addpb = sp.add_parser("add-playbook"); p_addpb.add_argument("file")
    p_addpit = sp.add_parser("add-pitfall")
    p_addpit.add_argument("--tag", required=True); p_addpit.add_argument("--symptom", required=True)
    p_addpit.add_argument("--rule", required=True); p_addpit.add_argument("--fixed", default="")
    p_merge = sp.add_parser("merge"); p_merge.add_argument("file")
    p_exp = sp.add_parser("export"); p_exp.add_argument("out", nargs="?", default="")
    sp.add_parser("stats")
    p_rep = sp.add_parser("replay"); p_rep.add_argument("id"); p_rep.add_argument("--step", default=None)
    p_rep.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    fn = {"list": lambda: cmd_list(a.software), "show": lambda: cmd_show(a.id),
          "add-playbook": lambda: cmd_add_playbook(a.file), "add-pitfall": lambda: cmd_add_pitfall(a),
          "merge": lambda: cmd_merge(a.file), "export": lambda: cmd_export(a.out or None),
          "stats": cmd_stats, "replay": lambda: cmd_replay(a.id, a.step, a.dry)}[a.cmd]
    fn()


if __name__ == "__main__":
    main()
