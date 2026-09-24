# -*- coding: utf-8 -*-
"""
UV Mirror Match  v4  —  Maya UV 对称 / 跨模型匹配工具
                        Maya UV symmetry / cross-mesh matching tool

用法 Usage (Script Editor, Python):
    import uv_mirror_match
    uv_mirror_match.show()

界面右上角可切换 中文 / English。
Use the button at the top right to switch the UI between Chinese and English.

中文:
  源模型留空 = 同一个模型左右对称匹配
  设置了源模型 = 从另一个模型取 UV:
    镜像对称     源和目标是左右镜像的两个模型
    相同位置     两个模型在空间里重叠
    相同顶点顺序 拓扑完全一样，姿势/位置可以不同
    + "不同拓扑"  布线不同的模型，投射到源模型表面取 UV
  流程: (可选) 设置源模型 → 选目标 UV / 点 / 面 → 匹配 Match

English:
  Source empty   = match left/right halves of the same mesh
  Source set     = take UVs from another mesh:
    Mirror             source and target are mirrored meshes
    Same Position      meshes overlap in space
    Same Vertex Order  identical topology, pose/position may differ
    + "Different Topology"  different edge flow, UVs sampled from source surface
  Workflow: (optional) Set Source → select target UVs / verts / faces → Match
"""
from __future__ import division, print_function

import cmath
import math
from collections import defaultdict

import maya.cmds as cmds
import maya.api.OpenMaya as om

WIN = "uvMirrorMatchWin"
LANG_VAR = "uvMirrorMatchLang"
_ui = {}

_TXT = {
    # 提示 / messages
    "err_sel": (u"请选择目标的 UV / 顶点 / 面 (组件)，不要选整个物体",
                u"Select target UVs / vertices / faces (components), not the whole object"),
    "err_conv": (u"选择无法转换为 UV", u"Selection can't be converted to UVs"),
    "err_one": (u"目标一次只支持一个模型", u"Target must be a single mesh"),
    "err_nosrc": (u"源模型不存在: %s", u"Source mesh not found: %s"),
    "err_idx_surf": (u"'相同顶点顺序' 不能和 '不同拓扑' 一起用",
                     u"'Same Vertex Order' can't be used with 'Different Topology'"),
    "err_same": (u"同一个模型只能用 '镜像对称' 方式",
                 u"A single mesh only supports 'Mirror' correspondence"),
    "err_nomatch": (u"没找到对应，检查源模型 / 对应方式 / 对称轴 / 空间 / 容差",
                    u"No match found - check source / correspondence / axis / space / tolerance"),
    "found": (u"找到 %d 个对应源组件", u"Found %d matching source components"),
    "matched": (u"已匹配 %d 个 UV", u"Matched %d UVs"),
    "center": (u" (其中 %d 个在跨中线的壳里，沿中线镜像)",
               u" (%d in midline shells, mirrored across the midline)"),
    "miss": (u"，%d 个没找到对应", u", %d had no match"),
    "hist_def": (u"已删除非变形历史 (保留蒙皮/变形器)",
                 u"Deleted non-deformer history (skin/deformers kept)"),
    "hist_all": (u"已删除历史", u"Deleted history"),
    "err_nomesh": (u"没有选中模型", u"No mesh selected"),
    "hist_done": (u"已处理 %d 个模型的历史", u"Cleaned history on %d mesh(es)"),
    "dlg_msg": (u"目标模型有构造历史，直接修改会生成很多 polyTweakUV 节点。\n"
                u"(有蒙皮时只删非变形历史，不会破坏绑定)",
                u"Target mesh has construction history. Editing it directly creates\n"
                u"many polyTweakUV nodes. (Skinned meshes keep their deformers.)"),
    "btn_del": (u"删除历史并继续", u"Delete History & Continue"),
    "btn_cont": (u"直接继续", u"Continue Anyway"),
    "btn_cancel": (u"取消", u"Cancel"),
    "warn_src": (u"先选中源模型", u"Select the source mesh first"),
    # 界面 / UI
    "lang_btn": (u"English", u"中文"),
    "src_hdr": (u"源模型 (留空 = 同一模型左右对称)", u"Source mesh (empty = mirror within the same mesh)"),
    "set_src": (u"设置源模型", u"Set Source"),
    "clear": (u"清除", u"Clear"),
    "corr": (u"对应方式", u"Correspondence"),
    "corr_opts": ((u"镜像对称", u"相同位置", u"相同顶点顺序"),
                  (u"Mirror", u"Same Position", u"Same Vertex Order")),
    "axis": (u"模型对称轴", u"Model Axis"),
    "axis_tip": (u"3D 模型的对称轴 (角色一般是 X)，不是 UV 方向",
                 u"3D mesh symmetry axis (usually X for characters), not a UV direction"),
    "align": (u"UV 对齐", u"UV Align"),
    "align_u": (u"对齐 U 中线 (竖直)", u"Align U Center (vertical)"),
    "align_v": (u"对齐 V 中线 (水平)", u"Align V Center (horizontal)"),
    "align_tip": (u"把选中的 UV 对齐到它们包围框的中线，Match 前先拉直中线用",
                  u"Align selected UVs to their bounding-box center; use to straighten the midline before Match"),
    "err_2uv": (u"至少选择 2 个 UV", u"Select at least 2 UVs"),
    "aligned": (u"已对齐 %d 个 UV", u"Aligned %d UVs"),
    "space": (u"空间", u"Space"),
    "space_opts": ((u"世界", u"物体"), (u"World", u"Object")),
    "space_tip": (u"只对跨模型有效；同一模型总是用物体空间",
                  u"Cross-mesh only; a single mesh always uses object space"),
    "surf": (u"不同拓扑 (投射到源模型表面取 UV)",
             u"Different Topology (sample UVs from source surface)"),
    "tol": (u"容差", u"Tolerance"),
    "tol_tip": (u"相对源模型包围盒大小；找不到对应时调大",
                u"Relative to source bounding box; raise it if matches are missing"),
    "mode": (u"对齐方式", u"Placement"),
    "mode_opts": ((u"整个UV壳", u"仅选择", u"叠到源UV", u"精确镜像"),
                  (u"Fit Shell", u"Fit Selection", u"Overlay", u"Exact Mirror")),
    "mode_tip": (u"精确镜像：形状完全一样，只翻转+平移，不旋转",
                 u"Exact Mirror: identical shape, flip + move only, no rotation"),
    "line": (u"精确镜像时按镜像线放置  U =", u"Exact Mirror: place across mirror line  U ="),
    "flip": (u"U 翻转", u"Flip U"),
    "flip_opts": ((u"自动", u"翻转", u"不翻转"), (u"Auto", u"Flip", u"No Flip")),
    "scale": (u"允许缩放 (关 = 保持源的像素密度)",
              u"Allow Scale (off = keep source texel density)"),
    "btn_hist": (u"删除所选模型历史", u"Delete History on Selected"),
    "btn_check": (u"选择对应源 UV (检查)", u"Select Source UVs (Check)"),
    "btn_match": (u"匹配 Match", u"Match"),
    "btn_transfer": (u"整体传递 UV → 所选模型", u"Transfer All UVs → Selected Mesh"),
    "transfer_tip": (u"选中目标模型 (物体)，把源模型的整套 UV (含接缝) 传过去。"
                     u"两个模型要在所选空间里重叠",
                     u"Select the target mesh (object). Copies the source's full UV layout, "
                     u"seams included. Meshes must overlap in the chosen space"),
    "err_need_src": (u"请先设置源模型", u"Set a source mesh first"),
    "err_sel_mesh": (u"请选中要传递 UV 的目标模型", u"Select the target mesh to transfer UVs to"),
    "err_src_is_tgt": (u"目标和源是同一个模型", u"Target and source are the same mesh"),
    "tr_exact": (u"拓扑相同：已精确复制 UV", u"Same topology: UVs copied exactly"),
    "tr_sample": (u"拓扑不同：已按表面投射传递 UV (%d 个 UV 壳)",
                  u"Different topology: UVs transferred by surface sampling (%d shells)"),
}


