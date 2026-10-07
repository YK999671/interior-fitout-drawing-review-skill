# DWG/DXF 解析链

## 环境依赖

`scripts/parse_cad.py` 使用 [ezdxf](https://ezdxf.readthedocs.io/en/stable/) 读取 DXF。DWG 由用户自行安装的 [ODA File Converter](https://www.opendesign.com/guestfiles/oda_file_converter) 转成 DXF；仓库不分发 ODA 可执行文件。安装 Python 依赖：`python -m pip install -r requirements-cad.txt`。

脚本按顺序寻找 `--oda-exe`、环境变量 `ODA_FILE_CONVERTER`、PATH 和 Windows 常见 ODA 安装目录。找不到 ODA 时，DXF 仍可解析，DWG 标为 `converter_unavailable`。不应自动下载或替用户接受安装协议。

## 调用

```bash
python scripts/inventory_files.py /path/to/drawings -o /path/to/output/manifest.json
python scripts/parse_cad.py /path/to/drawings -o /path/to/cad-output --manifest /path/to/output/manifest.json
```

需要时显式传入 `--oda-exe /path/to/ODAFileConverter`；`--max-entities 0` 取消默认每图 250000 个对象的 JSON 上限。输出目录必须在源图纸目录之外。源 DWG/DXF 开始和结束都计算哈希；转换时 `audit=False`，不会对源图执行修复写入。

每张图输出独立的 `drawing.json`。索引 `cad-parse-index.json` 记录转换状态、错误、对象数量和警告；传入清单后另写 `manifest-with-cad-status.json`，不覆盖原清单。DWG 转换后的 DXF 保留在输出目录，便于复核。

## 能读取与不能推断的内容

读取布局、图层、文字/多行文字、尺寸原文及测量值、块插入与属性、块定义、线、圆弧、多段线、填充和部分引线。每条对象记录句柄、图层、容器及可用坐标。块定义坐标为块内局部坐标；INSERT 记录插入点、旋转和比例，但脚本不自动展开所有嵌套块。尺寸测量值是图纸单位，不代表已校验标注文本或现场尺寸。

外部参照只列名称和路径，不保证文件已加载、可见或完成坐标变换。代理对象、缺字体、图像参照、复杂动态块、视口裁剪、三维实体以及 PDF/RVT/IFC 均需其他工具和人工图面核对。解析成功不等于房间识别、跨图配准、净高校验或完整碰撞检查完成。

状态：`parsed`、`partial`、`parse_failed`、`converter_unavailable`、`source_changed`。存在外参、代理对象或对象上限截断时用 `partial`；报告不能把这些位置写成“已全量检查”。
