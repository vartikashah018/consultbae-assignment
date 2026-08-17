import pandas as pd

files = [
    "data/source1_naukri_applicants.csv",
    "data/source2_gig_workers.csv",
    "data/source3_cbnexus_contacts.csv"
]

for file in files:
    print("\n" + "=" * 70)
    print(f"FILE: {file}")
    print("=" * 70)

    df = pd.read_csv(file)

    print("\nShape:")
    print(df.shape)

    print("\nColumns:")
    print(df.columns.tolist())

    print("\nFirst 5 rows:")
    print(df.head())

    print("\nMissing values:")
    print(df.isna().sum())