def _lang():
    if cmds.optionVar(exists=LANG_VAR):
        return cmds.optionVar(q=LANG_VAR)
    return "zh"


def _t(key):
    zh, en = _TXT[key]
    return en if _lang() == "en" else zh


# --------------------------------------------------------------------------
# 选择
# --------------------------------------------------------------------------
def _shape_path(dp):
    if dp.node().hasFn(om.MFn.kTransform):
        dp.extendToShape()
    return dp


def _get_selection():
    sel = cmds.ls(sl=True, fl=False) or []
    comps = [s for s in sel if "." in s]
    if not comps:
        raise RuntimeError(_t("err_sel"))
    uv_comps = cmds.polyListComponentConversion(comps, toUV=True) or []
    if not uv_comps:
        raise RuntimeError(_t("err_conv"))
    msel = om.MSelectionList()
    for c in uv_comps:
        msel.add(c)
    dag, ids = None, set()
    for i in range(msel.length()):
        dp, comp = msel.getComponent(i)
        dp = _shape_path(dp)
        if dag is None:
            dag = dp
        elif dp.fullPathName() != dag.fullPathName():
            raise RuntimeError(_t("err_one"))
        if not comp.isNull():
            ids.update(om.MFnSingleIndexedComponent(comp).getElements())
    return dag, sorted(ids)


def _dag_from_name(name):
    msel = om.MSelectionList()
    try:
        msel.add(name)
    except RuntimeError:
        raise RuntimeError(_t("err_nosrc") % name)
    return _shape_path(msel.getDagPath(0))


