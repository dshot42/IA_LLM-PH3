import subprocess
import sys

def install_requirements(requirements_file="./requirements.txt"):
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_file])
        print("✅ Toutes les dépendances ont été installées.")
    except subprocess.CalledProcessError as e:
        print("❌ Erreur lors de l'installation :", e)

if __name__ == "__main__":
    install_requirements()
