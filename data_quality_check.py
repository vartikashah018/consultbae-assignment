import pandas as pd


files = {
    "naukri": "data/source1_naukri_applicants.csv",
    "gig_workers": "data/source2_gig_workers.csv",
    "cbnexus": "data/source3_cbnexus_contacts.csv",
}


for source, file in files.items():

    print("\n" + "=" * 80)
    print(f"{source.upper()}")
    print("=" * 80)

    df = pd.read_csv(file)

    # Completely empty rows
    empty_rows = df[df.isna().all(axis=1)]

    print("\nCompletely empty rows:")
    print(empty_rows)

    # Duplicate rows
    duplicates = df[df.duplicated(keep=False)]

    print("\nDuplicate rows:")
    print(duplicates)

    # Find the name column
    name_column = None

    for column in ["Full Name", "worker_name", "Name"]:
        if column in df.columns:
            name_column = column
            break

    # Repeated names
    if name_column:
        print(f"\nRepeated values in {name_column}:")

        repeated = df[
            df[name_column].duplicated(keep=False)
        ].sort_values(name_column)

        print(repeated.to_string(index=False))

    # Check emails
    email_column = None

    if "Email" in df.columns:
        email_column = "Email"

    elif "email_id" in df.columns:
        email_column = "email_id"

    if email_column:
        print(f"\nPotentially invalid emails in {email_column}:")

        invalid = df[
            ~df[email_column]
            .astype(str)
            .str.contains("@", na=False)
        ]

        print(invalid.to_string(index=False))

    # Check phone formats
    for column in ["Phone", "Phone Number"]:

        if column in df.columns:

            print(f"\nPhone values in {column}:")

            print(
                df[column]
                .astype(str)
                .to_string(index=False)
            )