# AI Course

Plano de aprendizagem de GenAI em português, do funcionamento interno dos LLMs a RAG avançado, agentes, fine-tuning e deploy. São 14 módulos em 5 fases, cada um com uma lição interativa, um notebook prático em Python e um use case de complexidade crescente.

**Currículo online:** https://paulodiasfaria.github.io/ai-course/

## Módulos

| | Módulo | Materiais | Use case |
|---|---|---|---|
| M01 | Como funcionam os LLMs | [lição](https://paulodiasfaria.github.io/ai-course/modulos/01-como-funcionam-os-llms/licao.html) · [notebook](modulos/01-como-funcionam-os-llms/pratica.ipynb) | Mini-GPT e explorador de tokens |
| M02 | Prompt engineering e structured outputs | [lição](https://paulodiasfaria.github.io/ai-course/modulos/02-prompt-engineering-e-structured-outputs/licao.html) · [notebook](modulos/02-prompt-engineering-e-structured-outputs/pratica.ipynb) | Extração de dados de faturas e emails |
| M03 | APIs, modelos locais e apps conversacionais | [lição](https://paulodiasfaria.github.io/ai-course/modulos/03-apis-modelos-locais-e-apps-conversacionais/licao.html) · [notebook](modulos/03-apis-modelos-locais-e-apps-conversacionais/pratica.ipynb) | Chatbot de apoio ao cliente |
| M04 | Embeddings e pesquisa semântica | [lição](https://paulodiasfaria.github.io/ai-course/modulos/04-embeddings-e-pesquisa-semantica/licao.html) · [notebook](modulos/04-embeddings-e-pesquisa-semantica/pratica.ipynb) | Motor de pesquisa semântica de notícias |
| M05 | RAG fundamental | [lição](https://paulodiasfaria.github.io/ai-course/modulos/05-rag-fundamental/licao.html) · [notebook](modulos/05-rag-fundamental/pratica.ipynb) | Assistente de documentação interna |
| M06 | RAG avançado | [lição](https://paulodiasfaria.github.io/ai-course/modulos/06-rag-avancado/licao.html) · [notebook](modulos/06-rag-avancado/pratica.ipynb) | Assistente de legislação portuguesa |
| M07 | Avaliação, observabilidade e guardrails | [lição](https://paulodiasfaria.github.io/ai-course/modulos/07-avaliacao-observabilidade-e-guardrails/licao.html) · [notebook](modulos/07-avaliacao-observabilidade-e-guardrails/pratica.ipynb) | Laboratório de avaliação do assistente jurídico |
| M08 | Tool use e agentes | [lição](https://paulodiasfaria.github.io/ai-course/modulos/08-tool-use-e-agentes/licao.html) · [notebook](modulos/08-tool-use-e-agentes/pratica.ipynb) | Agente analista de dados |
| M09 | MCP, integrações e segurança de agentes | [lição](https://paulodiasfaria.github.io/ai-course/modulos/09-mcp-integracoes-e-seguranca-de-agentes/licao.html) · [notebook](modulos/09-mcp-integracoes-e-seguranca-de-agentes/pratica.ipynb) | Servidor MCP para uma base de dados de vendas |
| M10 | Sistemas multi-agente | [lição](https://paulodiasfaria.github.io/ai-course/modulos/10-sistemas-multi-agente/licao.html) · [notebook](modulos/10-sistemas-multi-agente/pratica.ipynb) | Equipa de pesquisa de mercado |
| M11 | Fine-tuning e alinhamento | [lição](https://paulodiasfaria.github.io/ai-course/modulos/11-fine-tuning-e-alinhamento/licao.html) · [notebook](modulos/11-fine-tuning-e-alinhamento/pratica.ipynb) | Modelo pequeno especialista em português |
| M12 | Inferência eficiente e LLMOps | [lição](https://paulodiasfaria.github.io/ai-course/modulos/12-inferencia-eficiente-e-llmops/licao.html) · [notebook](modulos/12-inferencia-eficiente-e-llmops/pratica.ipynb) | API de produção para o modelo afinado |
| M13 | Multimodal e fronteira do estado da arte | [lição](https://paulodiasfaria.github.io/ai-course/modulos/13-multimodal-e-fronteira-do-estado-da-arte/licao.html) · [notebook](modulos/13-multimodal-e-fronteira-do-estado-da-arte/pratica.ipynb) | Processador de documentos digitalizados |
| M14 | Projeto final de portfólio | [lição](https://paulodiasfaria.github.io/ai-course/modulos/14-projeto-final-de-portfolio/licao.html) · [notebook](modulos/14-projeto-final-de-portfolio/pratica.ipynb) | Copiloto de análise de documentos empresariais |

## Estrutura

```
ai-course/
├── index.html              # currículo (GitHub Pages)
├── assets/
│   ├── licao.css           # estilo comum das lições
│   └── licao.js            # quizzes, botão copiar, diagramas Mermaid, progresso
├── modulos/
│   ├── _template/licao.html  # página de referência com todos os componentes
│   └── NN-nome-do-modulo/
│       ├── README.md       # resumo, objetivos e leituras
│       ├── licao.html      # lição interativa
│       ├── pratica.ipynb   # notebook com exercícios
│       └── use-case/       # código do use case
├── pyproject.toml          # dependências (uv)
└── .env.example            # chaves de API
```

## Como começar

```bash
git clone https://github.com/paulodiasfaria/ai-course.git
cd ai-course
uv sync                     # dependências base
uv sync --extra rag         # acrescenta as de um grupo (rag, agentes, finetuning, deploy)
cp .env.example .env        # e preenche as chaves
uv run jupyter lab
```

As lições abrem diretamente no browser, localmente ou através do GitHub Pages.
