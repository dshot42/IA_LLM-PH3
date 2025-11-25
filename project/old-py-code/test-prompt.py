from transformers import AutoTokenizer, AutoModelForCausalLM

model_id = "phi-2"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id, 
    device_map="auto",   # tente d'utiliser le GPU si dispo
    load_in_8bit=True    # quantization
)

prompt = "USER: who is mickael Jackson ?\nASSISTANT:"
inputs = tokenizer(prompt, return_tensors="pt")
outputs = model.generate(**inputs, max_new_tokens=100)

print(tokenizer.decode(outputs[0], skip_special_tokens=True))
