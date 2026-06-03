import pandas as pd
import os
import numpy as np


class TrafficCollectorAgent:

    def __init__(self, dataset_path, selected_columns=None, combined_file="combined_dataset.csv"):
        self.dataset_path = dataset_path
        self.selected_columns = selected_columns
        self.combined_file = combined_file

    def collect(self):

        if os.path.exists(self.combined_file):
            print("Loading pre-combined dataset...")
            df = pd.read_csv(self.combined_file)
        else:

            dataframes = []

            files = [
                os.path.join(self.dataset_path, file)
                for file in os.listdir(self.dataset_path)
                if file.endswith(".csv")
            ]

            print(f"Found {len(files)} CSV files")

            for file in files:
                try:
                    if os.path.getsize(file) > 0:
                        df_temp = pd.read_csv(file, encoding="latin1", low_memory=False)
                        dataframes.append(df_temp)
                    else:
                        print(f"Skipped empty file: {file}")

                except Exception as e:
                    print(f"Error loading {file}: {e}")

            if not dataframes:
                raise ValueError("No valid CSV files found.")

            df = pd.concat(dataframes, ignore_index=True)

            print("Saving combined dataset...")
            df.to_csv(self.combined_file, index=False)

        cleaned_df = self.clean_data(df)
        cleaned_df = self.engineer_features(cleaned_df)

        if self.selected_columns:
            cleaned_df = cleaned_df[self.selected_columns]

        return cleaned_df

    def clean_data(self, df):

        df = df.copy()

        df.columns = df.columns.str.strip()

        df.replace([np.inf, -np.inf], np.nan, inplace=True)

        df.dropna(inplace=True)

        df.drop_duplicates(inplace=True)

        if "Flow Duration" in df.columns:
            df = df[df["Flow Duration"] > 0]

        if "Label" in df.columns:

            df.loc[:, "Label"] = df["Label"].astype(str).str.strip()

            df.loc[:, "Label"] = df["Label"].replace({
                "BENIGN": "Normal",
                "Benign": "Normal",
                "Web Attack ï¿½ Brute Force": "Web Attack",
                "Web Attack ï¿½ XSS": "Web Attack",
                "Web Attack ï¿½ Sql Injection": "Web Attack"
            })

        df.reset_index(drop=True, inplace=True)

        return df

    def engineer_features(self, df):

        df = df.copy()

        df["Average Packet Size"] = df.get("Total Length of Fwd Packets", 0) / (df.get("Total Fwd Packets", 0) + 1)

        df["Packet Size Variance"] = (
            df["Average Packet Size"]
            .rolling(window=3, min_periods=1)
            .var()
            .fillna(0)
        )

        df["Average IAT"] = df.get("Flow IAT Mean", 0)

        df["SYN Flag Count"] = df.get("SYN Flag Count", 0)
        df["ACK Flag Count"] = df.get("ACK Flag Count", 0)
        df["FIN Flag Count"] = df.get("FIN Flag Count", 0)
        df["RST Flag Count"] = df.get("RST Flag Count", 0)

        df["Fwd_Bwd_Ratio"] = df["Total Fwd Packets"] / (df["Total Backward Packets"] + 1)
        df["Bytes_per_packet"] = df["Flow Bytes/s"] / (df["Flow Packets/s"] + 1)
        df["SYN_ACK_Ratio"] = df["SYN Flag Count"] / (df["ACK Flag Count"] + 1)

        # Convert to binary: Normal = 0, Attack = 1
        if "Label" in df.columns:
            df["Label"] = df["Label"].apply(lambda x: 0 if x == "Normal" else 1)

        return df