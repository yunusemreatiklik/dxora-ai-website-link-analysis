# LLM model selection and benchmarking – TO DO before Dxora submission

The assignment requires at least **three** real providers/models compared on model name, accuracy/quality, response speed, API cost, context window, structured JSON reliability and justified final recommendation.

| Provider | Model ID | Input USD/1M tokens | Output USD/1M tokens | Avg latency (s) | Schema success rate | Context window | Evidence/source/date |
|---|---|---:|---:|---:|---:|---:|---|
| Google Gemini | TBD (use a stable available model ID) | TBD | TBD | TBD | TBD | TBD | https://ai.google.dev/gemini-api/docs/pricing |
| OpenAI | TBD | TBD | TBD | TBD | TBD | TBD | https://platform.openai.com/pricing |
| Anthropic | TBD | TBD | TBD | TBD | TBD | TBD | https://platform.claude.com/docs/en/about-claude/pricing |

Use 3–5 websites with different categories. Record the request/output token usage and end-to-end latency, count JSON schema validations and manually check grounding. **Do not turn estimates into measured findings.**

Estimated per-analysis cost formula:

`cost = (input_tokens / 1,000,000 × input_price) + (output_tokens / 1,000,000 × output_price)`

Select a fixed model ID for pricing and reproduce all runs. An alias such as `gemini-flash-latest` can change its underlying model.
