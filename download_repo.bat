git lfs install

pip install -r requirements.txt


REM git clone https://huggingface.co/microsoft/phi-2  ./project/models

git clone https://huggingface.co/microsoft/Phi-3-mini-128k-instruct ./project/models/phi3
REM git clone https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507  ./project/models

REM git clone https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-GGUF ./project/models
REM git clone https://huggingface.co/microsoft/Phi-3-mini-4k-instruct ./project/models
REM il est trop lourd pour mon GPU arc, la mémoire fait que swapper sur le DD
REM git clone https://huggingface.co/microsoft/Phi-3-small-128k-instruct # le standard 7b (demande beaucoup de puissance GPU)

REM RAG EMBEDED FAIISS TRAINER : il faut un model de training vertoriel pour faire les enregistrements faiss de mes chunk (shard de contenue sur 4byte)
git clone https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2 ./project/models


REM ici download repo pour image
REM  todo 
REM huggingface-cli login   # si tu veux, mais pas toujours obligatoire
pip install -U huggingface_hub
huggingface-cli download johnlam90/phi3-mini-4k-instruct-alpaca-lora --local-dir ./project/models/lora

huggingface-cli download BAAI/bge-large-en-v1.5 --local-dir ./project/ressources/models/bge

huggingface-cli download TheBloke/Mistral-7B-v0.1-GGUF mistral-7b-v0.1.Q5_K_M.gguf --local-dir ./project/models/mistral

huggingface-cli download mistralai/Mistral-7B-Instruct-v0.3 --local-dir C:\Users\come_\Desktop\ia-llm\phi3\project\models\mistral_instruct --local-dir-use-symlinks False


REM qwen le top en gguf !
huggingface-cli download Qwen/Qwen2-7B-Instruct-GGUF --include "Qwen2-7B-Instruct-Q5_K_M.gguf" --local-dir ./models/qwen2-7b/

huggingface-cli download kang9/Qwen3-8B-Q5_K_M-GGUF --local-dir ./models/qwen3-8b-q5