# --------------------------------------------------------------------------
# 模型数据
# --------------------------------------------------------------------------
class MeshData(object):
    def __init__(self, dag, space=om.MSpace.kObject):
        fn = om.MFnMesh(dag)
        self.dag, self.space = dag, space
        self.name = dag.fullPathName()
        self.uv_set = fn.currentUVSetName()

        us, vs = fn.getUVs(self.uv_set)
        self.uv = [complex(u, v) for u, v in zip(us, vs)]

        counts, verts = fn.getVertices()
        counts, verts = list(counts), list(verts)
        self.face_verts, o = [], 0
        for c in counts:
            self.face_verts.append(tuple(verts[o:o + c]))
            o += c

        uv_counts, uv_ids = fn.getAssignedUVs(self.uv_set)
        uv_counts, uv_ids = list(uv_counts), list(uv_ids)
        self.face_uvs, o = [], 0
        for f, c in enumerate(uv_counts):
            self.face_uvs.append(tuple(uv_ids[o:o + c]) if c == counts[f] else None)
            o += c

        self.uv_fv = {}
        for f, fu in enumerate(self.face_uvs):
            if fu is None:
                continue
            for k, u in enumerate(fu):
                self.uv_fv.setdefault(u, (f, k))

        self.face_key = {frozenset(fv): f for f, fv in enumerate(self.face_verts)}
        self.shell_ids = []
        if len(self.uv) and any(fu is not None for fu in self.face_uvs):
            try:
                _, shell_ids = fn.getUvShellsIds(self.uv_set)
                self.shell_ids = list(shell_ids)
            except RuntimeError:
                pass

        self.pts = [(p.x, p.y, p.z) for p in fn.getPoints(space)]
        xs, ys, zs = zip(*self.pts)
        self.diag = math.sqrt((max(xs) - min(xs)) ** 2 +
                              (max(ys) - min(ys)) ** 2 +
                              (max(zs) - min(zs)) ** 2)
        self.grid = None

    def comp(self, i):
        return "%s.map[%d]" % (self.name, i)

    # ---- 空间最近点 ----
    def build_grid(self, tol):
        self.tol = tol
        self.grid = defaultdict(list)
        for i, p in enumerate(self.pts):
            self.grid[self._cell(p)].append(i)

    def _cell(self, p):
        t = self.tol
        return (int(math.floor(p[0] / t)), int(math.floor(p[1] / t)), int(math.floor(p[2] / t)))

    def nearest(self, q):
        cx, cy, cz = self._cell(q)
        best, bd = -1, self.tol * self.tol
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j in self.grid.get((cx + dx, cy + dy, cz + dz), ()):
                        p = self.pts[j]
                        d = (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2
                        if d <= bd:
                            best, bd = j, d
        return best


# --------------------------------------------------------------------------
# 对应关系: 目标 UV -> 源 UV
# --------------------------------------------------------------------------
def _uv_at(S, sf, p):
    """源面 sf 上、点 p 处的 UV (纯 Python 重心插值)
    UV on source face sf at point p (pure-Python barycentric interpolation)"""
    uvs = S.face_uvs[sf]
    if uvs is None:
        return None
    P = [S.pts[v] for v in S.face_verts[sf]]
    U = [S.uv[u] for u in uvs]
    best, best_out = None, None
    for i in range(1, len(P) - 1):
        a, b, c = P[0], P[i], P[i + 1]
        v0 = [b[k] - a[k] for k in range(3)]
        v1 = [c[k] - a[k] for k in range(3)]
        v2 = [p[k] - a[k] for k in range(3)]
        d00 = sum(x * x for x in v0)
        d01 = sum(x * y for x, y in zip(v0, v1))
        d11 = sum(x * x for x in v1)
        d20 = sum(x * y for x, y in zip(v2, v0))
        d21 = sum(x * y for x, y in zip(v2, v1))
        den = d00 * d11 - d01 * d01
        if abs(den) < 1e-20:
            continue
        wb = (d11 * d20 - d01 * d21) / den
        wc = (d00 * d21 - d01 * d20) / den
        wa = 1.0 - wb - wc
        out = -min(wa, wb, wc, 0.0)
        if best_out is None or out < best_out:
            best_out = out
            best = wa * U[0] + wb * U[i] + wc * U[i + 1]
    return best


class Matcher(object):
    """src(t) -> (源UV坐标 source UV coord, 源组件名 source component) 或 or None"""

    def __init__(self, T, S, corr="mirror", axis=0, rel_tol=1e-3, surface=False):
        self.T, self.S, self.corr, self.axis = T, S, corr, axis
        self.same = T.name == S.name
        self.surface = surface and not self.same
        if self.surface:
            if corr == "index":
                raise RuntimeError(_t("err_idx_surf"))
            self.fnS = om.MFnMesh(S.dag)
        elif corr != "index":
            S.build_grid(max(S.diag * rel_tol, 1e-7))
        self._vmap = {}

    def _pos(self, p):
        q = list(p)
        if self.corr == "mirror":
            q[self.axis] = -q[self.axis]
        return q

    def src(self, t):
        return self._src_surface(t) if self.surface else self._src_topo(t)

    # ---- 拓扑一致：按面/顶点精确对应 ----
    def vert(self, v):
        r = self._vmap.get(v)
        if r is not None:
            return r
        if self.corr == "index":
            r = v if v < len(self.S.pts) else -1
        else:
            r = self.S.nearest(self._pos(self.T.pts[v]))
        self._vmap[v] = r
        return r

    def _src_topo(self, t):
        T, S = self.T, self.S
        fv = T.uv_fv.get(t)
        if fv is None:
            return None
        f, k = fv
        mv = [self.vert(v) for v in T.face_verts[f]]
        if -1 in mv:
            return None
        sf = S.face_key.get(frozenset(mv))
        if sf is None or S.face_uvs[sf] is None:
            return None
        try:
            sk = S.face_verts[sf].index(mv[k])
        except ValueError:
            return None
        s = S.face_uvs[sf][sk]
        if self.same and s == t:
            return None
        return S.uv[s], S.comp(s)

    # ---- 不同拓扑：投射到源模型表面取 UV ----
    def _src_surface(self, t):
        T, S = self.T, self.S
        fv = T.uv_fv.get(t)
        if fv is None:
            return None
        f, k = fv
        verts = T.face_verts[f]
        p = T.pts[verts[k]]
        n = len(verts)
        c = [sum(T.pts[v][i] for v in verts) / n for i in range(3)]
        # 往面中心收一点再找源面，UV 接缝两边才不会取错边
        nudge = [p[i] + (c[i] - p[i]) * 0.2 for i in range(3)]
        p, nudge = self._pos(p), self._pos(nudge)

        _, sf = self.fnS.getClosestPoint(om.MPoint(*nudge), S.space)
        z = _uv_at(S, sf, p)
        if z is None:
            return None
        return z, "%s.f[%d]" % (S.name, sf)


def _build(source, corr, axis, rel_tol, space, surface=False):
    tdag, targets = _get_selection()
    if source:
        sdag = _dag_from_name(source)
        same = sdag.fullPathName() == tdag.fullPathName()
    else:
        sdag, same = tdag, True
    if same:
        if corr != "mirror":
            raise RuntimeError(_t("err_same"))
        T = S = MeshData(tdag, om.MSpace.kObject)
    else:
        sp = om.MSpace.kWorld if space == "world" else om.MSpace.kObject
        T, S = MeshData(tdag, sp), MeshData(sdag, sp)
    return T, S, Matcher(T, S, corr, axis, rel_tol, surface), targets


# --------------------------------------------------------------------------
# 2D 相似变换拟合
# --------------------------------------------------------------------------
def _fit(P, Q, allow_scale):
    n = len(P)
    cp, cq = sum(P) / n, sum(Q) / n
    num = sum((q - cq) * (p - cp).conjugate() for p, q in zip(P, Q))
    den = sum(abs(p - cp) ** 2 for p in P)
    a = num / den if (den > 1e-14 and abs(num) > 1e-14) else complex(1, 0)
    if not allow_scale:
        a /= abs(a)
    err = sum(abs(a * (p - cp) + cq - q) ** 2 for p, q in zip(P, Q))
    return a, cp, cq, err


def _flipU(z):
    return complex(-z.real, z.imag)


# --------------------------------------------------------------------------
# 主功能
# --------------------------------------------------------------------------
def select_source(source="", corr="mirror", axis=0, rel_tol=1e-3, space="world",
                  surface=False, **_):
    """选中对应的源 UV，用来检查 / Select the matching source UVs to verify correspondence"""
    T, S, M, targets = _build(source, corr, axis, rel_tol, space, surface)
    comps = set()
    for t in targets:
        r = M.src(t)
        if r is not None:
            comps.add(r[1])
    if not comps:
        raise RuntimeError(_t("err_nomatch"))
    cmds.select(sorted(comps), r=True)
    _msg(_t("found") % len(comps))


def match(source="", corr="mirror", axis=0, rel_tol=1e-3, space="world",
          surface=False, mode="shell", flip="auto", allow_scale=False,
          use_line=False, line_u=0.5):
    T, S, M, targets = _build(source, corr, axis, rel_tol, space, surface)

    pairs = {}   # 目标UV -> 源UV坐标
    for t in targets:
        r = M.src(t)
        if r is not None:
            pairs[t] = r[0]
    miss = len(targets) - len(pairs)
    if not pairs:
        raise RuntimeError(_t("err_nomatch"))

    new = {}
    center_done = 0
    if mode != "overlay" and M.same and corr == "mirror":
        # 跨中线的壳 (躯干/头这类一整块左右对称的壳)：
        # 用壳里中线 UV 算出对称轴，直接沿这条线镜像
        done = _match_center_shells(T, M, pairs, new)
        center_done = len(done)
        for t in done:
            pairs.pop(t, None)
    if not pairs:
        pass
    elif mode == "overlay":
        for t, z in pairs.items():
            new[t] = z
    elif mode == "exact":
        # 精确镜像：形状 100% 一样，不旋转不缩放，只翻转 + 平移
        if flip == "auto":
            fl = (corr == "mirror")
        else:
            fl = (flip == "on")
        P = {t: (_flipU(z) if fl else z) for t, z in pairs.items()}
        if use_line and fl:
            # 按镜像线放置：u' = 2*U0 - u，整体排布左右对称
            for t, z in pairs.items():
                new[t] = complex(2 * line_u - z.real, z.imag)
        else:
            # 保持目标当前大概位置：所有相关壳一起算一个平移，
            # 大壳小壳之间的相对位置和源完全一致
            shells = {T.shell_ids[t] for t in pairs}
            Q, PP = [], []
            for t, sid in enumerate(T.shell_ids):
                if sid in shells:
                    z = P.get(t)
                    if z is None:
                        r = M.src(t)
                        if r is None:
                            continue
                        z = _flipU(r[0]) if fl else r[0]
                    Q.append(T.uv[t])
                    PP.append(z)
            d = sum(Q) / len(Q) - sum(PP) / len(PP)
            for t, z in P.items():
                new[t] = z + d
    else:
        groups = defaultdict(list)
        for t in pairs:
            groups[T.shell_ids[t]].append(t)

        for shell, sel_t in groups.items():
            if mode == "selection" and len(sel_t) >= 3:
                fit_pairs = [(t, pairs[t]) for t in sel_t]
            else:
                # 部分选择时：优先用壳里“没选中”的 UV 来对齐，
                # 这样修过的点能无缝接回没动的部分
                sel_set = set(sel_t)
                all_pairs, rest_pairs = [], []
                for t, sid in enumerate(T.shell_ids):
                    if sid == shell:
                        r = pairs.get(t) or M.src(t)
                        s = r if isinstance(r, complex) else (r[0] if r else None)
                        if s is not None:
                            all_pairs.append((t, s))
                            if t not in sel_set:
                                rest_pairs.append((t, s))
                fit_pairs = rest_pairs if len(rest_pairs) >= 3 else all_pairs
            if len(fit_pairs) < 2:
                continue

            Q = [T.uv[t] for t, _ in fit_pairs]
            SRC = [s for _, s in fit_pairs]
            best = None
            for fl in {"auto": (True, False), "on": (True,), "off": (False,)}[flip]:
                P = [_flipU(z) if fl else z for z in SRC]
                a, cp, cq, err = _fit(P, Q, allow_scale)
                if best is None or err < best[0]:
                    best = (err, fl, a, cp, cq)
            _, fl, a, cp, cq = best

            for t in sel_t:
                z = pairs[t]
                if fl:
                    z = _flipU(z)
                new[t] = a * (z - cp) + cq

    _apply(T, new)
    txt = _t("matched") % len(new)
    if center_done:
        txt += _t("center") % center_done
    if miss:
        txt += _t("miss") % miss
    _msg(txt)


def _match_center_shells(T, M, pairs, new):
    shells = {T.shell_ids[t] for t in pairs}
    centers = defaultdict(list)
    for t, (f, k) in T.uv_fv.items():
        sid = T.shell_ids[t]
        if sid in shells:
            v = T.face_verts[f][k]
            if M.vert(v) == v:          # 顶点在中线上
                centers[sid].append(t)
    done = []
    for sid, cts in centers.items():
        pts = [T.uv[t] for t in cts]
        c = sum(pts) / len(pts)
        w = 1j                           # 默认竖直对称轴
        if len(pts) >= 2:
            s2 = sum((z - c) ** 2 for z in pts)
            if abs(s2) > 1e-12:
                w = cmath.exp(0.5j * cmath.phase(s2))   # 中线方向 (可倾斜)
        ww = w * w
        for t, z in pairs.items():
            if T.shell_ids[t] == sid:
                new[t] = c + ww * (z - c).conjugate()   # 沿中线反射
                done.append(t)
    return done


def align_uvs(direction="u", **_):
    """对齐到包围框中线，等同 UV Toolkit 的 Align U/V Center
    Align to bounding-box center, same as UV Toolkit Align U/V Center"""
    sel = cmds.ls(sl=True) or []
    uvs = cmds.ls(cmds.polyListComponentConversion(sel, toUV=True) or [], fl=True) or []
    if len(uvs) < 2:
        raise RuntimeError(_t("err_2uv"))
    flat = cmds.polyEditUV(uvs, q=True)
    us, vs = flat[0::2], flat[1::2]
    if direction == "u":
        mid = (min(us) + max(us)) / 2.0
    else:
        mid = (min(vs) + max(vs)) / 2.0
    ch = cmds.constructionHistory(q=True, toggle=True)
    cmds.undoInfo(openChunk=True, chunkName="uvMirrorMatchAlign")
    try:
        cmds.constructionHistory(toggle=False)
        for c, u, v in zip(uvs, us, vs):
            if direction == "u":
                cmds.polyEditUV(c, u=mid, v=v, relative=False)
            else:
                cmds.polyEditUV(c, u=u, v=mid, relative=False)
    finally:
        cmds.constructionHistory(toggle=ch)
        cmds.undoInfo(closeChunk=True)
    _msg(_t("aligned") % len(uvs))


def _parent(shape):
    return cmds.listRelatives(shape, parent=True, fullPath=True)[0]


def _src_face_shell(S, sf):
    fu = S.face_uvs[sf]
    return S.shell_ids[fu[0]] if (fu and S.shell_ids) else -1


def _build_uv_temp(T, S):
    """用目标的拓扑新建一个临时模型，UV (含接缝) 按源模型生成
    Create a temp mesh with the target's topology and UVs (seams included) from the source"""
    fnS = om.MFnMesh(S.dag)

    def centroid(f):
        vs = T.face_verts[f]
        return [sum(T.pts[v][i] for v in vs) / len(vs) for i in range(3)]

    # 每个目标面落在源模型的哪个面 / 哪个 UV 壳
    face_src, face_shell, cents = [], [], []
    for f in range(len(T.face_verts)):
        c = centroid(f)
        _, sf = fnS.getClosestPoint(om.MPoint(*c), S.space)
        cents.append(c)
        face_src.append(sf)
        face_shell.append(_src_face_shell(S, sf))

    # 顶点周围的面落在不同壳 → 每个壳一个 UV = 接缝
    key_id, us, vs, counts, ids = {}, [], [], [], []
    for f, verts in enumerate(T.face_verts):
        sh, c = face_shell[f], cents[f]
        counts.append(len(verts))
        for v in verts:
            key = (v, sh)
            uid = key_id.get(key)
            if uid is None:
                p = T.pts[v]
                nudge = [p[i] + (c[i] - p[i]) * 0.2 for i in range(3)]
                _, sf = fnS.getClosestPoint(om.MPoint(*nudge), S.space)
                if _src_face_shell(S, sf) != sh:
                    sf = face_src[f]
                z = _uv_at(S, sf, p)
                if z is None:
                    z = complex(0, 0)
                uid = len(us)
                us.append(z.real)
                vs.append(z.imag)
                key_id[key] = uid
            ids.append(uid)

    connects = [v for fv in T.face_verts for v in fv]
    fn = om.MFnMesh()
    obj = fn.create([om.MPoint(*p) for p in T.pts], counts, connects, us, vs)
    fn.assignUVs(counts, ids)
    temp = om.MDagPath.getAPathTo(obj).fullPathName()
    tshape = cmds.listRelatives(temp, shapes=True, fullPath=True)[0]
    cur = cmds.polyUVSet(tshape, q=True, currentUVSet=True)[0]
    if cur != T.uv_set:
        cmds.polyUVSet(tshape, rename=True, uvSet=cur, newUVSet=T.uv_set)
    n_shells = len({sh for sh in face_shell if sh >= 0})
    return temp, n_shells


def transfer_uvs(source="", space="world", **_):
    """整体传递 UV (含接缝) / Transfer a full UV layout, seams included"""
    if not source:
        raise RuntimeError(_t("err_need_src"))
    objs = cmds.ls(sl=True, o=True, long=True) or []
    if not objs:
        raise RuntimeError(_t("err_sel_mesh"))
    tdag, sdag = _dag_from_name(objs[0]), _dag_from_name(source)
    if tdag.fullPathName() == sdag.fullPathName():
        raise RuntimeError(_t("err_src_is_tgt"))
    sp = om.MSpace.kWorld if space == "world" else om.MSpace.kObject
    T, S = MeshData(tdag, sp), MeshData(sdag, sp)
    same_topo = len(T.pts) == len(S.pts) and T.face_verts == S.face_verts

    temp = None
    if not same_topo:
        temp, n = _build_uv_temp(T, S)
    try:
        cmds.undoInfo(openChunk=True, chunkName="uvMirrorMatchTransfer")
        try:
            if same_topo:
                cmds.polyTransfer(_parent(T.name), uvSets=True,
                                  alternateObject=_parent(S.name))
                txt = _t("tr_exact")
            else:
                cmds.polyTransfer(_parent(T.name), uvSets=True, alternateObject=temp)
                txt = _t("tr_sample") % n
            _delete_history(T.name)
        finally:
            cmds.undoInfo(closeChunk=True)
    finally:
        if temp and cmds.objExists(temp):
            cmds.undoInfo(stateWithoutFlush=False)
            try:
                cmds.delete(temp)
            finally:
                cmds.undoInfo(stateWithoutFlush=True)
    _msg(txt)


def _delete_history(shape):
    """删除历史；有蒙皮时只删非变形历史 / Delete history; keep deformers on skinned meshes"""
    hist = cmds.listHistory(shape, pruneDagObjects=True) or []
    if cmds.ls(hist, type="geometryFilter"):
        cmds.bakePartialHistory(shape, prePostDeformers=True)
        return _t("hist_def")
    tr = cmds.listRelatives(shape, parent=True, fullPath=True)[0]
    cmds.delete(tr, constructionHistory=True)
    return _t("hist_all")


def delete_history_selected(**_):
    objs = cmds.ls(sl=True, o=True, long=True) or []
    shapes = set()
    for o in objs:
        if cmds.nodeType(o) == "mesh":
            shapes.add(o)
        else:
            shapes.update(cmds.listRelatives(o, shapes=True, type="mesh",
                                             noIntermediate=True, fullPath=True) or [])
    if not shapes:
        raise RuntimeError(_t("err_nomesh"))
    for s in shapes:
        _delete_history(s)
    _msg(_t("hist_done") % len(shapes))


def _apply(T, new):
    if not new:
        return
    hist = cmds.listHistory(T.name, pruneDagObjects=True, interestLevel=2) or []
    del_hist = False
    if hist:
        b_del, b_cont, b_can = _t("btn_del"), _t("btn_cont"), _t("btn_cancel")
        r = cmds.confirmDialog(
            title="UV Mirror Match", message=_t("dlg_msg"),
            button=[b_del, b_cont, b_can], defaultButton=b_del,
            cancelButton=b_can, dismissString=b_can)
        if r == b_can:
            return
        del_hist = r == b_del

    ch = cmds.constructionHistory(q=True, toggle=True)
    cmds.undoInfo(openChunk=True, chunkName="uvMirrorMatch")
    try:
        if del_hist:
            print("[UV Mirror Match] " + _delete_history(T.name))
        cmds.constructionHistory(toggle=False)
        for t, z in new.items():
            cmds.polyEditUV(T.comp(t), u=z.real, v=z.imag,
                            relative=False, uvSetName=T.uv_set)
    finally:
        cmds.constructionHistory(toggle=ch)
        cmds.undoInfo(closeChunk=True)


# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------
def _msg(txt):
    print("[UV Mirror Match] " + txt)
    cmds.inViewMessage(amg=txt, pos="topCenter", fade=True)


def _set_source(*_):
    sel = cmds.ls(sl=True, o=True) or []
    if not sel:
        cmds.warning(u"[UV Mirror Match] " + _t("warn_src"))
        return
    dp = _dag_from_name(sel[0])
    tr = cmds.listRelatives(dp.fullPathName(), parent=True, fullPath=True)[0]
    cmds.textField(_ui["src"], e=True, text=tr)


def _clear_source(*_):
    cmds.textField(_ui["src"], e=True, text="")


def _opts():
    rb = lambda k: cmds.radioButtonGrp(_ui[k], q=True, select=True) - 1
    return dict(
        source=cmds.textField(_ui["src"], q=True, text=True).strip(),
        corr=("mirror", "position", "index")[rb("corr")],
        axis=rb("axis"),
        space=("world", "object")[rb("space")],
        rel_tol=cmds.floatFieldGrp(_ui["tol"], q=True, value1=True),
        surface=cmds.checkBox(_ui["surf"], q=True, value=True),
        mode=("shell", "selection", "overlay", "exact")[rb("mode")],
        use_line=cmds.checkBox(_ui["line"], q=True, value=True),
        line_u=cmds.floatField(_ui["lineU"], q=True, value=True),
        flip=("auto", "on", "off")[rb("flip")],
        allow_scale=cmds.checkBox(_ui["scale"], q=True, value=True),
    )


def _run(func):
    try:
        func(**_opts())
    except RuntimeError as e:
        cmds.warning(u"[UV Mirror Match] %s" % e)


def _run_align(direction):
    try:
        align_uvs(direction)
    except RuntimeError as e:
        cmds.warning(u"[UV Mirror Match] %s" % e)


def _set_opts(o):
    cmds.textField(_ui["src"], e=True, text=o["source"])
    sb = lambda k, i: cmds.radioButtonGrp(_ui[k], e=True, select=i + 1)
    sb("corr", ("mirror", "position", "index").index(o["corr"]))
    sb("axis", o["axis"])
    sb("space", ("world", "object").index(o["space"]))
    cmds.floatFieldGrp(_ui["tol"], e=True, value1=o["rel_tol"])
    cmds.checkBox(_ui["surf"], e=True, value=o["surface"])
    sb("mode", ("shell", "selection", "overlay", "exact").index(o["mode"]))
    cmds.checkBox(_ui["line"], e=True, value=o["use_line"])
    cmds.floatField(_ui["lineU"], e=True, value=o["line_u"])
    sb("flip", ("auto", "on", "off").index(o["flip"]))
    cmds.checkBox(_ui["scale"], e=True, value=o["allow_scale"])


def _rebuild(o):
    show()
    try:
        _set_opts(o)
    except Exception:
        pass


def _toggle_lang(*_):
    o = _opts()
    cmds.optionVar(sv=(LANG_VAR, "en" if _lang() == "zh" else "zh"))
    # 不能在按钮自己的回调里删除窗口，会让 Maya 崩溃；等回调结束后再重建
    # Deleting the window inside its own button callback can crash Maya,
    # so rebuild after the callback has finished
    cmds.evalDeferred(lambda: _rebuild(o))


def show():
    if cmds.window(WIN, exists=True):
        cmds.deleteUI(WIN)
    en = _lang() == "en"
    L = 105 if en else 75                      # 标签列宽 / label column width
    cmds.window(WIN, title="UV Mirror Match", widthHeight=(520 if en else 440, 560))
    cmds.columnLayout(adj=True, rowSpacing=6, columnOffset=("both", 8))

    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1)
    cmds.text(label=_t("src_hdr"), align="left")
    cmds.button(label=_t("lang_btn"), width=60, command=_toggle_lang)
    cmds.setParent("..")
    cmds.rowLayout(numberOfColumns=3, adjustableColumn=1)
    _ui["src"] = cmds.textField(text="")
    cmds.button(label=_t("set_src"), command=_set_source)
    cmds.button(label=_t("clear"), command=_clear_source)
    cmds.setParent("..")

    cw4 = (L, 95, 105, 130) if en else (L, 85, 80, 100)
    opt = lambda k: _TXT[k][1] if en else _TXT[k][0]
    _ui["corr"] = cmds.radioButtonGrp(label=_t("corr"), labelArray3=opt("corr_opts"),
                                      numberOfRadioButtons=3, select=1, columnWidth4=cw4)
    _ui["axis"] = cmds.radioButtonGrp(label=_t("axis"), labelArray3=["X", "Y", "Z"],
                                      numberOfRadioButtons=3, select=1, columnWidth4=cw4,
                                      annotation=_t("axis_tip"))
    cmds.rowLayout(numberOfColumns=3, columnWidth3=(L, 150 if en else 120, 150 if en else 120),
                   columnAttach3=("right", "left", "left"), columnOffset3=(4, 4, 4))
    cmds.text(label=_t("align"))
    cmds.button(label=_t("align_u"), annotation=_t("align_tip"), width=145 if en else 115,
                command=lambda *_: _run_align("u"))
    cmds.button(label=_t("align_v"), annotation=_t("align_tip"), width=145 if en else 115,
                command=lambda *_: _run_align("v"))
    cmds.setParent("..")
    _ui["space"] = cmds.radioButtonGrp(label=_t("space"), labelArray2=opt("space_opts"),
                                       numberOfRadioButtons=2, select=1,
                                       columnWidth3=cw4[:3], annotation=_t("space_tip"))
    _ui["surf"] = cmds.checkBox(label=_t("surf"), value=False)
    _ui["tol"] = cmds.floatFieldGrp(label=_t("tol"), value1=0.001, precision=5,
                                    columnWidth2=(L, 80), annotation=_t("tol_tip"))
    cmds.separator(h=6)
    _ui["mode"] = cmds.radioButtonGrp(label=_t("mode"), labelArray4=opt("mode_opts"),
                                      numberOfRadioButtons=4, select=4,
                                      columnWidth5=(L, 85, 100, 75, 100) if en else (L, 80, 65, 80, 80),
                                      annotation=_t("mode_tip"))
    cmds.rowLayout(numberOfColumns=2, columnWidth2=(300 if en else 230, 80))
    _ui["line"] = cmds.checkBox(label=_t("line"), value=False)
    _ui["lineU"] = cmds.floatField(value=0.5, precision=3)
    cmds.setParent("..")
    _ui["flip"] = cmds.radioButtonGrp(label=_t("flip"), labelArray3=opt("flip_opts"),
                                      numberOfRadioButtons=3, select=1, columnWidth4=cw4)
    _ui["scale"] = cmds.checkBox(label=_t("scale"), value=False)
    cmds.separator(h=6)
    cmds.button(label=_t("btn_hist"), command=lambda *_: _run(delete_history_selected))
    cmds.button(label=_t("btn_check"), command=lambda *_: _run(select_source))
    cmds.button(label=_t("btn_match"), height=36, backgroundColor=(0.33, 0.5, 0.36),
                command=lambda *_: _run(match))
    cmds.separator(h=6)
    cmds.button(label=_t("btn_transfer"), height=30, backgroundColor=(0.33, 0.42, 0.55),
                annotation=_t("transfer_tip"), command=lambda *_: _run(transfer_uvs))
    cmds.showWindow(WIN)


if __name__ == "__main__":
    show()
