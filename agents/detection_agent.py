from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import (
    classification_report, confusion_matrix,
    accuracy_score, roc_auc_score, f1_score
)
import joblib
import os
import numpy as np


class DetectionAgent:

    def __init__(self, model_dir="models"):
        self.model_dir = model_dir
        os.makedirs(self.model_dir, exist_ok=True)

    def train(self, X_train, y_train, class_weight_dict=None):

        cw = class_weight_dict if class_weight_dict else "balanced"

        self.rf_model = RandomForestClassifier(
            n_estimators=200,
            max_depth=20,
            min_samples_split=5,
            class_weight=cw,
            random_state=42,
            n_jobs=-1
        )

        self.svm_model = SGDClassifier(
            loss="modified_huber",
            max_iter=1000,
            tol=1e-3,
            class_weight=cw,
            random_state=42,
            n_jobs=-1
        )

        self.et_model = ExtraTreesClassifier(
            n_estimators=200,
            max_depth=20,
            min_samples_split=5,
            class_weight=cw,
            random_state=42,
            n_jobs=-1
        )

        print("Training Random Forest...")
        self.rf_model.fit(X_train, y_train)

        print("Training SGD Classifier (SVM-like)...")
        self.svm_model.fit(X_train, y_train)

        print("Training Extra Trees...")
        self.et_model.fit(X_train, y_train)

        joblib.dump(self.rf_model, os.path.join(self.model_dir, "rf_model.pkl"))
        joblib.dump(self.svm_model, os.path.join(self.model_dir, "sgd_model.pkl"))
        joblib.dump(self.et_model, os.path.join(self.model_dir, "et_model.pkl"))

        print("All models trained and saved.")
    
    def hivemind_vote(self, predictions, proba_rf=None, proba_et=None):
        # Require at least 2 of 3 models to agree on Attack
        # This is already what majority vote does — but you can
        # make it stricter by requiring all 3 to agree:
        final_predictions = []
        for i in range(len(predictions[0])):
            votes = predictions[0][i] + predictions[1][i] + predictions[2][i]
            # Strict: flag Attack only if all 3 agree
            final_predictions.append(1 if votes == 3 else 0)
        return np.array(final_predictions)

    def evaluate(self, X_test, y_test):

        rf_pred = self.rf_model.predict(X_test)
        sgd_pred = self.svm_model.predict(X_test)
        et_pred = self.et_model.predict(X_test)

        final_pred = self.hivemind_vote([rf_pred, sgd_pred, et_pred])

        acc = accuracy_score(y_test, final_pred)
        f1 = f1_score(y_test, final_pred)
        auc = roc_auc_score(y_test, final_pred)

        print(f"Accuracy : {acc:.4f}")
        print(f"F1 Score : {f1:.4f}")
        print(f"ROC-AUC  : {auc:.4f}")

        print("\nConfusion Matrix:")
        cm = confusion_matrix(y_test, final_pred)
        tn, fp, fn, tp = cm.ravel()
        print(f"  True Negatives  (Normal correct) : {tn}")
        print(f"  False Positives (Normal as Attack): {fp}")
        print(f"  False Negatives (Attack missed)  : {fn}")
        print(f"  True Positives  (Attack correct) : {tp}")

        print("\nClassification Report:")
        print(classification_report(y_test, final_pred,
              target_names=["Normal", "Attack"], zero_division=0))

        return final_pred