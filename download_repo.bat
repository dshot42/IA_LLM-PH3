git lfs install

pip install -r requirements.txt


REM git clone https://huggingface.co/microsoft/phi-2  ./project/models

git clone https://huggingface.co/microsoft/Phi-3-mini-128k-instruct ./project/models
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
huggingface-cli download johnlam90/phi3-mini-4k-instruct-alpaca-lora --local-dir ./phi3-lora ./project/models/lora
