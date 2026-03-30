import pandas as pd
import re

# load dataset
df = pd.read_csv("data/train.csv")

#cleaning steps and extracting columns we need

# View the cleaned dataset
df.to_csv("cleaned.csv", index=False)
