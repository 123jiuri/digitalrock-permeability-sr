# 数字岩石渗透率：逐岩样留出符号回归

本仓库使用 PySR 从砂岩孔隙结构描述符中搜索渗透率方程，采用逐岩样留出
（LOPO）评价。仓库包含主要搜索流程、配置和测试代码。输入数据单独准备，
数据与运行结果保存在本地。

[English](README.md) · [输入格式](docs/input_schema.md) · [复现说明](docs/reproducibility.md)

## 实验流程

默认配置使用 10 块建模砂岩、20 个描述符，每折运行 12 个随机种子，共 120 个搜索任务。

1. 每折留出一块岩样，其余九块训练。
2. 平衡训练岩样的子体积数量，各种子共享训练表。
3. 用训练表确定预处理：正值取 log10，Euler 密度采用带尺度参数的 asinh 变换。
4. 用加、减、乘、除搜索，保留完整 Pareto 前沿。
5. 在留出岩样上评价候选式，汇总方程族、描述符频次和任务覆盖率。

## 安装

参考环境为 Python 3.13.13、PySR 1.5.10 和 Julia 1.12.6。
Python 依赖见 `pyproject.toml`，Julia 配置见[复现说明](docs/reproducibility.md)。
在使用参考 Python 版本的环境中安装：

```bash
python -m pip install -e ".[sr]"
```

## 输入数据

准备包含建模砂岩子体积的 CSV，列包括 `Filename`、`rock_name`、`lithology`、
`permeability` 和 20 个描述符。渗透率单位为 m²，描述符单位和质量检查规则见
[输入格式](docs/input_schema.md)。独立测试岩样单独存放。

## 运行

检查输入并生成各折共享的训练表：

```bash
python scripts/run_symbolic_regression.py --input-csv /path/to/discovery.csv --output-dir results/sandstone_lopo --dry-run
```

启动搜索：

```bash
python scripts/run_symbolic_regression.py --input-csv /path/to/discovery.csv --output-dir results/sandstone_lopo --workers 8
```

`--workers` 控制并行任务数，每个 PySR 任务内部串行运行。默认配置
`configs/sandstone_lopo.json` 使用 500 次迭代、最大复杂度 15、30 个种群，
每个种群包含 50 个表达式，简约性系数为 0.001。

重复同一命令可继续未完成的任务。输入、配置、代码或环境改变时，使用新的输出目录。
Windows 下建议采用较短的输出路径，方便保存 Julia/PySR 检查点。

## 输出

每次运行保存配置与环境信息、各折共享训练表、PySR 原始文件、完整 Pareto 记录
和折外评价指标。全部任务完成后，生成描述符频次和方程族汇总。运行生成的文件由 Git 忽略。

重新汇总可用 `scripts/analyze_formula_families.py`，命令见[英文说明](README.md#outputs)。

## 测试

```bash
python -m unittest discover -s tests -v
```

测试使用合成输入，检查岩样分组、共享抽样、预处理、Pareto 记录保留、断点续跑
和结果汇总，运行时无需研究数据或 Julia。

## 引用与许可

Cranmer, M. (2023). *Interpretable machine learning for science with PySR and
SymbolicRegression.jl*. https://doi.org/10.48550/arXiv.2305.01582

代码采用 [MIT 许可](LICENSE)。
