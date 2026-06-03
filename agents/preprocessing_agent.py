from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib
import os
import numpy as np


class PreprocessingAgent:

    def __init__(self, model_dir="models"):
        self.model_dir = model_dir
        os.makedirs(self.model_dir, exist_ok=True)

    def process(self, df):

        X = df.drop("Label", axis=1)
        y = df["Label"]

        print("Training features used:")
        print(list(X.columns))
        print("Number of features:", len(X.columns))

        joblib.dump(list(X.columns), "models/feature_names.pkl")

        # No LabelEncoder needed — labels are already 0 and 1
        joblib.dump([0, 1], os.path.join(self.model_dir, "label_encoder.pkl"))

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        joblib.dump(scaler, os.path.join(self.model_dir, "scaler.pkl"))

        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled,
            y.values,
            test_size=0.2,
            random_state=42,
            stratify=y.values
        )

        print(f"Training samples: {len(X_train)}")
        print(f"Testing samples: {len(X_test)}")

        unique, counts = np.unique(y_train, return_counts=True)
        class_counts = dict(zip(unique, counts))
        print("Binary class distribution:", class_counts)

        # Compute class weights
        total = len(y_train)
        n_classes = 2
        class_weight_dict = {
            cls: total / (n_classes * count)
            for cls, count in class_counts.items()
        }
        print("Class weights:", class_weight_dict)

        joblib.dump(class_weight_dict, os.path.join(self.model_dir, "class_weights.pkl"))

        return X_train, X_test, y_train, y_test, class_weight_dict