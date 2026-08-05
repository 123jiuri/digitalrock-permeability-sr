# Reproducibility checklist

Before publishing a run, record:

1. The exact input CSV checksums and the split definition.
2. The descriptor extraction version and descriptor dictionary.
3. Python, PySR, Julia, SymbolicRegression, and PythonCall versions.
4. CPU, memory, thread settings, and whether the run was serial.
5. Seeds, iterations, population settings, operators, loss, precision, and maximum complexity.
6. The complete output directory, including `metadata.json`, `formulas_all.csv`, and `seed_summary.csv`.

The public repository intentionally does not include the CSV files or experimental result directories. Keep those in a separate controlled archive and provide access through the data-availability statement of the paper.
