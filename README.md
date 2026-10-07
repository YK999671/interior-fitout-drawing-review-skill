# 精装修图纸会审 Skill

面向 Codex 的精装修招标图与开工前图纸会审**预审流程**。输入本地图纸路径，先建立资料清单、审查依据和覆盖矩阵，再按空间与构件核查图纸自洽、跨专业接口、施工与检修条件，输出带图纸依据的问题台账。

本仓库只包含通用 Skill、模板和辅助脚本。**不包含任何项目图纸、审图成果或客户资料。**

## 能做什么

- 从总说明、施工细则、材料说明及用户提供的甲方／公司标准建立审查基线；
- 用 ODA File Converter 与 ezdxf 提取 DWG/DXF 的图层、文字、尺寸、块和几何对象，再建立楼栋、楼层、户型、房间与各专业图纸的对应关系；
- 检查图号和索引、尺寸、材料编号、门与柜体、天花设备、机电点位、深化与施工界面；
- 记录“已检查、抽样、待解析、无法判断”等覆盖状态，不把局部样本称作全量审查；
- 输出问题台账、证据、需设计答复事项和新版复审状态。

审查项详见 [SKILL.md](SKILL.md) 与 [references/interior-fitout-checks.md](references/interior-fitout-checks.md)。

## 安装与使用

将整个仓库目录复制到 Codex 的 skills 目录，并使文件夹名保持为 `interior-fitout-drawing-review`。然后在对话中调用：

```text
使用 $interior-fitout-drawing-review 预审 <本地图纸文件夹路径>。
审查阶段：招标图；请先读取总说明，并列出缺少的甲方和公司标准。
```

建议同时提供项目所在地、审查阶段、甲方／公司标准、合同界面、甲供材清单和特别关注的问题。只给路径也可以先做资料盘点。

## CAD 解析依赖

DWG 解析需要自行安装 [ODA File Converter](https://www.opendesign.com/guestfiles/oda_file_converter)；本仓库不分发 ODA 程序。Python 侧安装：

```bash
python -m pip install -r requirements-cad.txt
```

DXF 可直接由 ezdxf 读取。ODA 检测不到时可用 `--oda-exe` 指定安装路径。解析能力、输出和限制见 [CAD 解析说明](references/cad-parsing.md)。

## 辅助脚本

Python 3.10+。清单、覆盖矩阵、版本比较和问题台账校验仅用标准库；从 XLSX 提取规则候选时需要 `openpyxl`。

```bash
python scripts/inventory_files.py /path/to/drawings -o output/manifest.json
python scripts/parse_cad.py /path/to/drawings -o output/cad --manifest output/manifest.json
python scripts/extract_project_rules.py /path/to/standards -o output/rule-candidates.json
python scripts/build_coverage_matrix.py assets/scope-template.csv -o output/coverage.csv
python scripts/compare_manifests.py output/manifest-old.json output/manifest-new.json
python scripts/validate_issue_register.py output/issues.json
```

`parse_cad.py` 能解析 DWG/DXF 的常见二维对象，但**不自动完成房间识别、外参配准或碰撞检测**。RVT、IFC 和 PDF 仍需其他工具。解析失败或部分解析的文件应进入覆盖报告，不应被视为“未发现问题”。

运行生成的 `output/` 含本地绝对路径、文件名、哈希及可能的项目内容；不要直接提交到公开仓库。

## 结果边界

Skill 输出的是可复核的预审意见。没有统一坐标或标高时，只能提示二维关系和净高风险；没有合同、清单或界面表时，不能替项目各方认定供货、施工责任或漏项。设计变更、工程责任与法定施工图审查仍需相应人员和程序确认。

## 目录

- `SKILL.md`：审查工作流与阶段门；
- `references/`：覆盖、证据、检查项、界面及问题数据结构；
- `assets/`：空白和匿名化示例模板；
- `scripts/`：CAD 解析、清单、规则候选、覆盖矩阵、版本比较和台账校验工具。

## License

MIT。见 [LICENSE](LICENSE)。
