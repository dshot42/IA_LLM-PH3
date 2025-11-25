import torch_directml
dml = torch_directml.device()

# Exemple avec un tenseur
import torch
x = torch.randn(3, 3).to(dml)
print(x.device)  # doit afficher privateuseone:0
