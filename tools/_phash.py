# -*- coding: utf-8 -*-
"""
_phash.py — 图片感知指纹（dHash 64bit）工具，ICU 图片匹配兜底的"数字指纹"形态。
用户场景：模板 PNG 文件太大、众包库存不动，把图压成一个数字来记。

原理：图缩到 9x8 灰度 → 相邻像素比大小 → 64 bit → 16 位 hex 字符串。
     匹配 = 比两个指纹差几位（汉明距离），<=10 位视为命中（经验阈值）。
优点：指纹 16 字符（vs PNG 几百 KB）、抗缩放/压缩/轻微亮度变化、比对毫秒级。

用法：
  python _phash.py encode <img.png> [--region l,t,w,h]
      输出图的指纹。--region 从大图裁特征区再取指纹（推荐：锚点特征区，不是全窗）。

  python _phash.py find <img.png> <hash> [--region l,t,w,h] [--scale 0.25,0.5,1.0] [--thresh 10]
      在 img 的指定区域（默认左上 500x400，锚点常在角落）多尺度滑窗，
      报告汉明距离最小的命中位置（区域坐标 + 全图坐标）。

实战链路（剧本 rescue 段）：
  1. 当天全窗截图 → 裁锚点特征区（如媒体库面板标题栏）→ encode 得 16 位指纹，录进剧本
  2. 日后 UI 偏移：新截图 → find 旧指纹 → 锚点新位置 → 按记录的相对偏移重推目标坐标
"""
import sys
import json
import argparse

import numpy as np
from PIL import Image

CELL = 8  # dHash 8x8 = 64bit


def dhash_arr(img):
    """PIL Image -> 64bit int（dHash：右比左亮为1）"""
    g = img.convert("L").resize((CELL + 1, CELL), Image.LANCZOS)
    a = np.asarray(g, dtype=np.int16)
    bits = a[:, :-1] > a[:, 1:]
    v = 0
    for b in bits.flatten():
        v = (v << 1) | int(b)
    return v


def dhash_hex(img):
    return "%016x" % dhash_arr(img)


def hamming(h1, h2):
    return bin(int(h1, 16) ^ int(h2, 16)).count("1")


def crop_region(img, region):
    if not region:
        return img
    l, t, w, h = region
    return img.crop((l, t, l + w, t + h))


def cmd_encode(args):
    img = Image.open(args.img)
    sub = crop_region(img, args.region)
    print(json.dumps({"ok": True, "img": args.img, "region": args.region,
                      "hash": dhash_hex(sub), "size": list(sub.size)},
                     ensure_ascii=False))


def cmd_find(args):
    target = int(args.hash, 16)
    full = Image.open(args.img)
    tpl_w, tpl_h = [int(v) for v in args.size.split(",")]
    region = args.region or [0, 0, min(500, full.width), min(400, full.height)]
    l, t, w, h = region
    search = full.crop((l, t, l + w, t + h))
    best = None
    for scale in args.scale:
        win_w, win_h = max(4, int(tpl_w * scale)), max(3, int(tpl_h * scale))
        if win_w > w or win_h > h:
            continue
        for y in range(0, h - win_h + 1, args.step):
            for x in range(0, w - win_w + 1, args.step):
                win = search.crop((x, y, x + win_w, y + win_h))
                d = hamming(dhash_hex(win), "%016x" % target)
                if best is None or d < best["dist"]:
                    cx = l + x + win_w / 2
                    cy = t + y + win_h / 2
                    best = {"dist": d, "scale": scale,
                            "center": [round(cx), round(cy)]}
                    if d <= args.thresh:
                        break
            else:
                continue
            break
    if best is None:
        print(json.dumps({"ok": False, "error": "搜索区小于窗口"}, ensure_ascii=False))
        return
    best["ok"] = True
    best["thresh"] = args.thresh
    best["hit"] = best["dist"] <= args.thresh
    best["note"] = "hit=距离<=阈值；center=窗口中心全图坐标；命中后到附近用小步长再 find 一次可精化"
    print(json.dumps(best, ensure_ascii=False, indent=1))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("encode")
    e.add_argument("img")
    e.add_argument("--region", default=None)
    e.set_defaults(fn=cmd_encode)

    f = sub.add_parser("find")
    f.add_argument("img")
    f.add_argument("hash")
    f.add_argument("--size", required=True, help="encode 时输出的 size，w,h")
    f.add_argument("--region", default=None)
    f.add_argument("--step", type=int, default=4)
    f.add_argument("--scale", default="1.0")
    f.add_argument("--thresh", type=int, default=10)
    f.set_defaults(fn=cmd_find)

    args = ap.parse_args()
    if getattr(args, "region", None):
        args.region = [int(v) for v in args.region.split(",")]
    if getattr(args, "scale", None) and isinstance(args.scale, str):
        args.scale = [float(v) for v in args.scale.split(",")]
    args.fn(args)


if __name__ == "__main__":
    main()
