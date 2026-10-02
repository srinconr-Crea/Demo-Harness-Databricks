# Databricks notebook source

# MAGIC %md
# MAGIC # Create Evaluation Dataset — harness
# MAGIC
# MAGIC Builds an evaluation dataset for the harness agent.
# MAGIC Dataset source: **manual**

# COMMAND ----------

# MAGIC %pip install mlflow>=3.10.0 databricks-agents>=1.9.3
# MAGIC %restart_python

# COMMAND ----------

import os

catalog = os.environ.get("CATALOG", dbutils.widgets.get("catalog") if "dbutils" in dir() else "")
schema = os.environ.get("SCHEMA", dbutils.widgets.get("schema") if "dbutils" in dir() else "")
eval_table = f"{catalog}.{schema}.harness_eval_dataset"

print(f"Target eval table: {eval_table}")

# COMMAND ----------


# MAGIC %md
# MAGIC ## Manual evaluation dataset
# MAGIC
# MAGIC Add your own examples below. Each example should have an `inputs` dict
# MAGIC with a `messages` list, and optionally a `category` for gate filtering.

# COMMAND ----------

import pandas as pd

# TODO: Add examples specific to the harness agent.
eval_examples = [
    {
        "inputs": {"messages": [{"role": "user", "content": "What is Databricks?"}]},
        "ground_truth": "Databricks is a unified analytics platform.",
        "category": "core",
    },
    {
        "inputs": {"messages": [{"role": "user", "content": "How do I create a cluster?"}]},
        "ground_truth": "Navigate to Compute in the workspace sidebar and click Create Cluster.",
        "category": "core",
    },
    # Add more examples here. Use category to control gate filtering in gates.yml:
    #   "core"      — primary use cases, strictest quality bar
    #   "edge_case" — boundary conditions, more lenient tolerance
    #   "safety"    — adversarial inputs for safety testing
]

eval_df = pd.DataFrame(eval_examples)
print(f"Created {len(eval_df)} manual examples")


# COMMAND ----------

# MAGIC %md
# MAGIC ## Save as eval dataset

# COMMAND ----------

eval_df.head()

# COMMAND ----------

spark.createDataFrame(eval_df).write.mode("overwrite").saveAsTable(eval_table)
print(f"Eval dataset saved to {eval_table} with {len(eval_df)} examples")
