import torch
from config import Config

def evaluate_model(model, tokenizer):
    prompts = [
        "Write a short poem about the sea.",
        "Give me a recipe for chocolate cake.",
        "Explain the theory of relativity in simple terms.",
        "quel est l'état de la Machine ABC003 avec vibration 0.95",
        "donne moi la liste des Machine avec vibration 0.95",
        "liste moi les fichiers dans le dossier :  C:/Users/come_/Desktop/ia-llm/phi3/project/ "
    ]

    print("\n --- Running Evaluation:")
    for prompt in prompts:
        prompt_query(prompt,model,tokenizer)
       

def prompt_query(prompt,model,tokenizer):
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=Config.MAX_OUTPUT_TOKEN,
            do_sample=True,
            top_p=Config.TOP_P,
            temperature=Config.TEMPERATURE
        )
    decoded = tokenizer.decode(output[0], skip_special_tokens=True)
    print(f"\nPrompt: {prompt}\nResponse: {decoded}")
    return decoded
