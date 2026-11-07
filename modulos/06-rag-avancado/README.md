# M06 · RAG avançado

As técnicas que separam um protótipo de um sistema em produção.

| | |
|---|---|
| Fase | RAG |
| Duração estimada | 10 h |
| Complexidade | 4/5 |
| Ferramentas | Qdrant, bge-reranker, Cohere Rerank, LlamaIndex, Microsoft GraphRAG |

## Ficheiros

- [`licao.html`](licao.html): lição interativa
- [`pratica.ipynb`](pratica.ipynb): notebook com exercícios
- [`use-case/`](use-case/): código do use case

## Use case: Assistente de legislação portuguesa

Um assistente sobre legislação laboral e fiscal portuguesa que cita artigos exatos, lida com perguntas que cruzam vários diplomas e mostra o ganho de cada técnica em relação ao RAG do módulo 5.

## Objetivos

- Combinar pesquisa híbrida com reranking por cross-encoders
- Reescrever e decompor perguntas para melhorar a recuperação
- Aplicar contextual retrieval, parent-child e late chunking
- Saber quando usar GraphRAG, RAG multimodal e agentic RAG

## Leituras de base

Contextual Retrieval (Anthropic, 2024); From Local to Global: GraphRAG (Microsoft, 2024); ColPali (Faysse et al., 2024)
