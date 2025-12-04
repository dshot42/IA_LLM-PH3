import pkg_resources

# Nom du fichier requirements
output_file = "requirements.txt"

with open(output_file, "w") as f:
    for dist in pkg_resources.working_set:
        # On ignore les packages liés à Triton / DirectML si tu veux CPU-only
        if any(x in dist.project_name.lower() for x in ["triton", "torch-directml"]):
            continue
        f.write(f"{dist.project_name}=={dist.version}\n")

print(f"✅ requirements.txt généré  .")
