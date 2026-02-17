"""
Train SimBA Random Forest classifiers for Grooming and Thigmotaxis.
Trains one model at a time by updating the config's 'classifier' field.
"""
import os
import sys
import configparser

CONFIG_PATH = os.path.abspath(os.path.join(
    "data", "simba_projects", "SimBA_EPM_Analysis",
    "project_folder", "project_config.ini"
))

BEHAVIORS = ["Grooming", "Thigmotaxis"]

def train_all():
    if not os.path.exists(CONFIG_PATH):
        print(f"Config not found: {CONFIG_PATH}")
        sys.exit(1)

    for behavior in BEHAVIORS:
        print(f"\n{'='*60}")
        print(f"Training classifier for: {behavior}")
        print(f"{'='*60}")

        # Update config to set which classifier to train
        config = configparser.ConfigParser()
        config.read(CONFIG_PATH)
        config.set("create ensemble settings", "classifier", behavior)
        with open(CONFIG_PATH, "w") as f:
            config.write(f)

        # Now train
        from simba.model.train_rf import TrainRandomForestClassifier
        trainer = TrainRandomForestClassifier(config_path=CONFIG_PATH)
        trainer.run()
        trainer.save()
        print(f"Model for {behavior} trained and saved!")

    print("\n" + "="*60)
    print("ALL CLASSIFIERS TRAINED SUCCESSFULLY!")
    print("="*60)

if __name__ == "__main__":
    train_all()
