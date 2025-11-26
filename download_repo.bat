git lfs install

git clone https://huggingface.co/microsoft/phi-2  ./project/models

REM git clone https://huggingface.co/microsoft/Phi-3-mini-128k-instruct ./project/models
REM git clone https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507  ./project/models

REM git clone https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-GGUF ./project/models
REM git clone https://huggingface.co/microsoft/Phi-3-mini-4k-instruct ./project/models
REM il est trop lourd pour mon GPU arc, la mémoire fait que swapper sur le DD

REM RAG EMBEDED FAIISS TRAINER : il faut un model de training vertoriel pour faire les enregistrements faiss de mes chunk (shard de contenue sur 4byte)
git clone https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2 ./project/models
