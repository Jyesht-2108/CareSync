# CareSync — Project Rules
- Train ML models ONLY on files inside /datasets. Never fetch, download, or synthesize external training data. This is a hard disqualification rule.
- The product must look and behave as a local/edge-first system: no runtime calls to external LLM or cloud AI APIs from the app itself.
- Keep the stack to what's specified: React + Vite + Tailwind frontend, FastAPI backend, scikit-learn/XGBoost for modeling. No new frameworks without a strong reason.
- When something is ambiguous (schema, missing labels, etc.), make the most clinically/technically reasonable assumption, document it in code comments + README, and continue. Do not stop to ask the user.