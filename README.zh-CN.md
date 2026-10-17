# 砂岩逐岩样留出符号回归

本仓库仅整理砂岩主符号回归的 LOPO 流程：10块建模岩样、20个候选描述符、
12个搜索种子，共120个“留出岩样×种子”任务。不包含数据、公式结果、图件或论文。
碳酸盐岩、独立测试、置换、消融、受控维数、机器学习基线和描述符提取均不纳入本版。

## 运行协议

每折完整留出一个岩样，其余九个岩样生成一张平衡训练表，该折12个种子共享。
抽样严格沿用原实现：较小岩样有放回抽到训练岩样最大子块数，最大岩样无放回打乱。
该过程平衡各岩样的记录数；不保证较小岩样的每条原始记录都被抽到。

预处理只使用该折平衡训练表。19个正值描述符及渗透率使用log10变换；有正负号的
Euler密度使用训练数据确定的asinh变换。搜索只用训练损失，保留完整Pareto前沿，
结束后再计算完整留出岩样上的指标。折外指标可用于开发阶段的方程族比较，不能将
这一过程称为选定结构之后的独立检验。

## 环境与入口

使用项目既有的 Porosity-permeability 环境，不升级锁定依赖。环境版本、参数和
命令详见[英文说明](README.md)。所有入口均可用该环境的Python直接运行，无需安装
本仓库本身。代码不要求安装PoreSpy、OpenPNM或机器学习基线依赖。

```text
scripts/prepare_discovery_input.py   可选：合并已有train/internal_test数值表与元数据
scripts/run_symbolic_regression.py   主LOPO入口：检查、运行、恢复、汇总
scripts/analyze_formula_families.py  完整任务结束后的代数汇总
configs/sandstone_lopo.json         正式10折×12种子搜索配置
src/digitalrock_sr/                 数据校验、预处理、搜索与汇总实现
tests/test_lopo.py                  不含真实数据的单元测试
```

先自行准备包含岩样ID、子块ID、渗透率和20个描述符的CSV，参见
[输入说明](docs/input_schema.md)。只允许建模砂岩；独立砂岩和其他岩性会被拒绝。
本阶段不重新提取描述符，也不自动恢复源数据的物理单位。

```bash
python scripts/run_symbolic_regression.py --input-csv /path/to/discovery.csv --output-dir results/sandstone_lopo --dry-run
python scripts/run_symbolic_regression.py --input-csv /path/to/discovery.csv --output-dir results/sandstone_lopo --workers 8
python -m unittest discover -s tests -v
```

第一条命令不会导入PySR或启动Julia。第二条才运行搜索，完整任务较耗时，不属于快速
安装测试。重复相同命令可以恢复；输入、配置、代码或环境变化时必须使用新输出目录。
所有数据与运行输出留在本地，Git忽略规则不是数据发布许可。

## 公式与统计

输出公式的变量名指变换后的输入，响应为log10(k/m²)。只有对数线性关系才能直接
反变换为幂律；非线性关系应保留实际反变换，不能直接改标为原变量公式。

描述符出现频次按全部Pareto记录计算，每个描述符在每条记录中最多计一次；另行计算
任务覆盖率。方程族汇总仅作搜索后的代数整理，不预设物理分组，也不替作者选定最终
方程。当前整理版不声称逐位复现旧运行的方程条数或精度。

旧入口及其说明可从Git历史提交40690cb恢复。本轮只更新代码仓库；本地研究资料、
正式结果和原始脚本不被覆盖。后续补充数据时，应另行确定数据仓库、许可和公开范围。
