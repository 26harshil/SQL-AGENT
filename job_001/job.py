import pandas as pd

input_file = INPUT_DIR / "extracted_data.csv"
output_file = OUTPUT_DIR / "transformed_data.csv"

# Read the input CSV
df = pd.read_csv(input_file)

# Remove duplicate rows
df = df.drop_duplicates()

# Clean column names
df.columns = df.columns.str.strip()

# Clean the name column if it exists
if "name" in df.columns:
    df["name"] = df["name"].astype(str).str.strip()

# Only create new_column if some_column actually exists
if "some_column" in df.columns:
    df["new_column"] = df["some_column"] * 2
else:
    print("Column 'some_column' does not exist. Skipping new_column creation.")

# Save the transformed CSV
df.to_csv(output_file, index=False)

print("Transformation completed.")