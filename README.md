# UV Mirror Match v4

Maya UV 对称 / 跨模型匹配 / UV 传递工具
Maya UV symmetry, cross-mesh matching & UV transfer tool

[中文](#中文) | [English](#english)

---

## 中文

### 这是什么

两个主要功能：

1. **匹配 Match**：先把一侧的 UV 整理好，再选中另一侧，点一下就会复制过来，并按需要镜像。它可以代替以前「删掉一半模型 → 展 UV → Mirror 几何体 → 手动翻转、挪开 UV」的流程，而且不用删模型，顶点顺序、蒙皮、Blendshape 都不受影响。
2. **整体传递 UV**：把一个模型的整套 UV，包括接缝，传到另一个重合的模型上。两个模型完全一样或者只是相似都可以。

### 安装

1. 把 `uv_mirror_match.py` 放进 `文档/maya/scripts/`
2. 在 Script Editor 的 Python 标签里运行：

```python
import uv_mirror_match
uv_mirror_match.show()
```

更新文件后，用下面的代码重新加载：

```python
import importlib, uv_mirror_match
importlib.reload(uv_mirror_match)
uv_mirror_match.show()
```

面板右上角的按钮可以切换中文和英文，下次打开会记住上次的选择。

### 该用哪个功能？

| 情况 | 用什么 |
|---|---|
| 同一个模型，左右两侧 UV 要对称 | 匹配 Match |
| 躯干、头部这类跨中线的壳，左右两半要对称 | 匹配 Match |
| 只调整了几个点，想同步到另一侧 | 匹配 Match |
| 两个模型重合，一个有 UV，另一个没有或者 UV 是乱的 | **整体传递 UV** |
| 传递之后个别地方想微调 | 匹配 Match |

简单来说：**目标已经有合适的 UV 壳和接缝，用 Match；目标还没有，用整体传递。**

### 匹配 Match

**核心概念：你选中的就是目标（Target）。** 工具会自动找到对应的源（Source），把源的 UV 形状复制过来，**只修改你选中的点**。

如果选错了边，整理好的那一侧会被改乱，按一次 Ctrl+Z 就能恢复。不确定的时候，先点「选择对应源 UV（检查）」看看。

**1. 左右手臂、左右腿**
1. 整理好一侧的 UV
2. 源模型栏留空，对应方式选「镜像对称」，模型对称轴选 X
3. 选中另一侧的 UV 壳（如果有大小两块，比如手掌加拇指，都要选上）
4. 对齐方式选「精确镜像」，点 Match

**2. 跨中线的壳：躯干、头部**
1. 选中中线那一列 UV，点「对齐 U 中线」把它们拉直
2. 选中还没整理的那半边，点 Match
3. 工具会自动识别跨中线的壳，沿中线镜像

**3. 只修几个点**
只选目标一侧对应的那几个点去 Match。工具会参考壳里没选中的点来定位，修好的点能无缝接回去。

**4. 跨模型**
先选中源模型，点「设置源模型」，然后选择对应方式：两个模型是左右镜像的，选「镜像对称」；在空间里重叠的，选「相同位置」；拓扑一样但姿势不同的，选「相同顶点顺序」。如果布线不同，再勾选「不同拓扑」。

### 整体传递 UV

1. 让两个模型**重合**
2. 选中有 UV 的模型，点「设置源模型」
3. 选中新模型（选物体就行）
4. 点蓝色的「**整体传递 UV → 所选模型**」

工具会自动判断：
- **完全一样的模型**：精确复制，UV 一模一样。
- **相似但布线不同的模型**：先看新模型的每个面落在源模型的哪个 UV 壳里，在壳和壳的交界处切出接缝，再从源模型表面取出每个点的 UV。结果会尽量贴近源模型。

完成后会自动删除历史，整个过程可以一次 Ctrl+Z 撤销。

### 面板说明

| 选项 | 说明 |
|---|---|
| 源模型 | 留空表示同一个模型左右对称；设置后从另一个模型取 UV |
| 对应方式 | 镜像对称 / 相同位置 / 相同顶点顺序（只用于 Match） |
| 模型对称轴 | 3D 模型的左右对称轴，不是 UV 方向。角色一般是 X |
| UV 对齐 | 对齐 U 中线 / 对齐 V 中线，效果和 UV Toolkit 一样 |
| 空间 | 跨模型时使用。transform 不同但形状重合时，改成「物体」 |
| 不同拓扑 | Match 跨模型、布线不同时勾选 |
| 容差 | 按源模型包围盒大小的比例计算。出现「没找到对应」时调大，比如 0.005 |
| 对齐方式 · 精确镜像 | **推荐。** 形状完全一样，只做翻转和平移，不旋转 |
| 对齐方式 · 整个UV壳 | 按目标壳当前的角度摆放，会旋转 |
| 对齐方式 · 仅选择 | 只根据选中的点来计算摆放位置 |
| 对齐方式 · 叠到源UV | 直接叠在源 UV 上，适合左右共用同一块贴图 |
| 按镜像线放置 U = | 精确镜像时，放到以这条线为轴的对称位置 |
| U 翻转 | 自动：镜像关系会翻转，其他不翻转 |
| 允许缩放 | 默认关闭，保持和源一样的像素密度 |
| 删除所选模型历史 | 有蒙皮的模型只删非变形历史，不会破坏绑定 |

### 小提示

- **测试新功能前先存档。**
- Match 时如果模型有构造历史，会弹窗询问。建议选「删除历史并继续」，否则会生成很多 polyTweakUV 节点。
- 精确镜像最好在 Maya 的 Layout **之后**做，否则再跑 Layout 会打乱对称的排布。
- 如果「选择对应源 UV」什么都没选中，按这个顺序检查：对应方式 → 空间 → 容差 → 两个模型有没有对齐。

### 限制

- 同一个模型内 Match 时，要求 3D 顶点位置左右对称。
- 布线不同时（「不同拓扑」和整体传递），结果是插值出来的，只能非常接近，做不到 100% 一样。接缝会落在最靠近源接缝的边上，可能会有一点锯齿。
- 整体传递只能识别把壳完全分开的接缝。如果某个接缝只切开了一半（比如壳内部的一道切口），那里的 UV 可能会有些拉伸。
- 一次只能处理一个目标模型。

### 更新记录

- **v4**：新增「整体传递 UV」（含接缝）；新增 U/V 中线对齐；中英双语界面；删除历史整合进工具；修复语言切换和 Match 时的崩溃问题
- **v3**：跨模型匹配、不同拓扑、跨中线的壳、精确镜像
- **v1**：同一模型左右对称匹配

---

## English

### What it does

Two main features:

1. **Match**: Clean up the UVs on one side, select the other side, and click Match. The clean side gets copied over and mirrored as needed. It replaces the old "delete half the mesh → unwrap → Mirror geometry → flip and move the UVs by hand" workflow, without deleting anything, so vertex order, skinning, and blendshapes stay intact.
2. **Transfer All UVs**: Copies a full UV layout, seams included, from one mesh to another mesh that overlaps it. The meshes can be identical or just similar.

### Install

1. Put `uv_mirror_match.py` in `Documents/maya/scripts/`
2. Run this in the Script Editor (Python tab):

```python
import uv_mirror_match
uv_mirror_match.show()
```

After updating the file, reload with:

```python
import importlib, uv_mirror_match
importlib.reload(uv_mirror_match)
uv_mirror_match.show()
```

Use the button at the top right to switch between Chinese and English. The tool remembers your choice.

### Which feature should I use?

| Situation | Use |
|---|---|
| Make left/right UVs symmetric on the same mesh | Match |
| Make both halves of a midline shell (torso, head) symmetric | Match |
| Sync a few tweaked points to the other side | Match |
| Two overlapping meshes, one has UVs and the other has none or messy ones | **Transfer All UVs** |
| Touch up a few spots after a transfer | Match |

In short: **if the target already has proper shells and seams, use Match. If it doesn't, use Transfer.**

### Match

**Key idea: what you select is the target.** The tool finds the matching source automatically, copies the source UV layout, and **only moves the points you selected**.

If you select the wrong side, the clean UVs get overwritten. One Ctrl+Z brings them back. When in doubt, click "Select Source UVs (Check)" first.

**1. Left/right arms or legs**
1. Clean up the UVs on one side
2. Leave Source empty, set Correspondence to Mirror and Model Axis to X
3. Select the UV shells on the other side (if there's a big shell and a small one, like palm + thumb, select both)
4. Set Placement to Exact Mirror and click Match

**2. Midline shells: torso, head**
1. Select the column of midline UVs and click "Align U Center" to straighten them
2. Select the half that isn't cleaned up yet and click Match
3. The tool detects midline shells automatically and mirrors across the midline

**3. Fixing just a few points**
Select only the matching points on the target side and click Match. The tool positions them using the unselected points in the shell, so the fixed points blend right back in.

**4. Cross-mesh**
Select the source mesh and click "Set Source", then choose a correspondence: Mirror for mirrored meshes, Same Position for meshes that overlap, Same Vertex Order for identical topology in a different pose. If the edge flow differs, also check "Different Topology".

### Transfer All UVs

1. Make sure the two meshes **overlap**
2. Select the mesh that has UVs and click "Set Source"
3. Select the new mesh (the object)
4. Click the blue "**Transfer All UVs → Selected Mesh**" button

The tool works out which case you have:
- **Identical meshes**: UVs are copied exactly.
- **Similar meshes with different topology**: It checks which source UV shell each face of the new mesh lands on, cuts seams where shells meet, then samples each point's UV from the source surface. The result stays as close to the source as possible.

History is deleted automatically afterward, and one Ctrl+Z undoes the whole thing.

### Panel reference

| Option | What it does |
|---|---|
| Source mesh | Empty means mirror within the same mesh. Set it to take UVs from another mesh |
| Correspondence | Mirror / Same Position / Same Vertex Order (Match only) |
| Model Axis | The 3D mesh's symmetry axis, not a UV direction. Usually X for characters |
| UV Align | Align U Center / Align V Center, same as the UV Toolkit |
| Space | For cross-mesh work. Switch to Object if the transforms differ but the shapes overlap |
| Different Topology | Check this for cross-mesh Match when the edge flow differs |
| Tolerance | A fraction of the source bounding box size. Raise it (e.g. 0.005) if you get "no match" |
| Placement · Exact Mirror | **Recommended.** Identical shape, flip + move only, no rotation |
| Placement · Fit Shell | Fits to the target shell's current angle, so it may rotate |
| Placement · Fit Selection | Fits using only the selected points |
| Placement · Overlay | Stacks directly on the source UVs, for mirrored textures that share texture space |
| Mirror line U = | With Exact Mirror, places the result symmetrically across this line |
| Flip U | Auto flips for mirror correspondence and doesn't flip otherwise |
| Allow Scale | Off by default, which keeps the same texel density as the source |
| Delete History on Selected | On skinned meshes, only non-deformer history is removed, so the rig stays intact |

### Tips

- **Save your scene before trying new features.**
- If the mesh has construction history, Match asks what to do. "Delete History & Continue" is recommended, because otherwise lots of polyTweakUV nodes get created.
- Do Exact Mirror **after** Maya's Layout. Running Layout again afterward will break the symmetric arrangement.
- If "Select Source UVs" selects nothing, check in this order: correspondence → space → tolerance → whether the meshes actually line up.

### Limitations

- Same-mesh Match needs the vertices to be symmetric in 3D.
- With different topology (Different Topology mode and Transfer), results are interpolated, so they're very close but not 100% identical. Seams land on the edges closest to the source seams and can look a little jagged.
- Transfer only detects seams that fully separate shells. A seam that only partly cuts into a shell (like a slit inside a shell) may cause some stretching there.
- One target mesh at a time.

### Changelog

- **v4**: Added Transfer All UVs (seams included); added U/V center align; bilingual UI; history deletion built in; fixed crashes when switching language and during Match
- **v3**: Cross-mesh matching, different topology, midline shells, Exact Mirror
- **v1**: Left/right symmetric matching on the same mesh
